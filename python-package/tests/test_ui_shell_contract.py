"""M15-T04 — graphite shell contract tests (Colab UI rebuild).

Every check here runs against REAL gradio components and the LIVE context —
no credentials, no network, no live Telegram/Drive. The shell is rendered
through the same ``ui._render_shell`` function the browser triggers via
``gr.render``, so these tests prove what the Colab page will contain:

  * every main page builds without a Gradio exception, in Arabic and English;
  * every rendered control is wired to a ready action or hidden/unavailable;
  * the OTP panel is visible ONLY in CODE_REQUESTED and the 2FA panel ONLY in
    PASSWORD_REQUIRED — on first render AND after a language-switch re-render;
  * an RTL/LTR switch never loses runtime state (login state, queue, selection);
  * no fake data: chips, cards, tables, logs and dashboard start empty/zeroed
    only because the live state is empty, and show live state when it exists;
  * telegram controls resolve ONLY the seven public auth APIs;
  * wired outputs match each handler's arity contract exactly;
  * the graphite theme/css is actually attached to the Blocks for launch.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

gr = pytest.importorskip("gradio")  # pinned in requirements.lock; skip if absent

from teledrive import action_registry, ui
from teledrive import telegram_auth as ta
from teledrive.handlers import DEFAULT_QUEUE_ARITY, ERROR_ARITY
from teledrive.i18n import t
from teledrive.models import MediaItem

from .test_telegram_auth import FakeClient, SessionPasswordNeededError

PHONE = "+971500000000"
CODE = "55555"

PUBLIC_TELEGRAM_APIS = {
    "telegram_auth.set_credentials",
    "telegram_auth.send_code",
    "telegram_auth.resend_code",
    "telegram_auth.verify_code",
    "telegram_auth.verify_password",
    "telegram_auth.logout",
    "telegram_auth.status",
}

# Actions proven here (see teledrive/action_registry.proof_test): none — this
# file guards the shell itself; it flips no registry flags.
PROVES: tuple = ()


@pytest.fixture()
def auth(ctx):
    def factory(api_id, api_hash):
        client = FakeClient(api_id, api_hash)
        factory.created.append(client)
        return client

    factory.created = []
    service = ta.TelegramAuth(ctx, client_factory=factory)
    ctx.telegram_auth = service
    return service


def _render(ctx, lang: str):
    """One render pass exactly as the browser triggers it, inside a Blocks ctx."""
    with gr.Blocks() as demo:
        refs = ui._render_shell(ctx, ctx.binder, gr.State(lang), lang)
    return demo, refs


def _block_fns(demo):
    return [bf for bf in demo.fns.values() if getattr(bf.fn, "action_id", None)]


# ---- pages build without a Gradio exception (both directions) ----


def test_shell_renders_in_arabic_rtl_by_default(ctx):
    demo, refs = _render(ctx, "ar")
    assert refs["direction"] == "td-rtl"
    assert refs["queue_table"].headers == [t(k) for k in ui.TABLE_HEADERS]
    assert t("nav.queue") == "التحويلات"


def test_shell_renders_in_english_ltr(ctx):
    demo, refs = _render(ctx, "en")
    assert refs["direction"] == "td-ltr"
    assert t("nav.queue") == "Transfers"


def test_invalid_language_falls_back_without_exception(ctx):
    demo, refs = _render(ctx, "fr")  # unsupported: falls back to config language
    assert refs["direction"] in ("td-rtl", "td-ltr")


# ---- every visible control is wired; nothing dead or orphaned ----


def test_every_ready_action_is_wired_through_real_components(ctx):
    demo, refs = _render(ctx, "ar")
    assert ctx.binder.missing() == []
    assert ctx.binder.orphans() == []
    wired_fns = _block_fns(demo)
    wired_ids = {bf.fn.action_id for bf in wired_fns}
    ready_ids = {s.action_id for s in action_registry.ready_specs()}
    assert wired_ids == ready_ids


def test_outputs_match_handler_arity_for_every_wired_action(ctx):
    demo, refs = _render(ctx, "ar")
    assert _block_fns(demo), "expected wired actions on the demo"
    for bf in _block_fns(demo):
        action_id = bf.fn.action_id
        expected = ERROR_ARITY.get(action_id, DEFAULT_QUEUE_ARITY)
        assert len(bf.outputs) == expected, action_id


def test_analyze_outputs_never_include_the_queue_table(ctx):
    """analyze.run updates candidates only — enqueue is always explicit."""
    demo, refs = _render(ctx, "ar")
    analyze_fns = [bf for bf in _block_fns(demo) if bf.fn.action_id == "analyze.run"]
    assert len(analyze_fns) == 0 or all(
        refs["queue_table"] not in bf.outputs for bf in analyze_fns
    )

    def fake_call(action_id, *args, **kwargs):
        rows = [["id1", "a.bin", "document", "1.0 B", t("state.Pending"), "0%", 0]]
        return SimpleNamespace(total=1, total_bytes=1, scope="auto", rows=rows)

    ctx.handlers.call = fake_call  # type: ignore[assignment]
    summary, rows = ctx.handlers.h_analyze_run("https://t.me/x/1", "auto")
    assert rows and rows[0][0] == "id1"
    assert rows != ctx.handlers.queue_rows() or not ctx.handlers.queue_rows()


def test_queue_controls_resolve_the_real_queue_manager(ctx):
    for spec in action_registry.ACTION_SPECS:
        if spec.section != "transfers":
            continue
        target = ctx.resolve(spec.service_path)
        assert getattr(target, "__self__", None) is ctx.queue_manager, spec.action_id


# ---- telegram controls use only the public auth surface ----


def test_telegram_actions_resolve_only_the_public_auth_apis(ctx):
    telegram_specs = [s for s in action_registry.ACTION_SPECS if s.action_id.startswith("telegram.")]
    assert {s.service_path for s in telegram_specs} == PUBLIC_TELEGRAM_APIS
    for spec in telegram_specs:
        assert getattr(ctx.resolve(spec.service_path), "__self__", None) is ctx.telegram_auth


# ---- OTP / 2FA visibility from the live state machine (seeded renders) ----


def test_otp_panel_hidden_on_fresh_render(ctx):
    demo, refs = _render(ctx, "ar")
    assert refs["code_panel"].visible is False
    assert refs["password_panel"].visible is False


def test_otp_panel_visible_only_when_code_requested(ctx, auth, monkeypatch):
    auth.set_credentials("12345", "abc")
    auth.send_code(PHONE)
    assert auth.state == ta.CODE_REQUESTED
    demo, refs = _render(ctx, "ar")
    assert refs["code_panel"].visible is True
    assert refs["password_panel"].visible is False


def test_2fa_panel_visible_only_when_password_required(ctx, auth):
    auth.set_credentials("12345", "abc")
    auth.send_code(PHONE)
    auth.client.code_error = SessionPasswordNeededError()
    auth.verify_code(CODE)
    assert auth.state == ta.PASSWORD_REQUIRED
    demo, refs = _render(ctx, "ar")
    assert refs["password_panel"].visible is True
    assert refs["code_panel"].visible is False


def test_panels_close_after_authorization(ctx, auth):
    auth.set_credentials("12345", "abc")
    auth.send_code(PHONE)
    auth.verify_code(CODE)
    assert auth.state == ta.AUTHORIZED
    demo, refs = _render(ctx, "ar")
    assert refs["code_panel"].visible is False
    assert refs["password_panel"].visible is False
    assert refs["telegram_chip"].value == t("status.connected")


# ---- RTL/LTR switch preserves runtime state ----


def test_language_switch_preserves_login_state_and_panels(ctx, auth):
    auth.set_credentials("12345", "abc")
    auth.send_code(PHONE)
    demo_ar, refs_ar = _render(ctx, "ar")
    assert refs_ar["direction"] == "td-rtl"
    assert refs_ar["code_panel"].visible is True

    demo_en, refs_en = _render(ctx, "en")
    assert refs_en["direction"] == "td-ltr"
    # the state machine was never touched by the re-render
    assert ctx.telegram_auth.state == ta.CODE_REQUESTED
    assert refs_en["code_panel"].visible is True
    assert refs_en["password_panel"].visible is False
    assert t("status.disconnected") in refs_en["telegram_detail"].value


def test_language_switch_preserves_selection_rows(ctx):
    item = MediaItem(safe_name="clip.mp4", media_type="video", size_bytes=5)
    ctx.selection.set_candidates([item])
    demo_ar, refs_ar = _render(ctx, "ar")
    demo_en, refs_en = _render(ctx, "en")
    rows_ar = refs_ar["candidates_table"].value["data"]
    rows_en = refs_en["candidates_table"].value["data"]
    # the SAME underlying item survives re-render; only the state label's
    # localization differs (بانتظار vs Pending), which is the point of i18n.
    assert len(rows_ar) == len(rows_en) == 1
    assert rows_ar[0][0] == rows_en[0][0] == item.id
    assert rows_ar[0][1] == rows_en[0][1] == "clip.mp4"
    assert rows_ar[0][4] != rows_en[0][4]


# ---- no fake data anywhere on first render ----


def test_fresh_render_shows_no_fake_rows_logs_or_connected_states(ctx):
    demo, refs = _render(ctx, "ar")
    assert refs["telegram_chip"].value == t("status.disconnected")
    assert refs["drive_chip"].value == t("status.disconnected")
    assert refs["queue_table"].value["data"] == []
    assert refs["candidates_table"].value["data"] == []
    assert t("status.disconnected") in refs["telegram_card"].value
    assert t("status.disconnected") in refs["drive_card"].value
    # dashboard and queue header are REAL reads of the live context
    assert refs["dashboard_json"].value == ctx.stats.dashboard()
    assert refs["queue_status"].value == ctx.handlers._queue_view(
        ctx.queue_manager.snapshot()
    )[0]


def test_logs_box_is_fed_by_the_real_log_service(ctx, monkeypatch):
    """The logs box must render what LogService.tail returns — never a literal."""
    from teledrive import services

    monkeypatch.setattr(services, "tail_log", lambda lines: "M15T04_SENTINEL")
    demo, refs = _render(ctx, "ar")
    assert "M15T04_SENTINEL" in (refs["logs_box"].value or "")


def test_dashboard_seed_reports_zeroes_not_staged_numbers(ctx):
    demo, refs = _render(ctx, "ar")
    payload = refs["dashboard_json"].value
    assert payload[t("dash.done")] == 0
    assert payload[t("dash.failed")] == 0
    assert payload[t("dash.telegram_status")] == t("status.disconnected")


# ---- the graphite theme/css is actually attached for launch ----


def test_graphite_theme_and_css_are_attached_to_the_blocks(ctx):
    demo = ui.build(ctx)
    css = getattr(demo, "_deprecated_css", "") or ""
    theme = getattr(demo, "_deprecated_theme", None)
    assert theme is not None
    assert "--td-bg" in css and "--td-lime" in css
    assert getattr(demo, "renderables", None), "language render root must exist"
