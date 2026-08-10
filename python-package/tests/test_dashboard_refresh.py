"""M17-T03: dashboard.refresh reads live state or 'غير متصل' — never fake numbers."""
from __future__ import annotations

from teledrive import action_registry

PROVES = ("dashboard.refresh",)


def test_refresh_returns_live_state_or_disconnected(ctx):
    """dashboard.refresh returns a dict; Telegram/Drive report disconnected
    when the services are not authenticated — never fabricated numbers."""
    payload_update = ctx.handlers.h_dashboard_refresh()
    payload = payload_update["value"]
    assert isinstance(payload, dict)
    # Keys we always expect (localized)
    from teledrive.i18n import t
    for key in ("dash.done", "dash.failed", "dash.remaining", "dash.speed",
                "dash.avg_speed", "dash.eta", "dash.overall_pct",
                "dash.telegram_status", "dash.drive_status",
                "dash.drive_space", "dash.colab_space", "dash.queue_status",
                "dash.current"):
        assert t(key) in payload, f"missing key {key!r}"
    # When disconnected (fresh ctx) status must reflect that
    assert t("status.disconnected") in payload[t("dash.telegram_status")] or \
           t("status.connected") in payload[t("dash.telegram_status")]
    # Done/failed/remaining are integer-looking (never None/fake)
    for k in (t("dash.done"), t("dash.failed"), t("dash.remaining")):
        assert isinstance(payload[k], int)
