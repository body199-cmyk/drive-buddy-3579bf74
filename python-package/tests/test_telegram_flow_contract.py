"""M15-T03 — contract for the Colab Telegram login flow.

No credentials, no network, no live Telegram. These tests prove the contract
the Colab UI depends on:

  * set_credentials creates exactly ONE client;
  * phone_code_hash lives in memory and never reaches the events table;
  * the OTP panel is visible ONLY in CODE_REQUESTED;
  * the 2FA panel is visible ONLY after a real SessionPasswordNeededError;
  * Connected is never rendered before AUTHORIZED;
  * a failed action re-derives panel visibility from the live state.
"""
from __future__ import annotations

import json

import pytest

from teledrive import database as db
from teledrive import telegram_auth as ta
from teledrive.errors import TeleDriveError
from teledrive.handlers import Handlers
from teledrive.i18n import t

# The ONE fake client already used by tests/test_telegram_auth.py — no second
# fake, no duplicated Telegram double.
from .test_telegram_auth import (
    FakeClient,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

PHONE = "+971500000000"
CODE = "55555"
FIRST_HASH = "hash-1"


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


@pytest.fixture()
def handlers(ctx, auth):
    return Handlers(ctx)


def _visible(payload) -> bool:
    """Read the visibility flag out of a gradio-or-plain update payload."""
    return bool(payload["visible"])


def _panels(result):
    detail, label, code_panel, password_panel = result
    return detail, label, _visible(code_panel), _visible(password_panel)


# ---- client identity ----


def test_set_credentials_creates_exactly_one_client(auth):
    auth.set_credentials("12345", "abc")
    assert len(auth.created) == 1
    assert auth.client is auth.created[0]
    assert auth.state == ta.READY_FOR_PHONE


def test_non_numeric_api_id_is_refused_before_any_client_exists(auth):
    with pytest.raises(TeleDriveError) as excinfo:
        auth.set_credentials("not-a-number", "abc")
    assert excinfo.value.message_key == "err.bad_api_id"
    assert auth.created == [] and auth.client is None


def test_empty_api_hash_is_refused(auth):
    with pytest.raises(TeleDriveError) as excinfo:
        auth.set_credentials("12345", "   ")
    assert excinfo.value.message_key == "err.bad_api_hash"
    assert auth.created == []


def test_non_international_phone_is_refused(auth):
    auth.set_credentials("12345", "abc")
    with pytest.raises(TeleDriveError) as excinfo:
        auth.send_code("0500000000")
    assert excinfo.value.message_key == "err.bad_phone"
    assert auth.client.sent == []


# ---- secrets stay in memory ----


def test_phone_code_hash_stays_in_memory_and_out_of_the_event_log(auth):
    auth.set_credentials("12345", "abc")
    auth.send_code(PHONE)
    assert auth._phone_code_hash == FIRST_HASH  # noqa: SLF001 - memory only
    dumped = json.dumps(db.recent_events(limit=500), ensure_ascii=False, default=str)
    assert FIRST_HASH not in dumped
    assert PHONE not in dumped
    assert "abc" not in dumped


def test_two_factor_password_is_never_recorded(auth):
    auth.set_credentials("12345", "abc")
    auth.send_code(PHONE)
    auth.client.code_error = SessionPasswordNeededError()
    auth.verify_code(CODE)
    auth.verify_password("top-secret-2fa")
    dumped = json.dumps(db.recent_events(limit=500), ensure_ascii=False, default=str)
    assert "top-secret-2fa" not in dumped


# ---- OTP panel is conditional ----


def test_otp_panel_is_hidden_before_a_code_is_requested(handlers):
    _, _, code_visible, password_visible = _panels(
        handlers.h_telegram_set_credentials("12345", "abc")
    )
    assert code_visible is False
    assert password_visible is False


def test_otp_panel_appears_only_in_code_requested(handlers, auth):
    handlers.h_telegram_set_credentials("12345", "abc")
    detail, _, code_visible, password_visible = _panels(
        handlers.h_telegram_send_code(PHONE)
    )
    assert auth.state == ta.CODE_REQUESTED
    assert code_visible is True
    assert password_visible is False
    assert t("status.disconnected") in detail  # not Connected yet


def test_otp_panel_closes_after_authorization(handlers, auth):
    handlers.h_telegram_set_credentials("12345", "abc")
    handlers.h_telegram_send_code(PHONE)
    detail, label, code_visible, password_visible = _panels(
        handlers.h_telegram_verify_code(CODE)
    )
    assert auth.state == ta.AUTHORIZED
    assert code_visible is False and password_visible is False
    assert label == t("status.connected")


def test_invalid_code_keeps_the_otp_panel_open_and_the_2fa_panel_shut(handlers, auth):
    handlers.h_telegram_set_credentials("12345", "abc")
    handlers.h_telegram_send_code(PHONE)
    auth.client.code_error = PhoneCodeInvalidError()
    message, _, code_visible, password_visible = _panels(
        handlers.h_telegram_verify_code("00000")
    )
    # the handler swallows the error into a safe message, keeps the hash,
    # keeps the OTP panel open and never opens the 2FA panel
    assert auth.state == ta.CODE_REQUESTED
    assert code_visible is True
    assert password_visible is False
    assert t("err.code_invalid") in message
    assert len(auth.client.sent) == 1


# ---- 2FA panel is conditional on a REAL Telegram answer ----


def test_2fa_panel_appears_only_on_session_password_needed(handlers, auth):
    handlers.h_telegram_set_credentials("12345", "abc")
    handlers.h_telegram_send_code(PHONE)
    auth.client.code_error = SessionPasswordNeededError()
    _, label, code_visible, password_visible = _panels(
        handlers.h_telegram_verify_code(CODE)
    )
    assert auth.state == ta.PASSWORD_REQUIRED
    assert password_visible is True
    assert code_visible is False
    assert label == t("status.disconnected")  # Connected NOT claimed yet


def test_account_without_2fa_never_sees_the_password_panel(handlers, auth):
    handlers.h_telegram_set_credentials("12345", "abc")
    handlers.h_telegram_send_code(PHONE)
    results = [
        _panels(handlers.h_telegram_verify_code(CODE)),
        _panels(handlers.h_telegram_status()),
    ]
    assert auth.state == ta.AUTHORIZED
    assert all(password_visible is False for _, _, _, password_visible in results)


def test_2fa_panel_closes_after_the_password_is_accepted(handlers, auth):
    handlers.h_telegram_set_credentials("12345", "abc")
    handlers.h_telegram_send_code(PHONE)
    auth.client.code_error = SessionPasswordNeededError()
    handlers.h_telegram_verify_code(CODE)
    client_before = auth.client
    _, label, code_visible, password_visible = _panels(
        handlers.h_telegram_verify_password("top-secret-2fa")
    )
    assert auth.client is client_before          # same client, no second one
    assert len(auth.client.sent) == 1            # no new code requested
    assert auth.state == ta.AUTHORIZED
    assert code_visible is False and password_visible is False
    assert label == t("status.connected")


def test_rejected_password_keeps_the_2fa_panel_open(handlers, auth):
    handlers.h_telegram_set_credentials("12345", "abc")
    handlers.h_telegram_send_code(PHONE)
    auth.client.code_error = SessionPasswordNeededError()
    handlers.h_telegram_verify_code(CODE)

    async def reject(password):
        raise RuntimeError("bad password")

    auth.client.sign_in_password = reject
    message, _, code_visible, password_visible = _panels(
        handlers.h_telegram_verify_password("wrong")
    )
    assert auth.state == ta.PASSWORD_REQUIRED
    assert password_visible is True and code_visible is False
    assert t("err.password_invalid") in message


# ---- logout closes both panels ----


def test_logout_closes_both_panels_and_clears_secret_state(handlers, auth):
    handlers.h_telegram_set_credentials("12345", "abc")
    handlers.h_telegram_send_code(PHONE)
    handlers.h_telegram_verify_code(CODE)
    _, label, code_visible, password_visible = _panels(handlers.h_telegram_logout())
    assert auth.state == ta.DISCONNECTED
    assert code_visible is False and password_visible is False
    assert label == t("status.disconnected")
    assert auth.client is None
    assert auth._phone is None and auth._phone_code_hash is None  # noqa: SLF001
