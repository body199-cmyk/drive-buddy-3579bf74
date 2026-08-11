"""Typed error taxonomy for the binding contract and services."""
from __future__ import annotations


class TeleDriveError(Exception):
    """Base class. Carries a locale key so the UI never renders raw text."""

    message_key = "err.unknown"

    def __init__(self, message: str = "", message_key: str | None = None):
        super().__init__(message or self.message_key)
        if message_key:
            self.message_key = message_key


class UnknownActionError(TeleDriveError):
    """A component was wired to an action_id that is not in ACTION_SPECS."""

    message_key = "err.unknown_action"


class DeadControlError(TeleDriveError):
    """A control was wired to an action that is not implemented AND tested."""

    message_key = "err.dead_control"


class ServicePathError(TeleDriveError):
    """A service_path does not resolve to a callable on the live context."""

    message_key = "err.service_path"


class IncompleteBindingError(TeleDriveError):
    """A ready action was never wired to a control."""

    message_key = "err.incomplete_binding"


class AuthStateError(TeleDriveError):
    """An auth action was requested from an illegal state."""

    message_key = "err.auth_state"


class DriveNotReadyError(TeleDriveError):
    message_key = "err.drive_not_ready"


class TelegramNotReadyError(TeleDriveError):
    message_key = "err.reauth"


class TelegramCodeSendError(TeleDriveError):
    """Telegram code request failed after the bounded retry policy."""
    message_key = "err.tg_code_send_failed"


class QuotaRefusedError(TeleDriveError):
    message_key = "err.drive_full"


class LocalDiskError(TeleDriveError):
    message_key = "err.disk_full"


class CooldownError(TeleDriveError):
    message_key = "err.cooldown"


class NothingSelectedError(TeleDriveError):
    message_key = "err.nothing_selected"


class CheckpointError(TeleDriveError):
    """Durable checkpoint export failed. Temp files MUST be kept."""
    message_key = "err.checkpoint_failed"


class VerificationError(TeleDriveError):
    """Drive-side verification of an uploaded file failed."""
    message_key = "err.verify_failed"
