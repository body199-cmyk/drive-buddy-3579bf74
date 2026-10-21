from pathlib import Path


def test_universal_downloader_is_registered_as_a_dashboard_section():
    """The navigation allowlist must include every section users can open."""
    dashboard = (
        Path(__file__).resolve().parents[1]
        / "teledrive"
        / "web_dashboard.py"
    ).read_text(encoding="utf-8")

    assert 'const DASHBOARD_SECTIONS=["overview","universal",' in dashboard
    assert 'id="universal" data-tab-panel="universal"' in dashboard
    assert 'data-section-target="universal"' in dashboard
