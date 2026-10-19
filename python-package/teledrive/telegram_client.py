"""Telethon user-account client wrapper."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Optional

from .config import (
    DOWNLOAD_REQUEST_SIZE,
    PARALLEL_DOWNLOAD_MIN_BYTES,
    PARALLEL_DOWNLOAD_STREAMS,
    PARALLEL_DOWNLOAD_WINDOW_CHUNKS,
    TELEGRAM_SESSION,
    TG_INFLIGHT_REQUESTS,
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
        # M45-T01: the cap is TG_INFLIGHT_REQUESTS (not the per-file stream
        # count). Before this, only the striped readers respected a bound and
        # every small file opened its own unbounded GetFile stream, which is
        # exactly the "Request was unsuccessful 6 time(s)" flood.
        self._download_request_slots = asyncio.Semaphore(TG_INFLIGHT_REQUESTS)
        self._media_clients: list[Any] = []
        self._media_pool_lock: Optional[asyncio.Lock] = None

    def _request_slots(self) -> asyncio.Semaphore:
        """Lazily create the global GetFile budget.

        Tests build the service with ``object.__new__`` and may not run
        ``__init__``; a single lazy accessor keeps every download path safe
        without duplicating semaphore bookkeeping.
        """
        slots = getattr(self, "_download_request_slots", None)
        if slots is None:
            slots = asyncio.Semaphore(TG_INFLIGHT_REQUESTS)
            self._download_request_slots = slots
        return slots

    async def _get_lane_client(self, lane: int) -> Any:
        """Return an independent MTProto client for ``lane`` when possible.

        M45-T03: a single TelegramClient multiplexes all GetFile requests over
        one TCP socket, which caps Colab throughput at ~1-2 MB/s. Lane 0 uses
        the primary client; lanes >= 1 use a lazily connected pool of in-memory
        MemorySession clients sharing the authorized DC auth_key (with
        ``receive_updates=False`` so neither the SQLite session file nor update
        state is touched). If the session is a test double or secondary
        connection setup fails, falls back transparently to ``self.client``.
        """
        if lane <= 0 or self.client is None:
            return self.client
        pool = getattr(self, "_media_clients", None)
        if pool is None:
            pool = []
            self._media_clients = pool
        idx = lane - 1
        if idx < len(pool) and pool[idx] is not None:
            return pool[idx]

        session = getattr(self.client, "session", None)
        auth_key = getattr(session, "auth_key", None)
        dc_id = getattr(session, "dc_id", None)
        server_address = getattr(session, "server_address", None)
        port = getattr(session, "port", None)
        if not (auth_key and getattr(auth_key, "key", None) and dc_id and server_address and port):
            return self.client
        if TelegramClient is None or not getattr(self, "api_id", None) or not getattr(self, "api_hash", None):
            return self.client

        lock = getattr(self, "_media_pool_lock", None)
        if lock is None:
            lock = asyncio.Lock()
            self._media_pool_lock = lock

        async with lock:
            if idx < len(pool) and pool[idx] is not None:
                return pool[idx]
            try:
                from telethon.sessions import MemorySession

                while len(pool) <= idx:
                    mem = MemorySession()
                    mem.set_dc(dc_id, server_address, port)
                    mem.auth_key = auth_key
                    try:
                        worker = TelegramClient(
                            mem,
                            self.api_id,
                            self.api_hash,
                            receive_updates=False,
                            request_retries=5,
                            connection_retries=5,
                            retry_delay=1,
                            flood_sleep_threshold=60,
                            auto_reconnect=True,
                        )
                    except TypeError:
                        worker = TelegramClient(mem, self.api_id, self.api_hash)
                    await worker.connect()
                    pool.append(worker)
                _log.info("connected MTProto media worker lane=%s pool_size=%s", lane, len(pool))
                return pool[idx]
            except Exception as exc:
                _log.debug("media worker lane=%s unavailable (%s); using primary client", lane, type(exc).__name__)
                return self.client

    async def _close_media_pool(self) -> None:
        pool = list(getattr(self, "_media_clients", None) or [])
        if hasattr(self, "_media_clients") and self._media_clients is not None:
            self._media_clients.clear()
        for worker in pool:
            if worker is not None:
                try:
                    await worker.disconnect()
                except Exception:
                    pass

    async def connect(self) -> None:
        # M45-T01: retrying a timed-out GetFile is what turns one slow socket
        # into a stalled queue. Telethon accepts these resiliency options, but
        # a test double / older Telethon build may not; fall back safely.
        try:
            self.client = TelegramClient(
                self.session_path,
                self.api_id,
                self.api_hash,
                request_retries=10,
                connection_retries=10,
                retry_delay=1,
                flood_sleep_threshold=60,
                auto_reconnect=True,
            )
        except TypeError:
            self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)
        await self.client.connect()
        self._connected = True
        _log.info(
            "telethon crypto backend=%s inflight_cap=%s",
            crypto_backend(),
            TG_INFLIGHT_REQUESTS,
        )

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
        await self._close_media_pool()
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
        start_at: int = 0,
    ) -> str:
        """Fetch a large file with bounded interleaved MTProto range readers.

        Each reader requests disjoint 512 KiB stripes. A bounded reorder window
        writes only the contiguous prefix to the .part file, so pause/stop (and
        a dropped socket) leaves a normal resumable prefix rather than
        sparse/out-of-order bytes. ``start_at`` must be 512 KiB aligned; the
        caller (download_partial) guarantees that.

        Any transport/validation error propagates to the retry path, which
        resumes from the prefix on disk instead of discarding it.
        """
        request_size = DOWNLOAD_REQUEST_SIZE
        start_at = max(0, int(start_at))
        started_at = time.monotonic()
        remaining = max(0, total - start_at)
        streams = min(
            PARALLEL_DOWNLOAD_STREAMS,
            (remaining + request_size - 1) // request_size,
        )
        if streams < 2:
            return await self._download_media_sequential(
                media, path, total, progress_cb, start_at=start_at
            )

        stride = streams * request_size
        work: list[tuple[int, int]] = []
        for lane in range(streams):
            start = start_at + lane * request_size
            if start >= total:
                continue
            count = (total - start + stride - 1) // stride
            work.append((start, count))

        queue: asyncio.Queue = asyncio.Queue(maxsize=PARALLEL_DOWNLOAD_WINDOW_CHUNKS)
        window = asyncio.Semaphore(PARALLEL_DOWNLOAD_WINDOW_CHUNKS)
        request_slots = self._request_slots()
        _log.info(
            "parallel download start bytes=%s offset=%s streams=%s request_size=%s",
            total,
            start_at,
            len(work),
            request_size,
        )
        sentinel = object()
        lanes_finished = 0
        next_offset = start_at
        pending: dict[int, bytes] = {}
        tasks: list[asyncio.Task] = []

        async def _stream_from_client(client_obj: Any, start_offset: int, remaining_count: int) -> int:
            offset = start_offset
            done_chunks = 0
            stream = client_obj.iter_download(
                media,
                offset=start_offset,
                stride=stride,
                limit=remaining_count,
                chunk_size=request_size,
                request_size=request_size,
                file_size=total,
            )
            async with stream:
                iterator = stream.__aiter__()
                for _ in range(remaining_count):
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
                    done_chunks += 1
            return done_chunks

        async def produce(lane: int, start: int, count: int) -> None:
            try:
                lane_client = await self._get_lane_client(lane)
                if lane_client is not self.client:
                    done_chunks = 0
                    try:
                        done_chunks = await _stream_from_client(lane_client, start, count)
                    except asyncio.CancelledError:
                        raise
                    except Exception as worker_exc:
                        # Secondary socket failed (e.g. foreign DC media);
                        # seamlessly continue the remaining stripes on self.client!
                        _log.debug(
                            "lane=%s secondary client fallback after %s/%s chunks (%s)",
                            lane,
                            done_chunks,
                            count,
                            type(worker_exc).__name__,
                        )
                        rem = count - done_chunks
                        if rem > 0:
                            await _stream_from_client(
                                self.client, start + done_chunks * stride, rem
                            )
                else:
                    await _stream_from_client(self.client, start, count)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await queue.put(("error", exc))
                return
            await queue.put(("done", sentinel))

        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "r+b" if start_at and path.exists() else "wb"
        with open(path, mode, buffering=4 * 1024 * 1024) as handle:
            if start_at:
                handle.truncate(start_at)
                handle.seek(start_at)
            tasks = [
                asyncio.create_task(produce(lane, start, count))
                for lane, (start, count) in enumerate(work)
            ]
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
                        # Release the sliding window permit BEFORE progress_cb so
                        # SQLite progress writes never stall producer lanes.
                        window.release()
                        if progress_cb:
                            progress_cb(next_offset, total)

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

        elapsed = max(1e-6, time.monotonic() - started_at)
        _log.info(
            "parallel download complete bytes=%s streams=%s request_size=%s "
            "seconds=%.2f mbps=%.2f",
            total,
            streams,
            request_size,
            elapsed,
            (max(0, total - start_at) / (1024 * 1024)) / elapsed,
        )
        return str(path)

    async def _download_media_sequential(
        self,
        media: Any,
        path: Path,
        total: int,
        progress_cb: Optional[Callable[[int, int], None]],
        start_at: int = 0,
    ) -> str:
        """One ordered 512 KiB reader used for small media and safe resume.

        The global in-flight budget is held for the whole ordered read, so a
        queue full of small files can never open more GetFile streams than
        ``TG_INFLIGHT_REQUESTS`` on the single MTProto connection.
        """
        start_at = max(0, int(start_at))
        written = start_at
        mode = "r+b" if start_at and path.exists() else "wb"
        with open(path, mode, buffering=4 * 1024 * 1024) as handle:
            if start_at:
                handle.truncate(start_at)
                handle.seek(start_at)
            async with self._request_slots():
                async for chunk in self.client.iter_download(
                    media,
                    offset=start_at,
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
        files >= 32 MiB use bounded, interleaved range readers while the
        writer commits only contiguous bytes to the partial file. Smaller media
        stays sequential. Pause/stop therefore leaves a valid prefix.

        The caller owns the retry decision: :class:`TransferManager` resumes a
        non-trivial prefix instead of overwriting it. A control signal raised
        by ``progress_cb`` is never caught here.
        """
        assert self.client
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        media = getattr(message, "media", None) or message
        total = int(total_size or 0)
        if total >= PARALLEL_DOWNLOAD_MIN_BYTES:
            return await self._download_media_parallel(media, path, total, progress_cb)
        started = time.monotonic()
        result = await self._download_media_sequential(media, path, total, progress_cb)
        elapsed = max(1e-6, time.monotonic() - started)
        size = path.stat().st_size
        _log.info(
            "fast download complete bytes=%s request_size=%s seconds=%.2f mbps=%.2f",
            size,
            DOWNLOAD_REQUEST_SIZE,
            elapsed,
            (size / (1024 * 1024)) / elapsed,
        )
        return result

    async def download_partial(
        self,
        message: Any,
        file_path: str,
        total_size: int,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """Continue a non-empty local partial from a protocol-valid offset.

        Telegram rejects a 512 KiB GetFile request whose offset+limit crosses
        a 1 MiB window (``An invalid limit was provided``). Aligning the
        offset down to the request size keeps every request inside one window.
        For files <= 512 KiB a 4 KiB alignment is still used, so the smallest
        media does not lose a whole request worth of progress.

        The existing partial is truncated only down to the alignment boundary;
        it is never deleted. Large remainders resume with the striped readers.
        """
        assert self.client
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        total = int(total_size or 0)
        align = (
            self.DOWNLOAD_ALIGN
            if (0 < total <= DOWNLOAD_REQUEST_SIZE)
            else max(self.DOWNLOAD_ALIGN, DOWNLOAD_REQUEST_SIZE)
        )
        offset = path.stat().st_size if path.exists() else 0
        offset -= offset % align
        if offset <= 0:
            if total >= DOWNLOAD_REQUEST_SIZE:
                return await self.download_media_fast(
                    message, file_path, total, progress_cb=progress_cb
                )
            return await self.download_media(message, file_path, progress_cb=progress_cb)
        media = getattr(message, "media", None) or message
        if total and total - offset >= PARALLEL_DOWNLOAD_MIN_BYTES:
            result = await self._download_media_parallel(
                media, path, total, progress_cb, start_at=offset
            )
        else:
            result = await self._download_media_sequential(
                media, path, total, progress_cb, start_at=offset
            )
        _log.info("resumed download from offset=%s", offset)
        return result

    async def disconnect(self) -> None:
        await self._close_media_pool()
        if self.client:
            await self.client.disconnect()
