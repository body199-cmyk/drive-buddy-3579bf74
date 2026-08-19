"""Telethon user-account client wrapper."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable, Optional

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
    #: A bounded, one-shot dialog read fills Telethon's local entity cache.
    ENTITY_CACHE_WARM_LIMIT = 200
    #: Telethon download offsets must align to this boundary.
    DOWNLOAD_ALIGN = 4096

    def __init__(self, api_id: int, api_hash: str, session_path=str(TELEGRAM_SESSION)):
        if not _TELETHON_AVAILABLE:
            raise RuntimeError("telethon is not installed")
        self.api_id = int(api_id)
        self.api_hash = api_hash
        self.session_path = session_path
        self.client: Optional[TelegramClient] = None
        self._connected = False
        self._entity_cache_warmed = False

    async def connect(self) -> None:
        self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)
        await self.client.connect()
        self._connected = True

    async def is_authorized(self) -> bool:
        if not self.client:
            return False
        return await self.client.is_user_authorized()

    async def start_login(self, phone: str) -> str:
        assert self.client
        sent = await self.client.send_code_request(phone)
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

    async def resolve_entity(self, chat: Any):
        """Return an InputPeer, warming the bounded local dialog cache once.

        A restored session can be authorized while its in-memory entity cache
        lacks an internal private-channel id. The warm-up reads only the
        account's own dialog metadata and never fetches messages.
        """

        assert self.client
        try:
            return await self.client.get_input_entity(chat)
        except ValueError as first:
            _log.info("entity cache miss (%s); warming dialogs once", type(first).__name__)
        if not self._entity_cache_warmed:
            self._entity_cache_warmed = True
            try:
                async for _dialog in self.client.iter_dialogs(
                    limit=self.ENTITY_CACHE_WARM_LIMIT
                ):
                    pass
            except Exception as warm_exc:  # best effort; final resolution decides
                _log.warning("dialog warm failed: %s", type(warm_exc).__name__)
        try:
            return await self.client.get_input_entity(chat)
        except ValueError as second:
            from .errors import PrivateChannelUnresolvedError

            raise PrivateChannelUnresolvedError(
                "no access to this Telegram chat from the signed-in account "
                f"({type(second).__name__})"
            ) from second

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

    async def download_partial(
        self,
        message: Any,
        file_path: str,
        total_size: int,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """Continue a non-empty local partial from Telethon's aligned offset.

        The existing partial is truncated only down to the mandatory alignment
        boundary; it is never deleted. If no usable offset exists, the normal
        full-download path remains authoritative.
        """

        assert self.client
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        offset = path.stat().st_size if path.exists() else 0
        offset -= offset % self.DOWNLOAD_ALIGN
        if offset <= 0:
            return await self.download_media(message, file_path, progress_cb=progress_cb)
        media = getattr(message, "media", None) or message
        total = int(total_size or 0)
        current = offset
        with open(path, "r+b") as handle:
            handle.truncate(offset)
            handle.seek(offset)
            async for chunk in self.client.iter_download(media, offset=offset):
                handle.write(chunk)
                current += len(chunk)
                if progress_cb:
                    progress_cb(current, total or current)
            handle.flush()
        _log.info("resumed download from offset=%s", offset)
        return str(path)

    async def disconnect(self) -> None:
        if self.client:
            await self.client.disconnect()
