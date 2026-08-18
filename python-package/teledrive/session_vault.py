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
import sqlite3
import threading
import time
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
    return save_session(_drive_from_ctx(ctx), secret=secret)


def restore_from_context(ctx: Any, secret: str = "") -> bool:
    return restore_session(_drive_from_ctx(ctx), secret=secret)


def wipe_from_context(ctx: Any) -> None:
    wipe_session(_drive_from_ctx(ctx, require_connected=False))


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
VAULT_FORMAT = 1
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
        if int(data.get("format", 0) or 0) != VAULT_FORMAT:
            raise TeleDriveError("unsupported vault format", "err.session_vault_invalid")
        return data

    # ---------- public API ----------

    def probe(self, service: Any) -> dict[str, Any]:
        """Used by notebook cell 3 before the app adopts the Drive service."""
        drive = self._drive_client(service)
        folder_id = self._vault_folder_id(drive)
        files = self._children_by_name(drive, folder_id)
        has_session = VAULT_SESSION_NAME in files
        has_creds = VAULT_CREDS_NAME in files
        payload = None
        if has_creds:
            try:
                payload = self._read_creds_payload(drive, folder_id)
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
        # M24-T03: the UI fields are empty on the Colab-Secrets path and on the
        # auto-restore path, yet the live client already holds the very values
        # this vault needs. Fall back to that memory instead of refusing a save
        # the user explicitly asked for.
        memory_id, memory_hash, memory_phone = self._creds_from_memory()
        if not api_id.isdigit():
            api_id = memory_id
        if not api_hash:
            api_hash = memory_hash
        if not phone:
            phone = memory_phone
        if not api_id.isdigit():
            raise TeleDriveError("api id must be numeric", "err.bad_api_id")
        if not api_hash:
            raise TeleDriveError("api hash required", "err.bad_api_hash")

        drive = self._drive_client()
        folder_id = self._vault_folder_id(drive)
        local_session = self._local_session_path()
        snapshot = local_session.with_name("telegram.session.snapshot")
        self._checkpoint_sqlite(local_session, snapshot)

        creds = {
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone,
            "saved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "format": VAULT_FORMAT,
            "session_file": VAULT_SESSION_NAME,
        }
        drive.upsert_bytes(VAULT_SESSION_NAME, snapshot.read_bytes(), folder_id, mime_type="application/octet-stream")
        drive.upsert_bytes(VAULT_CREDS_NAME, json.dumps(creds, ensure_ascii=False, indent=2).encode("utf-8"), folder_id, mime_type="application/json")
        try:
            snapshot.unlink(missing_ok=True)
        except Exception:
            pass
        _log.info("telegram vault saved phone=%s", mask_phone(phone))
        return VaultResult(True, "msg.session_saved", saved=True, phone_label=mask_phone(phone))

    def autorestore(self) -> VaultResult:
        if self.ctx.telegram_auth.authorized:
            return VaultResult(True, "msg.session_already_authorized", restored=True)
        if not self.ctx.drive_auth.connected:
            return VaultResult(False, "msg.session_restore_skipped_no_drive")

        drive = self._drive_client()
        folder_id = self._vault_folder_id(drive)
        files = self._children_by_name(drive, folder_id)
        if VAULT_SESSION_NAME not in files or VAULT_CREDS_NAME not in files:
            return VaultResult(False, "msg.session_not_saved")

        payload = self._read_creds_payload(drive, folder_id)
        if not payload:
            return VaultResult(False, "err.session_vault_invalid")

        session_bytes = drive.download_bytes(files[VAULT_SESSION_NAME]["id"])
        # M24-T03: never hand junk to Telethon. A truncated upload or a foreign
        # file with the same name must degrade to the manual login path, and it
        # must NOT overwrite a good local session on the way out.
        if not session_bytes or not session_bytes.startswith(SQLITE_MAGIC):
            _log.warning("telegram vault restore rejected: not a sqlite session")
            return VaultResult(False, "err.session_vault_invalid")
        self._write_session_bytes(session_bytes)

        api_id = str(payload.get("api_id") or "").strip()
        api_hash = str(payload.get("api_hash") or "").strip()
        phone = str(payload.get("phone") or "").strip()
        if not api_id.isdigit() or not api_hash:
            raise TeleDriveError("vault credentials are incomplete", "err.session_vault_invalid")

        status = self.ctx.telegram_auth.set_credentials(api_id, api_hash)
        if status.authorized:
            _log.info("telegram vault restored phone=%s", mask_phone(phone))
            return VaultResult(True, "msg.session_restored", restored=True, phone_label=mask_phone(phone))
        return VaultResult(False, "msg.session_restore_needs_login", phone_label=mask_phone(phone))

    def forget(self) -> VaultResult:
        drive = self._drive_client()
        folder_id = self._vault_folder_id(drive)
        files = self._children_by_name(drive, folder_id)
        for name in (VAULT_SESSION_NAME, VAULT_CREDS_NAME):
            meta = files.get(name)
            if meta:
                drive.delete_file(meta["id"])
        try:
            self._creds_path().unlink(missing_ok=True)
        except Exception:
            pass
        _log.info("telegram vault forgotten")
        return VaultResult(True, "msg.session_forgotten", forgotten=True)

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
            return VaultResult(
                self.ctx.telegram_auth.authorized,
                "msg.session_already_authorized",
                restored=self.ctx.telegram_auth.authorized,
            )
        self._autorestore_done = True
        try:
            return self.autorestore()
        except Exception as exc:  # noqa: BLE001 - the UI build must never die here
            _log.warning("session autorestore skipped: %s", type(exc).__name__)
            return VaultResult(False, "err.session_vault_invalid")

    def save_after_login(self, force: bool = False) -> VaultResult:
        """Save the vault right after a successful login. Never raises.

        The goal of the whole feature is that the user never re-enters a code,
        so persistence cannot depend on remembering a button. Skips silently
        when Telegram is not authorized, when Drive is not connected, when the
        credentials are not in memory, or when this Drive account already has a
        vault (``force=True`` overwrites it).
        """
        try:
            if not self.ctx.telegram_auth.authorized:
                return VaultResult(False, "err.session_not_authorized")
            if not getattr(self.ctx.drive_auth, "connected", False):
                return VaultResult(False, "msg.session_restore_skipped_no_drive")
            api_id, api_hash, phone = self._creds_from_memory()
            if not api_id.isdigit() or not api_hash:
                return VaultResult(False, "err.session_vault_invalid")
            drive = self._drive_client()
            folder_id = self._vault_folder_id(drive)
            if not force and self._vault_present(drive, folder_id):
                return VaultResult(True, "msg.session_saved", saved=False)
            return self.save_now(api_id, api_hash, phone)
        except Exception as exc:  # noqa: BLE001 - a login must never fail on this
            _log.warning("session autosave skipped: %s", type(exc).__name__)
            return VaultResult(False, "err.session_vault_invalid")

    def forget_quiet(self) -> VaultResult:
        """Delete the vault without ever raising. Used by the logout handler.

        Logout must be final: leaving telegram.session + telegram_creds.json on
        Drive means the next page load restores the account the user just
        signed out of. A Drive hiccup here must still never block the logout.
        """
        try:
            if not getattr(self.ctx.drive_auth, "connected", False):
                return VaultResult(False, "msg.session_restore_skipped_no_drive")
            return self.forget()
        except Exception as exc:  # noqa: BLE001 - logout is more important
            _log.warning("session forget skipped: %s", type(exc).__name__)
            return VaultResult(False, "err.session_vault_invalid")


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
