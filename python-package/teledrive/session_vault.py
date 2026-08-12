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
