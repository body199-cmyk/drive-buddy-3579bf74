"""Telethon user-account client wrapper."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable, Optional

from .config import (
    DOWNLOAD_REQUEST_SIZE,
    PARALLEL_DOWNLOAD_MIN_BYTES,
    PARALLEL_DOWNLOAD_STREAMS,
    PARALLEL_DOWNLOAD_WINDOW_CHUNKS,
    TELEGRAM_SESSION,
)
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


def crypto_backend() -> str:
    """Report which AES-IGE implementation Telethon will use.

    Telethon decrypts every MTProto media chunk. It prefers ``cryptg`` when
    installed, then the system libssl binding, and only then pure Python
    ``pyaes``. Exposing the answer in the log makes a slow transfer
    diagnosable without guessing. Never raises.
    """
    try:
        import cryptg  # noqa: F401
        return "cryptg"
    except Exception:
        pass
    try:
        from telethon.crypto import libssl

        if getattr(libssl, "decrypt_ige", None) and getattr(libssl, "encrypt_ige", None):
            return "libssl"
    except Exception:
        pass
    return "pyaes"


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
        # The whole context shares one Telegram client. Cap outstanding media
        # requests globally even when several queue workers are active.
        self._download_request_slots = asyncio.Semaphore(PARALLEL_DOWNLOAD_STREAMS)

    async def connect(self) -> None:
        self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)
        await self.client.connect()
        self._connected = True
        _log.info("telethon crypto backend=%s", crypto_backend())

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

    async def resolve_invite(self, invite_hash: str):
        """Resolve an already-authorized private invite without joining it.

        ``CheckChatInviteRequest`` returns ``chat`` only when this user is
        already a participant. An invite that would require joining stays a
        refusal, so Analyze never changes Telegram membership as a side effect.
        """
        assert self.client
        from telethon.tl.functions.messages import CheckChatInviteRequest

        checked = await self.client(CheckChatInviteRequest(str(invite_hash)))
        chat = getattr(checked, "chat", None)
        if chat is None:
            from .errors import PrivateChannelUnresolvedError

            raise PrivateChannelUnresolvedError(
                "private invite requires membership from the signed-in account"
            )
        return await self.resolve_entity(chat)

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

    async def _download_media_parallel(
        self,
        media: Any,
        path: Path,
        total: int,
        progress_cb: Optional[Callable[[int, int], None]],
    ) -> str:
        """Fetch a large file with two bounded MTProto range readers.

        Each reader requests disjoint 512 KiB stripes. A bounded reorder window
        writes only the contiguous prefix to the .part file, so pause/stop leaves
        a normal resumable prefix rather than sparse/out-of-order bytes. Any
        transport/validation error propagates to the caller's legacy fallback.
        """
        request_size = DOWNLOAD_REQUEST_SIZE
        streams = min(PARALLEL_DOWNLOAD_STREAMS, (total + request_size - 1) // request_size)
        if streams < 2:
            return await self._download_media_sequential(media, path, total, progress_cb)

        stride = streams * request_size
        work: list[tuple[int, int]] = []
        for lane in range(streams):
            start = lane * request_size
            if start >= total:
                continue
            count = (total - start + stride - 1) // stride
            work.append((start, count))

        queue: asyncio.Queue = asyncio.Queue(maxsize=PARALLEL_DOWNLOAD_WINDOW_CHUNKS)
        window = asyncio.Semaphore(PARALLEL_DOWNLOAD_WINDOW_CHUNKS)
        request_slots = self._download_request_slots
        _log.info(
            "parallel download start bytes=%s streams=%s request_size=%s",
            total,
            len(work),
            request_size,
        )
        sentinel = object()
        lanes_finished = 0
        next_offset = 0
        pending: dict[int, bytes] = {}
        tasks: list[asyncio.Task] = []

        async def produce(start: int, count: int) -> None:
            offset = start
            try:
                stream = self.client.iter_download(
                    media,
                    offset=start,
                    stride=stride,
                    limit=count,
                    chunk_size=request_size,
                    request_size=request_size,
                    file_size=total,
                )
                async with stream:
                    iterator = stream.__aiter__()
                    for _ in range(count):
                        await window.acquire()
                        try:
                            async with request_slots:
                                chunk = await iterator.__anext__()
                        except StopAsyncIteration as exc:
                            window.release()
                            raise RuntimeError("parallel Telegram stream ended early") from exc
                        except BaseException:
                            window.release()
                            raise
                        expected = min(request_size, total - offset)
                        if len(chunk) != expected:
                            window.release()
                            raise RuntimeError(
                                f"parallel Telegram chunk size mismatch: expected {expected}, got {len(chunk)}"
                            )
                        await queue.put(("chunk", offset, bytes(chunk)))
                        offset += stride
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await queue.put(("error", exc))
                return
            await queue.put(("done", sentinel))

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as handle:
            tasks = [asyncio.create_task(produce(start, count)) for start, count in work]
            try:
                while lanes_finished < len(work):
                    entry = await queue.get()
                    if entry[0] == "error":
                        raise entry[1]
                    if entry[0] == "done":
                        lanes_finished += 1
                        continue

                    _, offset, chunk = entry
                    if offset < next_offset or offset in pending:
                        raise RuntimeError("parallel Telegram stream returned overlapping ranges")
                    pending[offset] = chunk
                    while next_offset in pending:
                        contiguous = pending.pop(next_offset)
                        handle.write(contiguous)
                        next_offset += len(contiguous)
                        if progress_cb:
                            progress_cb(next_offset, total)
                        window.release()

                if next_offset != total or pending:
                    raise RuntimeError(
                        f"parallel Telegram download incomplete: wrote {next_offset} of {total} bytes"
                    )
                handle.flush()
            except BaseException:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise
            else:
                await asyncio.gather(*tasks)

        _log.info(
            "parallel download complete bytes=%s streams=%s request_size=%s",
            total,
            streams,
            request_size,
        )
        return str(path)

    async def _download_media_sequential(
        self,
        media: Any,
        path: Path,
        total: int,
        progress_cb: Optional[Callable[[int, int], None]],
    ) -> str:
        """One ordered reader used for small media and safe fallback."""
        written = 0
        with open(path, "wb") as handle:
            async for chunk in self.client.iter_download(
                media,
                request_size=DOWNLOAD_REQUEST_SIZE,
                file_size=total or None,
            ):
                handle.write(chunk)
                written += len(chunk)
                if progress_cb:
                    progress_cb(written, total or written)
            handle.flush()
        return str(path)

    async def download_media_fast(
        self,
        message: Any,
        file_path: str,
        total_size: int,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """Download a fresh media file at the MTProto maximum request size.

        Telethon's public :meth:`download_media` picks 128 KiB requests for
        files up to 100 MB. This path always uses the 512 KiB MTProto maximum;
        files >= 32 MiB use two bounded, interleaved range readers while the
        writer commits only contiguous bytes to the partial file. Smaller media
        stays sequential. Pause/stop therefore leaves a valid prefix.

        The caller owns the fallback: :class:`TransferManager` retries the
        legacy path if this raises. A control signal raised by ``progress_cb``
        is never caught here.
        """
        assert self.client
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        media = getattr(message, "media", None) or message
        total = int(total_size or 0)
        if total >= PARALLEL_DOWNLOAD_MIN_BYTES:
            return await self._download_media_parallel(media, path, total, progress_cb)
        result = await self._download_media_sequential(media, path, total, progress_cb)
        _log.info(
            "fast download complete bytes=%s request_size=%s",
            path.stat().st_size,
            DOWNLOAD_REQUEST_SIZE,
        )
        return result

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
            async for chunk in self.client.iter_download(
                media,
                offset=offset,
                request_size=DOWNLOAD_REQUEST_SIZE,
                file_size=total or None,
            ):
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
