"""One-command launcher for Google Colab.

    !python teledrive_launcher.py            # local UI, no public link
    !python teledrive_launcher.py --check    # verify bindings, no credentials
    !python teledrive_launcher.py --share    # explicit opt-in public link

Creates exactly ONE ApplicationContext (which owns the one async runtime, the
one Telegram client and the one Drive service) and launches Gradio inside the
same Python process. ``--check`` needs no Telegram or Drive credentials.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from teledrive import bootstrap  # noqa: E402
from teledrive.app import DEFAULT_PORT, launch  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TeleDrive v4.5 launcher")
    parser.add_argument(
        "--share",
        action="store_true",
        help="opt in to a public Gradio link (off by default)",
    )
    parser.add_argument(
        "--no-share",
        action="store_true",
        help="deprecated no-op; no public link is the default",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify that every ready action resolves, then exit",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Gradio server port (default {DEFAULT_PORT}, matches the Colab "
        "proxyPort helper so the official proxy URL is stable)",
    )
    return parser


def run_check(ctx) -> int:
    """Resolve every ready action's service path against the live context."""
    from teledrive import action_registry

    specs = list(action_registry.ready_specs())
    for spec in specs:
        ctx.resolve(spec.service_path)
    print(
        f"binding check ok: {len(specs)}/{len(action_registry.ACTION_SPECS)} "
        "ready actions resolve"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # The one and only context for this process.
    ctx = bootstrap.run()
    print("bootstrap:", ctx.bootstrap_info)

    if args.check:
        try:
            return run_check(ctx)
        finally:
            ctx.shutdown()

    launch(ctx, share=args.share, blocking=True, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
