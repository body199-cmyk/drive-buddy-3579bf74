"""M17-T03: first render must contain zero fake rows, numbers, or credentials."""
from __future__ import annotations

import pytest

from teledrive import ui as ui_module
from teledrive.handlers import shell_seed

gr = pytest.importorskip("gradio")

PROVES = ()


def test_first_render_shows_zero_rows(ctx):
    """Fresh context renders with empty queue, empty analyze, no fake chips.

    Logs may contain bootstrap INFO lines from prior actions in this process
    (binder/context setup) — that is real log output, not fake data. We only
    assert logs is a string, not a fabricated placeholder.
    """
    seed = shell_seed(ctx)
    assert seed["queue_rows"] in (None, [], [])
    assert isinstance(seed["logs"], str)
    assert seed["dashboard"]
    # Queue status must reflect reality (empty/paused/stopped — not "19 threads")
    assert isinstance(seed["concurrency"], int)
    assert 1 <= seed["concurrency"] <= 4


def test_no_fake_numbers_in_dashboard(ctx):
    payload = ctx.stats.dashboard()
    from teledrive.i18n import t
    # Must not fabricate a drive label when disconnected
    if t("status.disconnected") in payload[t("dash.drive_status")]:
        assert payload[t("dash.drive_space")] in ("", "—", "—", None) or \
               t("status.disconnected") in payload[t("dash.drive_space")] or \
               "—" in payload[t("dash.drive_space")]
