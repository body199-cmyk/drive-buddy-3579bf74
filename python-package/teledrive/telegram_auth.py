"""Telegram authentication state machine (Constitution Section 5 + ADR-004).

api_id / api_hash / phone / OTP / 2FA stay in protected memory. They are never
logged or checkpointed. After AUTHORIZED, the local Telethon session file may
be copied (obfuscated) to Drive AppData so a new Colab VM can resume without
OTP — owner-authorized by ADR-004. Logout deletes that blob.
Every coroutine runs on the one shared AsyncRuntime loop.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from . import database as db
from .config import TELEGRAM_SESSION
from .errors import AuthStateError, CooldownError, TeleDriveError
from .logging_config import get_logger
from .redaction import mask_phone, safe_exception

_log = get_logger("teledrive.telegram_auth")

DISCONNECTED = "DISCONNECTED"
READY_FOR_PHONE = "READY_FOR_PHONE"
SENDING_CODE = "SENDING_CODE"
CODE_REQUESTED = "CODE_REQUESTED"
VERIFYING_CODE = "VERIFYING_CODE"
PASSWORD_REQUIRED = "PASSWORD_REQUIRED"
VERIFYING_PASSWORD = "VERIFYING_PASSWORD"
AUTHORIZED = "AUTHORIZED"
REAUTH_REQUIRED = "REAUTH_REQUIRED"
ERROR = "ERROR"

STATES = (
    DISCONNECTED, READY_FOR_PHONE, SENDING_CODE, CODE_REQUESTED, VERIFYING_CODE,
    PASSWORD_REQUIRED, VERIFYING_PASSWORD, AUTHORIZED, REAUTH_REQUIRED, ERROR,
)

RESEND_COOLDOWN_SECONDS = 60

# M18-T03 — deep error classification (owner-authorized per §10 / KNOWN_ISSUES #40).
# Telethon's exception CLASSES stay unimported here, so the classifiers match by
# class NAME exactly like the FloodWaitError branch below; transport failures are
# matched by isinstance against stdlib network classes.
# (asyncio.IncompleteReadError subclasses EOFError; ConnectionError/TimeoutError
# subclass OSError — listed explicitly so the intent is greppable.)
_TRANSPORT_EXC = (ConnectionError, TimeoutError, OSError, EOFError)

# auth.sendCode RPC rejections → localized key. `err.bad_api_pair` means Telegram
# rejected the api_id/api_hash PAIR itself — auth.sendCode is the FIRST call that
# carries both halves, so a bad pair fails here, not at connect().
_SEND_CODE_RPC_KEYS = {
    "ApiIdInvalidError": "err.bad_api_pair",
    "PhoneNumberInvalidError": "err.tg_phone_invalid",
    "PhoneNumberFloodError": "err.tg_phone_flood",
}

# A saved authorization key can be invalidated by Telegram, including after a
# duplicate-key event caused by moving between runtimes.  These errors prove
# only that the local copy cannot authorize; they do not justify deleting the
# Drive recovery point before a later successful sign-in replaces it.
_REAUTH_SESSION_ERRORS = {
    "AuthKeyDuplicatedError",
    "AuthKeyUnregisteredError",
    "SessionRevokedError",
    "SessionExpiredError",
}


def _exc_name(exc: BaseException) -> str:
    return type(exc).__name__


@dataclass
class TelegramStatus:
    state: str = DISCONNECTED
    account_label: str = ""
    authorized: bool = False
    can_resend_in: int = 0
    message_key: str = "status.disconnected"
    extra: dict = field(default_factory=dict)


class TelegramAuth:
    """Owns the ONE Telethon client. No other object may construct one."""

    def __init__(self, ctx, client_factory: Optional[Callable[..., Any]] = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.ctx = ctx
        self._clock = clock
        self._client_factory = client_factory or self._default_factory
        self._lock = threading.RLock()
        self.state: str = DISCONNECTED
        self.client: Any = None
        # protected memory only — never written anywhere
        self._api_id: Optional[int] = None
        self._api_hash: Optional[str] = None
        self._phone: Optional[str] = None
        self._phone_code_hash: Optional[str] = None
        self._last_code_sent_at: Optional[float] = None
        self.account_label: str = ""
        self.last_error_key: str = ""

    # ---- helpers ----

    @staticmethod
    def _default_factory(api_id: int, api_hash: str):
        from .telegram_client import TelegramService

        return TelegramService(api_id, api_hash, session_path=str(TELEGRAM_SESSION))

    def _set_state(self, state: str, reason: str = "") -> None:
        if state not in STATES:
            raise AuthStateError(f"illegal telegram state {state!r}")
        previous, self.state = self.state, state
        self.ctx.ui_state.telegram_status = state
        _log.info("telegram state %s -> %s %s", previous, state, reason)
        db.add_event("", "auth.telegram", f"{previous}->{state}",
                     {"from": previous, "to": state, "reason": reason})

    def _require(self, *allowed: str) -> None:
        if self.state not in allowed:
            raise AuthStateError(f"action not allowed from state {self.state}")

    def _run(self, coro):
        return self.ctx.aio.run(coro)

    def _reset_invalid_saved_session(self, reason: str) -> None:
        """Release a rejected saved client and make the manual-login path fresh."""
        client = self.client
        if client is not None:
            closer = getattr(client, "disconnect", None)
            if callable(closer):
                try:
                    outcome = closer()
                    if hasattr(outcome, "__await__"):
                        self._run(outcome)
                except Exception as exc:  # noqa: BLE001 - recovery must continue
                    _log.warning("telegram invalid-session disconnect skipped: %s", type(exc).__name__)
        self.ctx.auth.clear_telegram()
        self.client = None
        self._phone = None
        self._phone_code_hash = None
        self._last_code_sent_at = None
        self.account_label = ""
        self.last_error_key = "msg.session_restore_needs_login"
        try:
            Path(TELEGRAM_SESSION).unlink(missing_ok=True)
        except OSError as exc:
            _log.warning("telegram invalid-session file cleanup skipped: %s", type(exc).__name__)
        self._set_state(READY_FOR_PHONE, reason)

    # ---- actions ----

    def set_credentials(self, api_id: str | int, api_hash: str) -> TelegramStatus:
        with self._lock:
            try:
                parsed_id = int(str(api_id).strip())
            except Exception:
                raise TeleDriveError("api id must be numeric", "err.bad_api_id")
            if not str(api_hash).strip():
                raise TeleDriveError("api hash required", "err.bad_api_hash")
            self._api_id = parsed_id
            self._api_hash = str(api_hash).strip()
            self.client = self._client_factory(self._api_id, self._api_hash)
            try:
                self._run(self.client.connect())
                authorized = self._run(self.client.is_authorized())
            except BaseException as exc:  # noqa: BLE001 - narrow reauth recovery below
                name = _exc_name(exc)
                if name in _REAUTH_SESSION_ERRORS:
                    self._reset_invalid_saved_session(f"saved session rejected: {name}")
                    return self.status()
                raise
            if authorized:
                self.account_label = self._describe_account()
                self.ctx.auth.set_telegram(self.client, self.account_label)
                self._set_state(AUTHORIZED, "existing session")
                self._persist_session()
            else:
                self._set_state(READY_FOR_PHONE, "credentials accepted")
            return self.status()

    def send_code(self, phone: str) -> TelegramStatus:
        with self._lock:
            self._require(READY_FOR_PHONE, ERROR, CODE_REQUESTED)
            phone = (phone or "").strip().replace(" ", "")
            if not phone.startswith("+") or not phone[1:].isdigit():
                raise TeleDriveError("phone must be international", "err.bad_phone")
            if self.state == CODE_REQUESTED and self._phone == phone:
                # duplicate click: idempotent, no second send_code_request
                return self.status()
            self._phone = phone
            self._set_state(SENDING_CODE)
            return self._do_send_code()

    def resend_code(self) -> TelegramStatus:
        with self._lock:
            self._require(CODE_REQUESTED, READY_FOR_PHONE)
            if not self._phone:
                raise AuthStateError("no phone recorded")
            remaining = self.cooldown_remaining()
            if remaining > 0:
                raise CooldownError(f"resend available in {remaining}s")
            self._set_state(SENDING_CODE, "resend")
            return self._do_send_code()

    def _do_send_code(self) -> TelegramStatus:
        try:
            sent_hash = self._run(self.client.start_login(self._phone))
        except BaseException as exc:  # noqa: BLE001 — classified below
            return self._handle_send_error(exc)
        self._phone_code_hash = sent_hash
        self._last_code_sent_at = self._clock()
        self._set_state(CODE_REQUESTED)
        return self.status()

    def _handle_send_error(self, exc: BaseException) -> TelegramStatus:
        name = _exc_name(exc)
        if name == "FloodWaitError":
            seconds = int(getattr(exc, "seconds", RESEND_COOLDOWN_SECONDS) or 0)
            self._last_code_sent_at = self._clock() - max(0, RESEND_COOLDOWN_SECONDS - seconds)
            self.last_error_key = "err.floodwait"
            self._set_state(CODE_REQUESTED if self._phone_code_hash else READY_FOR_PHONE,
                            "flood wait")
            raise CooldownError(f"flood wait {seconds}s", "err.floodwait")
        # M18-T03 — name the real cause instead of the dead-end err.unknown.
        if isinstance(exc, _TRANSPORT_EXC):
            # network/DC failure before Telegram even saw the request — retryable
            self.last_error_key = "err.tg_connect_failed"
            self._set_state(READY_FOR_PHONE, f"send_code transport: {name}")
            raise TeleDriveError(f"telegram connect failed: {name}",
                                 "err.tg_connect_failed")
        rpc_key = _SEND_CODE_RPC_KEYS.get(name)
        if rpc_key is not None:
            self.last_error_key = rpc_key
            if rpc_key == "err.bad_api_pair":
                # credentials themselves rejected — user fixes them via Connect
                self._set_state(ERROR, f"send_code rpc: {name}")
            else:
                # number rejected/rate-limited — user may retry a corrected phone
                self._set_state(READY_FOR_PHONE, f"send_code rpc: {name}")
            raise TeleDriveError(safe_exception(exc), rpc_key)
        self.last_error_key = "err.unknown"
        self._set_state(ERROR, safe_exception(exc))
        raise TeleDriveError(safe_exception(exc))

    def verify_code(self, code: str) -> TelegramStatus:
        with self._lock:
            self._require(CODE_REQUESTED, VERIFYING_CODE)
            if not self._phone_code_hash:
                raise AuthStateError("no phone_code_hash — request a code first")
            code = (code or "").strip()
            if not code:
                raise TeleDriveError("code required", "err.bad_code")
            self._set_state(VERIFYING_CODE)
            try:
                self._run(
                    self.client.sign_in_code(
                        phone=self._phone,
                        code=code,
                        phone_code_hash=self._phone_code_hash,  # exact reuse
                    )
                )
            except BaseException as exc:  # noqa: BLE001
                return self._handle_code_error(exc)
            return self._finish_authorized()

    def _handle_code_error(self, exc: BaseException) -> TelegramStatus:
        name = _exc_name(exc)
        if name == "SessionPasswordNeededError":
            self._set_state(PASSWORD_REQUIRED, "2FA")
            return self.status()
        if name == "PhoneCodeInvalidError":
            # keep the hash and the state — the user retypes the code
            self.last_error_key = "err.code_invalid"
            self._set_state(CODE_REQUESTED, "invalid code")
            raise TeleDriveError("invalid code", "err.code_invalid")
        if name == "PhoneCodeExpiredError":
            self._phone_code_hash = None
            self.last_error_key = "err.code_expired"
            self._set_state(READY_FOR_PHONE, "expired code")
            raise TeleDriveError("expired code", "err.code_expired")
        # M18-T03 — a transport drop mid-verification is NOT a wrong code:
        # the hash is still valid, keep CODE_REQUESTED so the same code retries.
        if isinstance(exc, _TRANSPORT_EXC):
            self.last_error_key = "err.tg_connect_failed"
            self._set_state(CODE_REQUESTED, f"verify_code transport: {name}")
            raise TeleDriveError(f"telegram connect failed: {name}",
                                 "err.tg_connect_failed")
        self.last_error_key = "err.unknown"
        self._set_state(ERROR, safe_exception(exc))
        raise TeleDriveError(safe_exception(exc))

    def verify_password(self, password: str) -> TelegramStatus:
        with self._lock:
            self._require(PASSWORD_REQUIRED, VERIFYING_PASSWORD)
            if not password:
                raise TeleDriveError("password required", "err.bad_password")
            self._set_state(VERIFYING_PASSWORD)
            try:
                # same client, no new code requested
                self._run(self.client.sign_in_password(password))
            except BaseException as exc:  # noqa: BLE001
                name = _exc_name(exc)
                # M18-T03 — never mislabel a dropped connection as a wrong password.
                if isinstance(exc, _TRANSPORT_EXC):
                    self.last_error_key = "err.tg_connect_failed"
                    self._set_state(PASSWORD_REQUIRED,
                                    f"verify_password transport: {name}")
                    raise TeleDriveError(f"telegram connect failed: {name}",
                                         "err.tg_connect_failed")
                if name == "FloodWaitError":
                    seconds = int(getattr(exc, "seconds", RESEND_COOLDOWN_SECONDS) or 0)
                    self.last_error_key = "err.floodwait"
                    self._set_state(PASSWORD_REQUIRED,
                                    f"verify_password flood {seconds}s")
                    raise CooldownError(f"flood wait {seconds}s", "err.floodwait")
                self.last_error_key = "err.password_invalid"
                self._set_state(PASSWORD_REQUIRED, safe_exception(exc))
                raise TeleDriveError("password rejected", "err.password_invalid")
            finally:
                password = "\0" * len(password)  # zero the local reference
                del password
            return self._finish_authorized()

    def _finish_authorized(self) -> TelegramStatus:
        authorized = bool(self._run(self.client.is_authorized()))
        if not authorized:
            self._set_state(REAUTH_REQUIRED, "sign_in did not authorize")
            raise TeleDriveError("not authorized", "err.reauth")
        self._phone_code_hash = None
        self.account_label = self._describe_account()
        self.ctx.auth.set_telegram(self.client, self.account_label)
        self._set_state(AUTHORIZED, "sign_in ok")
        db.add_event("", "auth.telegram", "authorized", {"account": self.account_label})
        self._persist_session()
        return self.status()

    def _describe_account(self) -> str:
        if self._phone:
            return mask_phone(self._phone)
        return "saved-session"

    def _persist_session(self) -> None:
        """Best-effort Drive vault write. Never raises into the auth flow."""
        try:
            from . import session_vault

            session_vault.persist_from_context(self.ctx, secret=self._api_hash or "")
        except Exception as exc:  # noqa: BLE001
            _log.warning("session vault persist skipped: %s", type(exc).__name__)

    def _wipe_session(self) -> None:
        try:
            from . import session_vault

            session_vault.wipe_from_context(self.ctx)
        except Exception as exc:  # noqa: BLE001
            _log.warning("session vault wipe skipped: %s", type(exc).__name__)

    def logout(self) -> TelegramStatus:
        with self._lock:
            if self.client is not None:
                try:
                    self._run(self.client.logout())
                except BaseException as exc:  # noqa: BLE001
                    _log.warning("logout error: %s", safe_exception(exc))
            self.ctx.auth.clear_telegram()
            self.client = None
            self._phone = None
            self._phone_code_hash = None
            self._last_code_sent_at = None
            self.account_label = ""
            self._wipe_session()
            self._set_state(DISCONNECTED, "logout")
            return self.status()

    def switch_account(self) -> TelegramStatus:
        """Explicit account change always requires full reauthorization."""
        self.logout()
        self._api_id = None
        self._api_hash = None
        self._set_state(REAUTH_REQUIRED, "account switch")
        return self.status()

    # ---- read-only ----

    def cooldown_remaining(self) -> int:
        if self._last_code_sent_at is None:
            return 0
        elapsed = self._clock() - self._last_code_sent_at
        return max(0, int(RESEND_COOLDOWN_SECONDS - elapsed + 0.999))

    @property
    def authorized(self) -> bool:
        return self.state == AUTHORIZED

    def status(self) -> TelegramStatus:
        return TelegramStatus(
            state=self.state,
            account_label=self.account_label,
            authorized=self.authorized,
            can_resend_in=self.cooldown_remaining(),
            message_key="status.connected" if self.authorized else "status.disconnected",
        )
