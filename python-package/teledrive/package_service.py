"""Packaging: build the downloadable ZIP only after the test suite passes.

Constitution Section 10: an untested archive must never be produced.
"""
from __future__ import annotations

import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .config import ROOT
from .errors import TeleDriveError
from .logging_config import get_logger
from .utils import now_iso

_log = get_logger("teledrive.package")

PACKAGE_ROOT = Path(__file__).resolve().parent.parent  # python-package/
INCLUDE_DIRS = ("teledrive", "tests", "docs", "notebook")
INCLUDE_FILES = (
    "README.md",
    "CHANGELOG.md",
    "HANDOFF.md",
    "requirements.txt",
    "requirements.lock",
    "pyproject.toml",
    "teledrive_launcher.py",
)
EXCLUDE_PARTS = (
    "__pycache__",
    ".pytest_cache",
    ".git",
    "session",
    "temp",
    "checkpoints",
    "_quarantine",
)
# Never ship secrets, runtime databases, sessions or tokens.
EXCLUDE_SUFFIXES = (".db", ".db-wal", ".db-shm", ".session", ".session-journal", ".pyc", ".zip")
EXCLUDE_NAMES = (".env", "drive_token.json", "client_secret.json", "teledrive.log")


def _is_excluded(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDE_PARTS for part in relative.parts):
        return True
    if path.name in EXCLUDE_NAMES:
        return True
    return path.suffix in EXCLUDE_SUFFIXES


@dataclass
class BuildResult:
    ok: bool
    zip_path: str
    tests_passed: bool
    summary: str


class PackageService:
    def __init__(self, ctx=None, package_root: Path | None = None) -> None:
        self.ctx = ctx
        self.root = package_root or PACKAGE_ROOT

    # ---- tests gate ----

    def run_tests(self) -> tuple[bool, str]:
        proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
            [sys.executable, "-m", "pytest", "-q", "tests"],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            timeout=900,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, output.strip()[-4000:]

    # ---- archive ----

    def _files(self) -> list[Path]:
        collected: list[Path] = []
        for name in INCLUDE_FILES:
            path = self.root / name
            if path.exists():
                collected.append(path)
        for directory in INCLUDE_DIRS:
            base = self.root / directory
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file() and not _is_excluded(path, self.root):
                    collected.append(path)
        return collected

    def build_archive(self, destination: Path | None = None) -> Path:
        destination = destination or (ROOT / "teledrive_v4.5.zip")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in self._files():
                archive.write(path, arcname=str(Path("teledrive-v4.5") / path.relative_to(self.root)))
        _log.info("archive built at %s", destination)
        return destination

    def build_tested_archive(self, destination: str | Path | None = None) -> BuildResult:
        passed, summary = self.run_tests()
        if not passed:
            raise TeleDriveError(
                f"test suite failed; archive not produced\n{summary}", "err.tests_failed"
            )
        path = self.build_archive(Path(destination) if destination else None)
        return BuildResult(
            ok=True,
            zip_path=str(path),
            tests_passed=True,
            summary=f"{now_iso()} tests passed\n{summary}",
        )


def main(argv: list[str] | None = None) -> int:
    """CLI used by CI: ``python -m teledrive.package_service --build``.

    Tests always run first; a failing suite means no archive is produced.
    """
    import argparse

    parser = argparse.ArgumentParser(description="TeleDrive package builder")
    parser.add_argument("--build", action="store_true", help="run tests, then build the zip")
    parser.add_argument("--output", default=None, help="destination zip path")
    args = parser.parse_args(argv)
    if not args.build:
        parser.error("nothing to do; pass --build")
    result = PackageService().build_tested_archive(args.output)
    print(result.summary.splitlines()[0])
    print("archive:", result.zip_path)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
