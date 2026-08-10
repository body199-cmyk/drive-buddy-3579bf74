"""M16-T01 — Analyze scan-mode contract tests.

Created because the M16 MASTER T01 gate names ``tests/test_analyze_ui_modes.py``
and no such file existed in the tree (the AUTHORITY decision instructs the agent
to create the required test file rather than guess).

Proves:
* DEFAULT_SCAN_MODE is ``message`` (never a whole-chat crawl by default);
* ``fields_for_mode`` is the single source of truth for which numeric inputs a
  mode uses (message -> message_id, range -> start_id/end_id, latest/chat ->
  limit), with ``auto`` normalized to ``chat``;
* ``ScannerService.mode_fields`` maps an unsupported mode to a localized
  ``TeleDriveError`` (``err.bad_scan_mode``), never ``err.unknown``;
* the ``analyze.set_mode`` action is implemented+tested, its handler returns
  exactly four visibility updates matching the mode, and the UI wires the mode
  radio through ``binder.wire_if_ready(..., event="change")``;
* no client-side ``minimum=``/``maximum=`` on the optional Analyze numbers
  (regression for ``Value 0 is less than minimum value 1.``) and no raw English
  strings inside the Analyze choices;
* every link/validation refusal path raises a localized ``TeleDriveError`` with
  its own key: err.bad_link, err.link_invite_unsupported, err.scan_*;
* the SCAN_VALIDATION_KEYS map is exhaustive and both locales declare every key.

``analyze.set_mode`` is proven here (see action_registry.proof_test).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from teledrive import action_registry, services, ui
from teledrive.errors import TeleDriveError
from teledrive.i18n import t
from teledrive.media_scanner import (
    DEFAULT_SCAN_MODE,
    MODE_FIELDS,
    SCAN_FIELDS,
    fields_for_mode,
)

PROVES = ("analyze.set_mode",)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
UI_SOURCE = PACKAGE_ROOT / "teledrive" / "ui.py"
EN_LOCALE = PACKAGE_ROOT / "teledrive" / "locale" / "en.json"
AR_LOCALE = PACKAGE_ROOT / "teledrive" / "locale" / "ar.json"

EXPECTED_FIELDS = {
    "message": {"message_id": True, "start_id": False, "end_id": False, "limit": False},
    "range": {"message_id": False, "start_id": True, "end_id": True, "limit": False},
    "latest": {"message_id": False, "start_id": False, "end_id": False, "limit": True},
    "chat": {"message_id": False, "start_id": False, "end_id": False, "limit": True},
}


class _FakeTelegramAuth:
    authorized = True
    client = object()


class _FakeContext:
    """Minimal context: every refusal case below raises BEFORE touching aio/db."""

    def __init__(self) -> None:
        self.telegram_auth = _FakeTelegramAuth()


def _scanner() -> services.ScannerService:
    return services.ScannerService(_FakeContext())


def _ui_text() -> str:
    return UI_SOURCE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Default mode + fields_for_mode (pure)
# ---------------------------------------------------------------------------


def test_default_scan_mode_is_message_not_chat():
    """Constitution 12.7: no whole-chat crawl by default."""
    assert DEFAULT_SCAN_MODE == "message"
    assert DEFAULT_SCAN_MODE in MODE_FIELDS
    assert set(SCAN_FIELDS) == {"message_id", "start_id", "end_id", "limit"}


def test_fields_for_mode_maps_every_mode_exactly():
    for scan_mode, expected in EXPECTED_FIELDS.items():
        assert fields_for_mode(scan_mode) == expected, scan_mode
    # ``auto`` is the documented legacy alias of ``chat``.
    assert fields_for_mode("auto") == fields_for_mode("chat")
    assert fields_for_mode("  MESSAGE ") == EXPECTED_FIELDS["message"]
    # Pure lookup: never raises for canonical modes, always returns 4 keys.
    for result in (fields_for_mode(m) for m in ("message", "range", "latest", "chat")):
        assert set(result) == set(SCAN_FIELDS)


def test_fields_for_mode_rejects_unknown_mode():
    with pytest.raises(ValueError):
        fields_for_mode("everything")
    with pytest.raises(ValueError):
        fields_for_mode("")


# ---------------------------------------------------------------------------
# ScannerService.mode_fields (localized error path)
# ---------------------------------------------------------------------------


def test_mode_fields_service_returns_the_same_mapping():
    scanner = _scanner()
    assert scanner.mode_fields("message") == EXPECTED_FIELDS["message"]
    assert scanner.mode_fields("range") == EXPECTED_FIELDS["range"]
    assert scanner.mode_fields("latest") == EXPECTED_FIELDS["latest"]
    assert scanner.mode_fields("chat") == EXPECTED_FIELDS["chat"]
    assert scanner.mode_fields() == EXPECTED_FIELDS[DEFAULT_SCAN_MODE]


def test_mode_fields_service_raises_localized_error_for_unknown_mode():
    with pytest.raises(TeleDriveError) as excinfo:
        _scanner().mode_fields("everything")
    assert excinfo.value.message_key == "err.bad_scan_mode"


# ---------------------------------------------------------------------------
# analyze.set_mode — proof test (see action_registry.proof_test)
# ---------------------------------------------------------------------------


def test_set_mode_shows_only_the_fields_that_mode_uses(ctx):
    """Proof test for ACTION_SPECS['analyze.set_mode']."""
    spec = action_registry.get("analyze.set_mode")
    assert spec is not None and spec.ready
    assert spec.service_path == "scanner.mode_fields"
    assert spec.handler_name == "h_analyze_set_mode"

    handler = getattr(ctx.handlers, spec.handler_name)
    assert handler.action_id == "analyze.set_mode"

    expected_updates = {
        "message": (True, False, False, False),
        "range": (False, True, True, False),
        "latest": (False, False, False, True),
        "chat": (False, False, False, True),
    }
    for scan_mode, flags in expected_updates.items():
        updates = handler(scan_mode)
        assert len(updates) == 4, scan_mode
        assert tuple(bool(u["visible"]) for u in updates) == flags, scan_mode

    # The handler always returns exactly the four numeric field updates,
    # in SCAN_FIELDS order, so ERROR_ARITY == 4 and the UI wiring never drifts.
    from teledrive.handlers import ERROR_ARITY

    assert ERROR_ARITY["analyze.set_mode"] == 4
    assert DEFAULT_SCAN_MODE == "message"


def test_mode_radio_is_wired_through_the_binder_change_event(ctx):
    text = _ui_text()
    assert re.search(
        r'binder\.wire_if_ready\(\s*mode,\s*"analyze\.set_mode",\s*\[mode\],'
        r'\s*\[message_id,\s*start_id,\s*end_id,\s*limit\],\s*event="change",?\s*\)',
        text,
    )
    # The radio is gated like every non-ready-able control: declared through
    # binder.is_ready so the rendered-control contract sees it.
    assert 'binder.is_ready("analyze.set_mode")' in text

    gr = pytest.importorskip("gradio")
    from teledrive import ui as ui_module

    with gr.Blocks() as demo:
        refs = ui_module._render_shell(ctx, ctx.binder, gr.State("ar"), "ar")
    wired_ids = {
        bf.fn.action_id
        for bf in demo.fns.values()
        if getattr(getattr(bf, "fn", None), "action_id", None)
    }
    assert "analyze.set_mode" in wired_ids
    assert ctx.binder.missing() == []
    assert ctx.binder.orphans() == []


def test_shell_seed_derives_mode_and_fields_from_the_service():
    """The first render must show message_id only, from LIVE service state."""
    from teledrive import app_context
    from teledrive.handlers import shell_seed

    app_context.reset_context()
    ctx = app_context.create_context()
    try:
        seed = shell_seed(ctx)
        assert seed["analyze_mode"] == DEFAULT_SCAN_MODE
        assert seed["analyze_fields"] == EXPECTED_FIELDS[DEFAULT_SCAN_MODE]
        assert seed["analyze_fields"] == ctx.scanner.mode_fields(DEFAULT_SCAN_MODE)
    finally:
        app_context.reset_context()


# ---------------------------------------------------------------------------
# UI source regressions (M16-T01 live-Colab failure cannot return)
# ---------------------------------------------------------------------------


def test_scan_numbers_have_no_client_side_bounds():
    """A frontend minimum= on an empty Number posts 0 and kills the event.
    ScanRequest.validate() is the only bound authority; re-adding a client
    bound here is exactly the M16-T01 regression."""
    text = _ui_text()
    analyze_start = text.find('with gr.Tab(t("nav.link"))')
    assert analyze_start != -1
    analyze_block = text[analyze_start : analyze_start + 8000]
    assert "minimum=" not in analyze_block
    assert "maximum=" not in analyze_block


def test_analyze_choices_are_localized_not_raw_english():
    text = _ui_text()
    analyze_start = text.find('with gr.Tab(t("nav.link"))')
    analyze_block = text[analyze_start : analyze_start + 8000]
    for scan_mode in ("message", "range", "latest", "chat"):
        assert f'(t("scan.mode.{scan_mode}"), "{scan_mode}")' in analyze_block
    for media in ("all", "video", "audio", "document", "photo", "voice", "animation", "sticker"):
        assert f'(t("media.{media}"), "{media}")' in analyze_block
    # No raw English strings standing alone as a choice value.
    assert 'choices=["message"' not in analyze_block
    assert 'choices=["all"' not in analyze_block
    # The result box has its own translated label (no more triple label).
    assert 'label=t("analyze.result")' in analyze_block


def test_limit_defaults_to_the_canonical_server_bound():
    text = _ui_text()
    assert "value=MAX_SCAN_MESSAGES" in text
    from teledrive.media_scanner import MAX_SCAN_MESSAGES

    assert MAX_SCAN_MESSAGES == 1000


# ---------------------------------------------------------------------------
# Localized refusal paths through ScannerService.analyze
# ---------------------------------------------------------------------------


def test_invalid_link_is_localized_not_unknown():
    with pytest.raises(TeleDriveError) as excinfo:
        _scanner().analyze("not a telegram link", mode="message")
    assert excinfo.value.message_key == "err.bad_link"


def test_invite_link_is_refused_with_its_own_key():
    with pytest.raises(TeleDriveError) as excinfo:
        _scanner().analyze("https://t.me/+MxPnyu0DtP0yYTJk", mode="chat")
    assert excinfo.value.message_key == "err.link_invite_unsupported"
    # The invite variant with joinchat/ is refused the same way.
    with pytest.raises(TeleDriveError) as excinfo2:
        _scanner().analyze("https://t.me/joinchat/AbCdEfGhIjKl", mode="message")
    assert excinfo2.value.message_key == "err.link_invite_unsupported"


def test_message_mode_without_id_names_the_real_reason():
    with pytest.raises(TeleDriveError) as excinfo:
        _scanner().analyze("https://t.me/somepublicchannel", mode="message")
    assert excinfo.value.message_key == "err.scan_message_id"


def test_range_mode_without_ids_names_the_real_reason():
    with pytest.raises(TeleDriveError) as excinfo:
        _scanner().analyze("https://t.me/somepublicchannel", mode="range")
    assert excinfo.value.message_key == "err.scan_range_ids"


def test_unsupported_mode_is_mapped():
    with pytest.raises(TeleDriveError) as excinfo:
        _scanner().analyze("https://t.me/somepublicchannel", mode="everything")
    assert excinfo.value.message_key == "err.bad_scan_mode"


def test_unsupported_media_type_is_mapped():
    with pytest.raises(TeleDriveError) as excinfo:
        _scanner().analyze(
            "https://t.me/somepublicchannel",
            mode="chat",
            media_types=["hologram"],
        )
    assert excinfo.value.message_key == "err.scan_media_type"


def test_invalid_and_oversized_ranges_are_mapped():
    with pytest.raises(TeleDriveError) as excinfo:
        _scanner().analyze(
            "https://t.me/somepublicchannel",
            mode="range",
            start_id=10,
            end_id=5,
        )
    assert excinfo.value.message_key == "err.scan_range_invalid"

    with pytest.raises(TeleDriveError) as excinfo2:
        _scanner().analyze(
            "https://t.me/somepublicchannel",
            mode="range",
            start_id=1,
            end_id=2000,
        )
    assert excinfo2.value.message_key == "err.scan_range_too_large"


def test_every_scan_validation_message_has_a_key():
    """The map must stay exhaustive if validate() ever grows a new message."""
    assert set(services.SCAN_VALIDATION_KEYS.values()) == {
        "err.bad_scan_mode",
        "err.scan_media_type",
        "err.scan_message_id",
        "err.scan_range_ids",
        "err.scan_range_invalid",
        "err.scan_range_too_large",
        "err.scan_limit",
    }


def test_locales_declare_every_new_key():
    arabic = json.loads(AR_LOCALE.read_text(encoding="utf-8"))
    english = json.loads(EN_LOCALE.read_text(encoding="utf-8"))
    required = (
        set(services.SCAN_VALIDATION_KEYS.values())
        | set(services.NON_SCANNABLE_LINK_KINDS.values())
        | {"err.bad_link", "err.bad_scan_request", "analyze.result"}
    )
    assert required.issubset(set(arabic))
    assert required.issubset(set(english))
    for key in required:
        assert arabic[key].strip() != "", key
        assert english[key].strip() != "", key
    # Both languages must stay in exact key parity (test_i18n contract).
    assert set(arabic) == set(english)
    # The translated messages are actually reachable through the i18n layer.
    assert t("err.bad_scan_mode") != "err.bad_scan_mode"
    assert t("err.link_invite_unsupported") != "err.link_invite_unsupported"
    assert t("analyze.result") != "analyze.result"
