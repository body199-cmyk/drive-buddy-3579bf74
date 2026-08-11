"""Telethon user-account client wrapper."""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

TELEGRAM_REQUEST_TIMEOUT_SECONDS = 30

from .config import TELEGRAM_SESSION
from .logging_config import get_logger

_log = get_logger("teledrive.telegram")

try:
    from telethon import TelegramClient
    from telethon.errors import (
        SessionPasswordNeededError,
        PhoneCodeInvalidError,
        FloodWaitError,
    )
    _TELETHON_AVAILABLE = True
except Exception:  # pragma: no cover
    TelegramClient = None  # type: ignore
    SessionPasswordNeededError = Exception  # type: ignore
    PhoneCodeInvalidError = Exception  # type: ignore
    FloodWaitError = Exception  # type: ignore
    _TELETHON_AVAILABLE = False


class TelegramService:
    def __init__(self, api_id: int, api_hash: str, session_path=str(TELEGRAM_SESSION)):
        if not _TELETHON_AVAILABLE:
            raise RuntimeError("telethon is not installed")
        self.api_id = int(api_id)
        self.api_hash = api_hash
        self.session_path = session_path
        self.client: Optional[TelegramClient] = None
        self._connected = False

    async def connect(self) -> None:
        if self.client is None:
            self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)
        if not self.client.is_connected():
            await self.client.connect()
        self._connected = True

    async def is_authorized(self) -> bool:
        if not self.client:
            return False
        return await self.client.is_user_authorized()

    async def start_login(self, phone: str) -> str:
        assert self.client
        sent = await asyncio.wait_for(
            self.client.send_code_request(phone),
            timeout=TELEGRAM_REQUEST_TIMEOUT_SECONDS,
        )
        return sent.phone_code_hash

    async def sign_in_code(self, phone: str, code: str, phone_code_hash: str):
        """Sign in reusing the EXACT phone_code_hash from send_code_request."""
        assert self.client
        return await self.client.sign_in(
            phone=phone, code=code, phone_code_hash=phone_code_hash
        )

    async def sign_in_password(self, password: str):
        """Second factor on the SAME client; never requests a new code."""
        assert self.client
        return await self.client.sign_in(password=password)

    async def complete_login(self, phone: str, code: str, password: Optional[str] = None) -> bool:
        assert self.client
        try:
            await self.client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            if not password:
                raise
            await self.client.sign_in(password=password)
        return await self.client.is_user_authorized()

    async def logout(self) -> None:
        if self.client:
            try:
                await self.client.log_out()
            except Exception:
                pass
            await self.client.disconnect()
        self._connected = False

    async def get_entity(self, chat: Any):
        assert self.client
        return await self.client.get_entity(chat)

    async def get_message(self, chat: Any, message_id: int):
        assert self.client
        return await self.client.get_messages(chat, ids=message_id)

    async def iter_messages(self, chat: Any, **kw):
        assert self.client
        async for m in self.client.iter_messages(chat, **kw):
            yield m

    async def download_media(
        self,
        message: Any,
        file_path: str,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        assert self.client
        path = await self.client.download_media(
            message, file=file_path, progress_callback=progress_cb
        )
        return path or file_path

    async def disconnect(self) -> None:
        if self.client:
            await self.client.disconnect()
