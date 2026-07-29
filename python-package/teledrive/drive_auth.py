"""Native Google Colab Drive authentication (Constitution Section 6).

The ONLY allowed path:
    colab_auth.authenticate_user() -> google.auth.default(scopes=[drive])
    -> build("drive", "v3", ...) -> about().get() gate.

Uploaded OAuth desktop client JSON, paste-the-code textboxes and persisted
drive_token.json are forbidden and no longer exist in this package.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from . import database as db
from .errors import DriveNotReadyError, TeleDriveError
from .logging_config import get_logger
from .redaction import safe_exception

_log = get_logger("teledrive.drive_auth")

SCOPES = ["https://www.googleapis.com/auth/drive"]
ABOUT_FIELDS = "user(displayName,emailAddress),storageQuota(limit,usage)"

DISCONNECTED = "DISCONNECTED"
AUTHENTICATING = "AUTHENTICATING"
VERIFYING = "VERIFYING"
CONNECTED = "CONNECTED"
ERROR = "ERROR"


@dataclass
class DriveStatus:
    state: str = DISCONNECTED
    connected: bool = False
    account_label: str = ""
    quota: dict = field(default_factory=dict)
    message_key: str = "status.disconnected"


def _native_colab_service():
    """Build the Drive service through native Colab credentials only."""
    from google.colab import auth as colab_auth  # noqa: PLC0415 — Colab-only import
    import google.auth  # noqa: PLC0415
    from googleapiclient.discovery import build  # noqa: PLC0415

    colab_auth.authenticate_user(clear_output=False)
    creds, _ = google.auth.default(scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


class DriveAuth:
    """Owns the ONE Drive service. No other object may construct one."""

    def __init__(self, ctx, service_factory: Optional[Callable[[], Any]] = None) -> None:
        self.ctx = ctx
        self._factory = service_factory or _native_colab_service
        self._lock = threading.RLock()
        self.state = DISCONNECTED
        self.service: Any = None
        self.account_label = ""
        self.quota: dict[str, int] = {}

    # ---- actions ----

    def connect(self) -> DriveStatus:
        with self._lock:
            self.state = AUTHENTICATING
            self.ctx.ui_state.drive_status = self.state
            try:
                service = self._factory()
            except BaseException as exc:  # noqa: BLE001
                return self._fail(exc)
            return self._verify_and_store(service)

    def _verify_and_store(self, service: Any) -> DriveStatus:
        """The about().get() gate. Nothing reports Connected before it passes."""
        self.state = VERIFYING
        try:
            about = service.about().get(fields=ABOUT_FIELDS).execute()
        except BaseException as exc:  # noqa: BLE001
            self.service = None
            return self._fail(exc)
        self.service = service
        user = (about or {}).get("user", {}) or {}
        self.account_label = user.get("emailAddress") or user.get("displayName") or ""
        quota = (about or {}).get("storageQuota", {}) or {}
        self.quota = {
            "limit": int(quota.get("limit", 0) or 0),
            "usage": int(quota.get("usage", 0) or 0),
        }
        self.state = CONNECTED
        self.ctx.ui_state.drive_status = self.state
        self.ctx.auth.set_drive(self, self.account_label)
        db.add_event("", "auth.drive", "connected", {"account": self.account_label})
        _log.info("drive connected account=%s", self.account_label)
        return self.status()

    def adopt_service(self, service: Any) -> DriveStatus:
        """Inject an externally built Drive service into THIS context.

        Used by the Colab notebook, where cell 3 performs the native
        authorization. The service still has to pass the ``about().get()``
        gate here before anything may report Connected, and it becomes the one
        and only Drive service owned by the single ApplicationContext.
        """
        with self._lock:
            if service is None:
                raise TeleDriveError("no drive service provided", "err.drive_auth_failed")
            return self._verify_and_store(service)

    def reconnect(self) -> DriveStatus:
        """Account switching requires an explicit restart + re-auth, never a
        silent credential swap: we drop the service first, then re-run the gate."""
        with self._lock:
            self.service = None
            self.account_label = ""
            self.quota = {}
            self.state = DISCONNECTED
            self.ctx.auth.clear_drive()
        return self.connect()

    def _fail(self, exc: BaseException) -> DriveStatus:
        self.state = ERROR
        self.ctx.ui_state.drive_status = self.state
        message = safe_exception(exc)
        _log.warning("drive auth failed: %s", message)
        db.add_event("", "auth.drive", "failed", {"error": message})
        raise TeleDriveError(message, "err.drive_auth_failed")

    # ---- read-only ----

    @property
    def connected(self) -> bool:
        return self.state == CONNECTED and self.service is not None

    def require_service(self):
        if not self.connected:
            raise DriveNotReadyError("drive is not connected")
        return self.service

    def storage_quota(self) -> dict[str, int]:
        service = self.require_service()
        about = service.about().get(fields=ABOUT_FIELDS).execute()
        quota = (about or {}).get("storageQuota", {}) or {}
        self.quota = {
            "limit": int(quota.get("limit", 0) or 0),
            "usage": int(quota.get("usage", 0) or 0),
        }
        return self.quota

    def status(self) -> DriveStatus:
        return DriveStatus(
            state=self.state,
            connected=self.connected,
            account_label=self.account_label,
            quota=dict(self.quota),
            message_key="status.connected" if self.connected else "status.disconnected",
        )

    # revoke() keeps AuthManager.clear_drive() working; no token file exists.
    def revoke(self) -> None:
        self.service = None
        self.state = DISCONNECTED
        self.account_label = ""
