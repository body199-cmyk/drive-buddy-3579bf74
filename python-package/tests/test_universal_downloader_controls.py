from __future__ import annotations

from threading import Event
from pathlib import Path

from teledrive.universal_downloader import UniversalDownloadManager


def _manager_with_task(status: str = "downloading"):
    manager = UniversalDownloadManager(ctx=None)
    task_id = "udl-test1234"
    event = Event()
    manager._tasks.append({"id": task_id, "status": status, "status_ar": status})
    manager._cancel_events[task_id] = event
    return manager, task_id, event


def test_cancel_task_marks_active_download_for_cancellation():
    manager, task_id, event = _manager_with_task("downloading")

    result = manager.cancel_task(task_id)

    assert result["ok"] is True
    assert event.is_set()
    task = next(item for item in manager._tasks if item["id"] == task_id)
    assert task["status"] == "cancelling"


def test_cancel_task_refuses_to_interrupt_drive_upload():
    manager, task_id, event = _manager_with_task("uploading")

    result = manager.cancel_task(task_id)

    assert result["ok"] is False
    assert event.is_set() is False
    task = next(item for item in manager._tasks if item["id"] == task_id)
    assert task["status"] == "uploading"


def test_dashboard_exposes_cancel_and_speed_without_unsafe_html_rendering():
    dashboard_path = Path(__file__).parents[1] / "teledrive" / "web_dashboard.py"
    source = dashboard_path.read_text(encoding="utf-8")

    assert '@app.post("/api/universal/cancel")' in source
    assert 'fetch("api/universal/cancel"' in source
    assert "speed_bps" in source
    assert "document.createElement" in source
    assert "innerHTML" not in source
