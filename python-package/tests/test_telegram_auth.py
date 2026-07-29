"""Telegram login: phone_code_hash reuse, 2FA on the same client, cooldowns."""
from __future__ import annotations

import pytest

from teledrive import telegram_auth as ta
from teledrive.errors import AuthStateError, CooldownError, TeleDriveError


class SessionPasswordNeededError(Exception):
    pass


class PhoneCodeInvalidError(Exception):
    pass


class PhoneCodeExpiredError(Exception):
    pass


class FloodWaitError(Exception):
    def __init__(self, seconds=30):
        super().__init__("flood")
        self.seconds = seconds


class FakeClient:
    def __init__(self, api_id, api_hash):
        self.api_id = api_id
        self.api_hash = api_hash
        self.sent = []
        self.sign_in_calls = []
        self.password_calls = []
        self.authorized = False
        self.code_error = None
        self.send_error = None
        self.instances = 1

    async def connect(self):
        return None

    async def is_authorized(self):
        return self.authorized

    async def start_login(self, phone):
        if self.send_error:
            error, self.send_error = self.send_error, None
            raise error
        self.sent.append(phone)
        return f"hash-{len(self.sent)}"

    async def sign_in_code(self, phone, code, phone_code_hash):
        self.sign_in_calls.append((phone, code, phone_code_hash))
        if self.code_error:
            error, self.code_error = self.code_error, None
            raise error
        self.authorized = True

    async def sign_in_password(self, password):
        self.password_calls.append(password)
        self.authorized = True

    async def logout(self):
        self.authorized = False


@pytest.fixture()
def auth(ctx):
    created = []

    def factory(api_id, api_hash):
        client = FakeClient(api_id, api_hash)
        created.append(client)
        return client

    service = ta.TelegramAuth(ctx, client_factory=factory)
    service.created = created
    ctx.telegram_auth = service
    return service


def test_happy_path_reuses_the_exact_phone_code_hash(auth):
    auth.set_credentials("12345", "abc")
    assert auth.state == ta.READY_FOR_PHONE
    auth.send_code("+971500000000")
    assert auth.state == ta.CODE_REQUESTED
    status = auth.verify_code("55555")
    client = auth.client
    assert client.sign_in_calls == [("+971500000000", "55555", "hash-1")]
    assert len(client.sent) == 1  # code requested exactly once
    assert status.authorized and auth.state == ta.AUTHORIZED


def test_wrong_code_keeps_the_hash_and_does_not_resend(auth):
    auth.set_credentials("1", "h")
    auth.send_code("+971500000000")
    auth.client.code_error = PhoneCodeInvalidError()
    with pytest.raises(TeleDriveError) as excinfo:
        auth.verify_code("00000")
    assert excinfo.value.message_key == "err.code_invalid"
    assert auth.state == ta.CODE_REQUESTED
    auth.verify_code("55555")
    assert auth.client.sign_in_calls[-1][2] == "hash-1"
    assert len(auth.client.sent) == 1


def test_expired_code_requires_a_new_request(auth):
    auth.set_credentials("1", "h")
    auth.send_code("+971500000000")
    auth.client.code_error = PhoneCodeExpiredError()
    with pytest.raises(TeleDriveError) as excinfo:
        auth.verify_code("55555")
    assert excinfo.value.message_key == "err.code_expired"
    assert auth.state == ta.READY_FOR_PHONE


def test_two_factor_uses_the_same_client_without_a_new_code(auth):
    auth.set_credentials("1", "h")
    auth.send_code("+971500000000")
    auth.client.code_error = SessionPasswordNeededError()
    status = auth.verify_code("55555")
    assert auth.state == ta.PASSWORD_REQUIRED and not status.authorized
    client_before = auth.client
    auth.verify_password("secret")
    assert auth.client is client_before
    assert len(auth.client.sent) == 1
    assert auth.state == ta.AUTHORIZED


def test_duplicate_send_code_click_is_idempotent(auth):
    auth.set_credentials("1", "h")
    auth.send_code("+971500000000")
    auth.send_code("+971500000000")
    assert len(auth.client.sent) == 1


def test_resend_is_rate_limited(auth):
    clock = {"now": 1000.0}
    auth._clock = lambda: clock["now"]  # noqa: SLF001 - test clock injection
    auth.set_credentials("1", "h")
    auth.send_code("+971500000000")
    with pytest.raises(CooldownError):
        auth.resend_code()
    clock["now"] += ta.RESEND_COOLDOWN_SECONDS + 1
    auth.resend_code()
    assert len(auth.client.sent) == 2
    assert auth.client.sign_in_calls == []


def test_flood_wait_is_surfaced_as_cooldown(auth):
    auth.set_credentials("1", "h")
    auth.client.send_error = FloodWaitError(45)
    with pytest.raises(CooldownError) as excinfo:
        auth.send_code("+971500000000")
    assert excinfo.value.message_key == "err.floodwait"


def test_verify_without_a_code_request_is_refused(auth):
    auth.set_credentials("1", "h")
    with pytest.raises(AuthStateError):
        auth.verify_code("55555")


def test_logout_clears_all_secret_state(auth):
    auth.set_credentials("1", "h")
    auth.send_code("+971500000000")
    auth.verify_code("55555")
    auth.logout()
    assert auth.state == ta.DISCONNECTED
    assert auth._phone is None and auth._phone_code_hash is None  # noqa: SLF001
    assert auth.client is None


def test_status_never_exposes_the_full_phone(auth):
    auth.set_credentials("1", "h")
    auth.send_code("+971501234567")
    auth.verify_code("55555")
    assert "1234567" not in auth.status().account_label
