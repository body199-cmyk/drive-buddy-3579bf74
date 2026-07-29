"""High-level auth glue: hold Telegram + Drive service instances for the app."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AuthState:
    telegram_authorized: bool = False
    drive_authorized: bool = False
    telegram_user: str = ""
    drive_user: str = ""


class AuthManager:
    def __init__(self):
        self.telegram = None
        self.drive = None
        self.state = AuthState()

    def set_telegram(self, service, user: str = "") -> None:
        self.telegram = service
        self.state.telegram_authorized = service is not None
        self.state.telegram_user = user

    def set_drive(self, service, user: str = "") -> None:
        self.drive = service
        self.state.drive_authorized = service is not None
        self.state.drive_user = user

    def clear_telegram(self) -> None:
        self.telegram = None
        self.state.telegram_authorized = False
        self.state.telegram_user = ""

    def clear_drive(self) -> None:
        if self.drive:
            try:
                self.drive.revoke()
            except Exception:
                pass
        self.drive = None
        self.state.drive_authorized = False
        self.state.drive_user = ""


AUTH = AuthManager()
