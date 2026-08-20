"""Resume a Telegram login across Colab VMs via Drive AppData.

Owner-authorized deviation from Constitution §13 (memory-only credentials).
See ``docs/decisions/ADR-004-session-vault.md``.

What is stored
--------------
* Colab Secrets (outside this module): ``TELEGRAM_API_ID`` / ``TELEGRAM_API_HASH``.
* Drive folder ``TeleDrive_AppData``: one obfuscated Telethon session blob
  named ``td_telegram.session.vault``. That file is a login cookie. Anyone
  who has it AND the api_hash can impersonate the account.

What is never stored
--------------------
api_id, api_hash, phone, OTP, 2FA password, Drive OAuth tokens. Nothing is
printed, logged, checkpointed or packaged. Bytes never appear in events.

Obfuscation is XOR-stream with a PBKDF2 key derived from api_hash. It is
NOT a claim of cryptography-grade protection — it only stops a casual
Drive listing from being a raw SQLite session.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import (
    DRIVE_APPDATA_FOLDER,
    SESSION_VAULT_MAX_BYTES,
    SESSION_VAULT_NAME,
)
from .logging_config import get_logger

_log = get_logger("teledrive.session_vault")

MAGIC = b"TDVS1\n"
VAULT_MANIFEST_NAME = "td_telegram.active.json"
VAULT_VERSION_PREFIX = "td_telegram.version."
_PBKDF2_ROUNDS = 80_000
_SALT = b"teledrive-session-vault-v1"

_KEEPALIVE_LOCK = threading.Lock()
_KEEPALIVE_STARTED = False


def _session_path() -> Path:
    from . import config

    return Path(config.TELEGRAM_SESSION)


def _key(secret: str) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        (secret or "").encode("utf-8"),
        _SALT,
        _PBKDF2_ROUNDS,
        dklen=32,
    )


def _xor_stream(data: bytes, key: bytes) -> bytes:
    out = bytearray(len(data))
    block = b""
    counter = 0
    for i in range(len(data)):
        if i % 32 == 0:
            block = hashlib.sha256(key + counter.to_bytes(8, "big")).digest()
            counter += 1
        out[i] = data[i] ^ block[i % 32]
    return bytes(out)


def wrap_blob(raw: bytes, secret: str) -> bytes:
    if len(raw) > SESSION_VAULT_MAX_BYTES:
        raise ValueError("session blob too large")
    return MAGIC + _xor_stream(raw, _key(secret))


def unwrap_blob(blob: bytes, secret: str) -> Optional[bytes]:
    if not blob or len(blob) > SESSION_VAULT_MAX_BYTES + len(MAGIC):
        return None
    if blob.startswith(MAGIC):
        raw = _xor_stream(blob[len(MAGIC):], _key(secret))
    else:
        # tolerate a raw session uploaded by an older helper
        raw = blob
    if not raw.startswith(b"SQLite format 3"):
        return None
    return raw


def _ops(drive: Any) -> Any:
    if drive is None:
        return None
    needed = ("ensure_folder", "list_children", "download_bytes")
    if all(hasattr(drive, name) for name in needed) and (
        hasattr(drive, "upsert_bytes") or hasattr(drive, "upload_bytes")
    ):
        return drive
    try:
        from .drive_client import DriveService

        return DriveService.from_auth(drive)
    except Exception as exc:  # noqa: BLE001
        _log.warning("session vault: drive ops unavailable (%s)", type(exc).__name__)
        return None


def _put(ops: Any, name: str, data: bytes, parent_id: str) -> str:
    if hasattr(ops, "upsert_bytes"):
        return ops.upsert_bytes(
            name, data, parent_id, mime_type="application/octet-stream"
        )
    children = ops.list_children(parent_id) or []
    if hasattr(ops, "delete_file"):
        for child in children:
            if child.get("name") == name:
                try:
                    ops.delete_file(child["id"])
                except Exception:
                    pass
    return ops.upload_bytes(name, data, parent_id)


def _find(ops: Any, parent_id: str, name: str) -> list[dict]:
    children = ops.list_children(parent_id) or []
    hits = [c for c in children if c.get("name") == name]
    hits.sort(key=lambda c: c.get("modifiedTime") or "", reverse=True)
    return hits


def save_session(drive: Any, secret: str = "", local_path: Path | None = None) -> Optional[str]:
    """Upload the local Telethon session as an obfuscated Drive blob."""
    path = Path(local_path) if local_path is not None else _session_path()
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if not raw or not raw.startswith(b"SQLite format 3"):
        return None
    ops = _ops(drive)
    if ops is None:
        return None
    try:
        folder_id = ops.ensure_folder(DRIVE_APPDATA_FOLDER)
        file_id = _put(ops, SESSION_VAULT_NAME, wrap_blob(raw, secret), folder_id)
    except Exception as exc:  # noqa: BLE001
        _log.warning("session vault save skipped: %s", type(exc).__name__)
        return None
    _log.info("session vault saved")
    return file_id


def restore_session(drive: Any, secret: str = "", local_path: Path | None = None) -> bool:
    """Write a previously saved session onto local disk. Returns True on success."""
    ops = _ops(drive)
    if ops is None:
        return False
    try:
        folder_id = ops.find_folder(DRIVE_APPDATA_FOLDER) if hasattr(ops, "find_folder") else None
        if not folder_id:
            folder_id = ops.ensure_folder(DRIVE_APPDATA_FOLDER)
        hits = _find(ops, folder_id, SESSION_VAULT_NAME)
        if not hits:
            return False
        blob = ops.download_bytes(hits[0]["id"])
    except Exception as exc:  # noqa: BLE001
        _log.warning("session vault restore skipped: %s", type(exc).__name__)
        return False
    raw = unwrap_blob(blob or b"", secret)
    if raw is None:
        _log.warning("session vault restore: blob rejected")
        return False
    path = Path(local_path) if local_path is not None else _session_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    except OSError as exc:
        _log.warning("session vault restore write failed: %s", type(exc).__name__)
        return False
    _log.info("session vault restored")
    return True


def wipe_session(drive: Any = None, local_path: Path | None = None) -> None:
    """Delete the local session file and the Drive blob. Used on logout."""
    path = Path(local_path) if local_path is not None else _session_path()
    for candidate in (path, Path(str(path) + "-journal")):
        try:
            if candidate.exists() or candidate.is_symlink():
                candidate.unlink()
        except OSError:
            pass
    ops = _ops(drive)
    if ops is None:
        return
    try:
        folder_id = None
        if hasattr(ops, "find_folder"):
            folder_id = ops.find_folder(DRIVE_APPDATA_FOLDER)
        if not folder_id and hasattr(ops, "ensure_folder"):
            # do not create a folder just to wipe
            return
        if not folder_id:
            return
        if not hasattr(ops, "delete_file"):
            return
        for child in _find(ops, folder_id, SESSION_VAULT_NAME):
            try:
                ops.delete_file(child["id"])
            except Exception:
                pass
        _log.info("session vault wiped")
    except Exception as exc:  # noqa: BLE001
        _log.warning("session vault wipe skipped: %s", type(exc).__name__)


def persist_from_context(ctx: Any, secret: str = "") -> Optional[str]:
    """Persist through the one modern vault path used by every authorization flow."""
    vault = getattr(ctx, "session_vault", None)
    if vault is None:  # pragma: no cover - ApplicationContext always owns one
        return None
    result = vault.save_after_login(force=False)
    return "saved" if result.saved else None


def restore_from_context(ctx: Any, secret: str = "") -> bool:
    vault = getattr(ctx, "session_vault", None)
    if vault is None:  # pragma: no cover - compatibility fallback
        return restore_session(_drive_from_ctx(ctx), secret=secret)
    return bool(vault.autorestore_once().restored)


def wipe_from_context(ctx: Any) -> None:
    vault = getattr(ctx, "session_vault", None)
    if vault is not None:
        vault.forget_quiet()
    try:
        wipe_session(_drive_from_ctx(ctx, require_connected=False))
    except Exception as exc:  # noqa: BLE001
        _log.warning("legacy vault wipe skipped: %s", type(exc).__name__)


def _drive_from_ctx(ctx: Any, *, require_connected: bool = True) -> Any:
    if ctx is None:
        return None
    existing = getattr(ctx, "drive_client", None)
    if existing is not None:
        return existing
    auth = getattr(ctx, "drive_auth", None)
    if auth is None:
        return None
    if require_connected and not getattr(auth, "connected", False):
        return None
    ensure = getattr(ctx, "ensure_drive_client", None)
    if callable(ensure):
        try:
            return ensure()
        except Exception:
            return None
    return auth


def start_keepalive(interval_seconds: int = 120) -> dict:
    """Best-effort Colab idle delay: daemon heartbeat + browser Connect click.

    Does NOT defeat the 12-hour free-runtime cap or a closed tab. Idempotent.
    """
    global _KEEPALIVE_STARTED
    interval = max(30, int(interval_seconds or 120))
    with _KEEPALIVE_LOCK:
        if _KEEPALIVE_STARTED:
            return {"started": False, "reason": "already-running", "js": False}
        _KEEPALIVE_STARTED = True

        def _beat() -> None:
            while True:
                time.sleep(interval)
                try:
                    stamp = time.strftime("%H:%M UTC", time.gmtime())
                    print("TeleDrive keep-alive", stamp, flush=True)
                except Exception:
                    pass

        threading.Thread(target=_beat, name="td-keepalive", daemon=True).start()

    js = False
    try:
        from IPython.display import Javascript, display  # type: ignore

        display(Javascript(_KEEPALIVE_JS))
        js = True
    except Exception:
        js = False
    _log.info("keep-alive started js=%s interval=%s", js, interval)
    return {"started": True, "reason": "ok", "js": js}


def reset_keepalive_for_tests() -> None:
    global _KEEPALIVE_STARTED
    with _KEEPALIVE_LOCK:
        _KEEPALIVE_STARTED = False


# ---------------------------------------------------------------------------
# M24-T01 — explicit Telegram session vault on the user's own Drive.
# The class below is the user-facing save / auto-restore / forget API.
# The function-level helpers above stay for telegram_auth.py (protected):
# persist_from_context / wipe_from_context / restore_from_context / keepalive.
# Telegram still runs ONLY from the local session file under /content.
# ---------------------------------------------------------------------------

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from .errors import DriveNotReadyError, TeleDriveError
from .redaction import mask_phone

VAULT_SESSION_NAME = "telegram.session"
VAULT_CREDS_NAME = "telegram_creds.json"
VAULT_FORMAT = 1                  # legacy: raw session + plaintext api_hash
VAULT_FORMAT_ENCRYPTED = 2        # M24-T05: wrapped session, NO api_hash on Drive
VAULT_SUPPORTED_FORMATS = (VAULT_FORMAT, VAULT_FORMAT_ENCRYPTED)


def _plaintext_vault() -> bool:
    """Owner escape hatch: keep the old plaintext format (not recommended)."""
    import os

    return str(os.environ.get("TELEDRIVE_VAULT_PLAINTEXT", "")).strip().lower() in (
        "1", "true", "yes",
    )


# M24-T03: a restored blob is written to disk ONLY when it really is a SQLite
# session. Telethon opens the path with sqlite3; junk bytes there produce a
# corrupt-database crash instead of the honest manual-login fallback.
SQLITE_MAGIC = b"SQLite format 3"


def _looks_like_drive_ops(obj: Any) -> bool:
    needed = ("ensure_folder", "list_children", "download_bytes", "upsert_bytes")
    return obj is not None and all(hasattr(obj, name) for name in needed)


@dataclass
class VaultResult:
    ok: bool
    message_key: str
    detail: str = ""
    restored: bool = False
    saved: bool = False
    forgotten: bool = False
    phone_label: str = ""


class SessionVault:
    def __init__(self, ctx) -> None:
        self.ctx = ctx
        # M24-T03: autorestore_once() is called from ui.build() before the
        # first paint; the language re-render must not repeat the Drive round
        # trip, so the one-shot latch lives on the context-owned vault.
        self._autorestore_done = False
        # M24-T05 determinism state.
        self._pending_save = False
        self._last_fingerprint = ""
        self.last_result: Optional[VaultResult] = None

    # ---------- path helpers ----------

    def _session_path(self) -> Path:
        from . import config

        client = getattr(getattr(self.ctx, "telegram_auth", None), "client", None)
        raw = getattr(client, "session_path", None) if client is not None else None
        if raw:
            return Path(raw)
        return Path(config.TELEGRAM_SESSION)

    def _local_session_path(self) -> Path:
        path = self._session_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _creds_path(self) -> Path:
        return self._local_session_path().with_name(VAULT_CREDS_NAME)

    def _drive_client(self, service: Any | None = None) -> Any:
        if service is not None:
            if _looks_like_drive_ops(service):
                return service
            from .drive_client import DriveService

            return DriveService(service)
        if not getattr(self.ctx.drive_auth, "connected", False):
            raise DriveNotReadyError("drive is not connected")
        existing = getattr(self.ctx, "drive_client", None)
        if _looks_like_drive_ops(existing):
            return existing
        from .drive_client import DriveService

        return DriveService.from_auth(self.ctx.drive_auth)

    def _vault_folder_id(self, drive: Any) -> str:
        return drive.ensure_folder(DRIVE_APPDATA_FOLDER)

    def _children_by_name(self, drive: Any, folder_id: str) -> dict[str, dict[str, Any]]:
        children = drive.list_children(folder_id)
        return {str(child.get("name") or ""): child for child in children}

    @staticmethod
    def _versioned_name(kind: str, version: str) -> str:
        return f"{VAULT_VERSION_PREFIX}{version}.{kind}"

    def _active_vault_files(
        self, drive: Any, folder_id: str
    ) -> tuple[dict[str, dict[str, Any]], str, str]:
        """Resolve the active pair from a manifest, with legacy fallback.

        A manifest is published only after both versioned files are on Drive.  A
        failed or interrupted replacement therefore leaves the prior manifest
        (or legacy pair) as the only active saved session.
        """
        files = self._children_by_name(drive, folder_id)
        manifest = files.get(VAULT_MANIFEST_NAME)
        if manifest:
            try:
                payload = json.loads(drive.download_bytes(manifest["id"]).decode("utf-8"))
                session_name = str(payload.get("session_file") or "")
                creds_name = str(payload.get("creds_file") or "")
                if (
                    session_name.startswith(VAULT_VERSION_PREFIX)
                    and creds_name.startswith(VAULT_VERSION_PREFIX)
                    and session_name in files
                    and creds_name in files
                ):
                    return files, session_name, creds_name
                _log.warning("telegram vault manifest rejected: incomplete active pair")
            except Exception as exc:  # noqa: BLE001 - legacy files remain recoverable
                _log.warning("telegram vault manifest unreadable: %s", type(exc).__name__)
        return files, VAULT_SESSION_NAME, VAULT_CREDS_NAME

    def _cleanup_superseded_versions(
        self, drive: Any, folder_id: str, keep: set[str]
    ) -> None:
        """Best-effort cleanup only after a new manifest is already live."""
        legacy_names = {VAULT_SESSION_NAME, VAULT_CREDS_NAME, SESSION_VAULT_NAME}
        for name, meta in self._children_by_name(drive, folder_id).items():
            if name in keep or (not name.startswith(VAULT_VERSION_PREFIX) and name not in legacy_names):
                continue
            try:
                drive.delete_file(meta["id"])
            except Exception as exc:  # noqa: BLE001 - active manifest is already safe
                _log.warning("telegram vault cleanup skipped: %s", type(exc).__name__)

    # ---- credential fallback (M24-T03) ----

    def _creds_from_memory(self) -> tuple[str, str, str]:
        """Return (api_id, api_hash, phone) from the live TelegramAuth memory.

        telegram_auth.py is a PROTECTED file. This helper only READS its
        in-memory attributes; it never writes them, never logs them and never
        copies them anywhere except the vault payload the user asked for.
        Missing values come back as empty strings so the caller stays in
        control of the validation error.
        """
        auth = getattr(self.ctx, "telegram_auth", None)
        api_id = str(getattr(auth, "_api_id", "") or "").strip()
        api_hash = str(getattr(auth, "_api_hash", "") or "").strip()
        phone = str(getattr(auth, "_phone", "") or "").strip()
        return api_id, api_hash, phone

    def _vault_present(self, drive: Any, folder_id: str) -> bool:
        """True when BOTH vault files already exist for this Drive account."""
        files = self._children_by_name(drive, folder_id)
        return VAULT_SESSION_NAME in files and VAULT_CREDS_NAME in files

    # ---- M24-T05 vault observability and format helpers ----

    def _emit(self, result: VaultResult, detail: str = "") -> VaultResult:
        """Store and record a redacted outcome without breaking vault work."""
        self.last_result = result
        try:
            from . import database as db

            db.add_event("", "session.vault", result.message_key, {
                "ok": bool(result.ok),
                "saved": bool(result.saved),
                "restored": bool(result.restored),
                "forgotten": bool(result.forgotten),
                "phone": result.phone_label,
                "detail": detail,
            })
        except Exception:  # noqa: BLE001 - telemetry must never break the vault
            pass
        _log.info("vault %s ok=%s detail=%s", result.message_key, result.ok, detail)
        return result

    @staticmethod
    def _fingerprint(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _vault_secret(self) -> str:
        """Read the API hash from live memory or Colab Secrets only."""
        _, api_hash, _ = self._creds_from_memory()
        if api_hash:
            return api_hash
        try:  # Colab only; absent in CI and tests
            from google.colab import userdata  # type: ignore

            return str(userdata.get("TELEGRAM_API_HASH") or "").strip()
        except Exception:  # noqa: BLE001
            return ""

    # ---------- file snapshot / restore ----------

    def _checkpoint_sqlite(self, source: Path, dest: Path) -> None:
        if not source.exists():
            raise TeleDriveError("telegram session file is missing", "err.session_missing")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        src = sqlite3.connect(str(source))
        try:
            out = sqlite3.connect(str(dest))
            try:
                src.backup(out)
            finally:
                out.close()
        finally:
            src.close()

    def _snapshot_bytes(self) -> bytes:
        """Return a validated snapshot of the live Telethon SQLite session."""
        source = self._local_session_path()
        if not source.exists():
            raise TeleDriveError("telegram session file is missing", "err.session_missing")
        snapshot = source.with_name("telegram.session.snapshot")
        data = b""
        try:
            self._checkpoint_sqlite(source, snapshot)
            data = snapshot.read_bytes()
        except Exception as exc:  # noqa: BLE001 - fall back to a direct read
            _log.warning("vault snapshot backup fallback: %s", type(exc).__name__)
            try:
                conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                finally:
                    conn.close()
            except Exception as inner:  # noqa: BLE001
                _log.warning("vault wal checkpoint skipped: %s", type(inner).__name__)
            try:
                data = source.read_bytes()
            except OSError as inner:
                raise TeleDriveError("session read failed", "err.session_missing") from inner
        finally:
            try:
                snapshot.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
        if not data.startswith(SQLITE_MAGIC):
            raise TeleDriveError("session snapshot is not sqlite", "err.session_vault_invalid")
        return data

    def _write_session_bytes(self, data: bytes) -> Path:
        local = self._local_session_path()
        tmp = local.with_suffix(".session.tmp")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        tmp.replace(local)
        return local

    def _read_creds_payload(self, drive: Any, folder_id: str) -> dict[str, Any] | None:
        files = self._children_by_name(drive, folder_id)
        meta = files.get(VAULT_CREDS_NAME)
        if not meta:
            return None
        raw = drive.download_bytes(meta["id"])
        data = json.loads(raw.decode("utf-8"))
        if int(data.get("format", 0) or 0) not in VAULT_SUPPORTED_FORMATS:
            raise TeleDriveError("unsupported vault format", "err.session_vault_invalid")
        return data

    # ---------- public API ----------

    def probe(self, service: Any) -> dict[str, Any]:
        """Used by notebook cell 3 before the app adopts the Drive service."""
        drive = self._drive_client(service)
        folder_id = self._vault_folder_id(drive)
        files, session_name, creds_name = self._active_vault_files(drive, folder_id)
        has_session = session_name in files
        has_creds = creds_name in files
        payload = None
        if has_creds:
            try:
                raw = drive.download_bytes(files[creds_name]["id"])
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                payload = None
        return {
            "has_session": has_session,
            "has_creds": has_creds,
            "phone": str((payload or {}).get("phone") or ""),
            "phone_label": mask_phone(str((payload or {}).get("phone") or "")),
        }

    def save_now(self, api_id: str = "", api_hash: str = "", phone: str = "") -> VaultResult:
        if not self.ctx.telegram_auth.authorized:
            raise TeleDriveError("telegram is not authorized", "err.session_not_authorized")
        api_id = str(api_id or "").strip()
        api_hash = str(api_hash or "").strip()
        phone = str(phone or "").strip()
        memory_id, memory_hash, memory_phone = self._creds_from_memory()
        if not api_id.isdigit():
            api_id = memory_id
        if not api_hash:
            api_hash = memory_hash or self._vault_secret()
        if not phone:
            phone = memory_phone
        if not api_id.isdigit():
            raise TeleDriveError("api id must be numeric", "err.bad_api_id")
        if not api_hash:
            raise TeleDriveError("api hash required", "err.bad_api_hash")

        raw = self._snapshot_bytes()
        drive = self._drive_client()
        folder_id = self._vault_folder_id(drive)
        plaintext = _plaintext_vault()
        blob = raw if plaintext else wrap_blob(raw, api_hash)
        version = uuid.uuid4().hex
        session_name = self._versioned_name("session", version)
        creds_name = self._versioned_name("creds", version)
        creds = {
            "api_id": api_id,
            "phone": phone,
            "saved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "format": VAULT_FORMAT if plaintext else VAULT_FORMAT_ENCRYPTED,
            "session_file": session_name,
        }
        if plaintext:
            creds["api_hash"] = api_hash

        # Never overwrite the active pair in place.  The new session and its
        # metadata are staged under a fresh opaque version; the one small
        # manifest write below is the commit point.  If any staging write fails,
        # the previous manifest remains active and recoverable.
        drive.upsert_bytes(
            session_name, blob, folder_id, mime_type="application/octet-stream"
        )
        drive.upsert_bytes(
            creds_name,
            json.dumps(creds, ensure_ascii=False, indent=2).encode("utf-8"),
            folder_id,
            mime_type="application/json",
        )
        manifest = {
            "format": 1,
            "session_file": session_name,
            "creds_file": creds_name,
            "saved_at": creds["saved_at"],
        }
        drive.upsert_bytes(
            VAULT_MANIFEST_NAME,
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            folder_id,
            mime_type="application/json",
        )
        self._cleanup_superseded_versions(drive, folder_id, {session_name, creds_name})
        self._last_fingerprint = self._fingerprint(raw)
        self._pending_save = False
        _log.info("telegram vault saved phone=%s format=%s", mask_phone(phone), creds["format"])
        return self._emit(
            VaultResult(True, "msg.session_saved", saved=True, phone_label=mask_phone(phone)),
            f"format={creds['format']} bytes={len(blob)}",
        )

    def _release_client_for_swap(self) -> bool:
        """Free the session path before overwriting it when a client is inactive."""
        auth = getattr(self.ctx, "telegram_auth", None)
        client = getattr(auth, "client", None)
        if client is None:
            return True
        if getattr(auth, "authorized", False):
            return False
        closer = getattr(client, "disconnect", None)
        if not callable(closer):
            return False
        try:
            outcome = closer()
            if hasattr(outcome, "__await__"):
                self.ctx.aio.run(outcome)
        except Exception as exc:  # noqa: BLE001
            _log.warning("vault could not release telegram client: %s", type(exc).__name__)
            return False
        return True

    def _discard_stale_local_session(self) -> None:
        """Remove only the proven-invalid runtime copy, never the Drive backup.

        A Drive vault is a recovery point.  It must survive a failed restore until
        a later authorized login publishes a replacement manifest.  The local
        copy is discarded after its client has been released so the manual login
        flow creates a genuinely fresh Telethon session file.
        """
        if not self._release_client_for_swap():
            _log.warning("stale local telegram session retained: client still active")
            return
        try:
            self._local_session_path().unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            _log.warning("stale local telegram session cleanup skipped: %s", type(exc).__name__)
        self._last_fingerprint = ""

    def autorestore(self) -> VaultResult:
        if self.ctx.telegram_auth.authorized:
            return self._emit(VaultResult(True, "msg.session_already_authorized", restored=True))
        if not self.ctx.drive_auth.connected:
            return self._emit(VaultResult(False, "msg.session_restore_skipped_no_drive"))

        drive = self._drive_client()
        folder_id = self._vault_folder_id(drive)
        files, session_name, creds_name = self._active_vault_files(drive, folder_id)
        if session_name not in files or creds_name not in files:
            return self._emit(VaultResult(False, "msg.session_not_saved"))

        try:
            payload = json.loads(drive.download_bytes(files[creds_name]["id"]).decode("utf-8"))
        except Exception:
            return self._emit(VaultResult(False, "err.session_vault_invalid"))
        if not payload:
            return self._emit(VaultResult(False, "err.session_vault_invalid"))

        fmt = int(payload.get("format", 0) or 0)
        api_id = str(payload.get("api_id") or "").strip()
        phone = str(payload.get("phone") or "").strip()
        label = mask_phone(phone)
        api_hash = str(payload.get("api_hash") or "").strip() or self._vault_secret()
        if not api_id.isdigit() or not api_hash:
            return self._emit(
                VaultResult(False, "msg.session_restore_needs_login", phone_label=label),
                "missing api_hash for unwrap",
            )

        blob = drive.download_bytes(files[session_name]["id"])
        raw = blob if fmt == VAULT_FORMAT else unwrap_blob(blob or b"", api_hash)
        if not raw or not raw.startswith(SQLITE_MAGIC):
            _log.warning("telegram vault restore rejected: not a sqlite session")
            return self._emit(
                VaultResult(False, "err.session_vault_invalid", phone_label=label),
                f"format={fmt}",
            )
        if not self._release_client_for_swap():
            return self._emit(
                VaultResult(False, "msg.session_restore_needs_login", phone_label=label),
                "telegram client already active",
            )

        self._write_session_bytes(raw)
        self._last_fingerprint = self._fingerprint(raw)
        try:
            status = self.ctx.telegram_auth.set_credentials(api_id, api_hash)
        except (ConnectionError, TimeoutError, OSError, EOFError) as exc:
            # A transport failure says nothing about whether the saved login is
            # valid.  Keep both local and remote copies so the next retry uses
            # the exact same recovery point.
            return self._emit(
                VaultResult(False, "err.tg_connect_failed", phone_label=label),
                f"restore transport failure: {type(exc).__name__}",
            )
        except Exception as exc:  # noqa: BLE001 - preserve the recovery point
            return self._emit(
                VaultResult(False, "err.session_vault_invalid", phone_label=label),
                f"restore verification failure: {type(exc).__name__}",
            )
        if status.authorized:
            return self._emit(
                VaultResult(True, "msg.session_restored", restored=True, phone_label=label),
                f"format={fmt}",
            )
        self._discard_stale_local_session()
        return self._emit(
            VaultResult(False, "msg.session_restore_needs_login", phone_label=label),
            "restored session is not authorized (revoked; Drive vault retained)",
        )

    def forget(self) -> VaultResult:
        drive = self._drive_client()
        folder_id = self._vault_folder_id(drive)
        files = self._children_by_name(drive, folder_id)
        for name, meta in files.items():
            if (
                name not in (VAULT_SESSION_NAME, VAULT_CREDS_NAME, SESSION_VAULT_NAME, VAULT_MANIFEST_NAME)
                and not name.startswith(VAULT_VERSION_PREFIX)
            ):
                continue
            try:
                drive.delete_file(meta["id"])
            except Exception:  # noqa: BLE001
                pass
        try:
            self._creds_path().unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
        self._last_fingerprint = ""
        _log.info("telegram vault forgotten")
        return self._emit(VaultResult(True, "msg.session_forgotten", forgotten=True))

    # ---- quiet lifecycle helpers (M24-T03) ----

    def autorestore_once(self) -> VaultResult:
        """Restore the saved sign-in BEFORE the first UI paint. Never raises.

        ui.build() calls this so shell_seed() reads a real AUTHORIZED state
        instead of a stale DISCONNECTED one, which removes the dependency on a
        page-load event firing at all. It runs at most once per process, and
        any failure (no Drive, empty vault, revoked session) simply leaves the
        existing manual login path untouched.
        """
        if self._autorestore_done:
            return self._emit(VaultResult(
                self.ctx.telegram_auth.authorized,
                "msg.session_already_authorized",
                restored=self.ctx.telegram_auth.authorized,
            ))
        self._autorestore_done = True
        try:
            return self.autorestore()
        except Exception as exc:  # noqa: BLE001 - the UI build must never die here
            _log.warning("session autorestore skipped: %s", type(exc).__name__)
            return self._emit(VaultResult(False, "err.session_vault_invalid"), type(exc).__name__)

    def save_after_login(self, force: bool = False) -> VaultResult:
        """Persist authorization once Drive is ready, preserving an honest retry latch."""
        try:
            if not self.ctx.telegram_auth.authorized:
                return self._emit(VaultResult(False, "err.session_not_authorized"))
            if not getattr(self.ctx.drive_auth, "connected", False):
                self._pending_save = True
                return self._emit(
                    VaultResult(False, "msg.session_restore_skipped_no_drive"),
                    "deferred: drive not ready",
                )
            api_id, api_hash, phone = self._creds_from_memory()
            if not api_hash:
                api_hash = self._vault_secret()
            if not api_id.isdigit() or not api_hash:
                return self._emit(
                    VaultResult(False, "err.session_vault_invalid"), "no credentials in memory"
                )
            if not force and self._last_fingerprint:
                try:
                    if self._fingerprint(self._snapshot_bytes()) == self._last_fingerprint:
                        return self._emit(VaultResult(True, "msg.session_saved", saved=False), "unchanged")
                except Exception:  # noqa: BLE001 - fall through to a real save
                    pass
            return self.save_now(api_id, api_hash, phone)
        except Exception as exc:  # noqa: BLE001 - a login must never fail on this
            self._pending_save = True
            _log.warning("session autosave deferred: %s", type(exc).__name__)
            return self._emit(VaultResult(False, "err.session_vault_invalid"), type(exc).__name__)

    @property
    def pending(self) -> bool:
        """True when an authorized sign-in is waiting for Drive."""
        return bool(self._pending_save)

    def flush_pending(self) -> Optional[VaultResult]:
        """Persist the deferred sign-in once Telegram and Drive are both live."""
        if not self._pending_save:
            return None
        if not self.ctx.telegram_auth.authorized:
            return None
        if not getattr(self.ctx.drive_auth, "connected", False):
            return None
        self._pending_save = False
        return self.save_after_login(force=True)

    def status(self) -> dict[str, Any]:
        """Return redacted vault state for notebooks and diagnostics."""
        local = self._local_session_path()
        exists = local.exists()
        info: dict[str, Any] = {
            "telegram_state": getattr(self.ctx.telegram_auth, "state", ""),
            "telegram_authorized": bool(getattr(self.ctx.telegram_auth, "authorized", False)),
            "drive_connected": bool(getattr(self.ctx.drive_auth, "connected", False)),
            "local_session": str(local),
            "local_exists": exists,
            "local_bytes": local.stat().st_size if exists else 0,
            "pending_save": self._pending_save,
            "last_result": self.last_result.message_key if self.last_result else "",
            "vault_files": [],
            "vault_format": 0,
            "saved_at": "",
            "phone_label": "",
        }
        if not info["drive_connected"]:
            return info
        try:
            drive = self._drive_client()
            folder_id = self._vault_folder_id(drive)
            children, session_name, creds_name = self._active_vault_files(drive, folder_id)
            visible_names = {session_name, creds_name}
            if VAULT_MANIFEST_NAME in children:
                visible_names.add(VAULT_MANIFEST_NAME)
            files = [
                {
                    "name": name,
                    "size": int(meta.get("size") or 0),
                    "modified": str(meta.get("modifiedTime") or ""),
                }
                for name, meta in children.items()
                if name in visible_names
            ]
            files.sort(key=lambda item: item["name"])
            info["vault_files"] = files
            if creds_name in children:
                payload = json.loads(drive.download_bytes(children[creds_name]["id"]).decode("utf-8"))
                info["vault_format"] = int(payload.get("format", 0) or 0)
                info["saved_at"] = str(payload.get("saved_at") or "")
                info["phone_label"] = mask_phone(str(payload.get("phone") or ""))
        except Exception as exc:  # noqa: BLE001 - a read model never raises
            info["error"] = type(exc).__name__
        return info

    def forget_quiet(self) -> VaultResult:
        """Delete the vault without ever raising. Used by the logout handler.

        Logout must be final: leaving telegram.session + telegram_creds.json on
        Drive means the next page load restores the account the user just
        signed out of. A Drive hiccup here must still never block the logout.
        """
        try:
            if not getattr(self.ctx.drive_auth, "connected", False):
                return self._emit(VaultResult(False, "msg.session_restore_skipped_no_drive"))
            return self.forget()
        except Exception as exc:  # noqa: BLE001 - logout is more important
            _log.warning("session forget skipped: %s", type(exc).__name__)
            return self._emit(VaultResult(False, "err.session_vault_invalid"), type(exc).__name__)


_KEEPALIVE_JS = r"""
(function(){
  if (window.__tdKeepAlive) { return; }
  function tdClickConnect(){
    var hosts = [];
    try { hosts.push(document.querySelector('colab-connect-button')); } catch (e) {}
    try { hosts.push(document.querySelector('#top-toolbar colab-connect-button')); } catch (e) {}
    for (var i = 0; i < hosts.length; i++){
      var h = hosts[i];
      if (!h) { continue; }
      try { h.click(); } catch (e) {}
      try {
        var root = h.shadowRoot;
        if (!root) { continue; }
        var inner = root.querySelector('#connect')
          || root.querySelector('paper-button')
          || root.querySelector('colab-running-icon');
        if (inner) { inner.click(); }
      } catch (e) {}
    }
  }
  window.__tdKeepAlive = setInterval(tdClickConnect, 60000);
  tdClickConnect();
})();
"""
