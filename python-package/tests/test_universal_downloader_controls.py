from __future__ import annotations

import pytest

from threading import Event
from pathlib import Path

from teledrive.universal_downloader import UniversalDownloadManager


def _manager_with_task(status: str = "downloading"):
    manager = UniversalDownloadManager(ctx=None)
    task_id = "udl-test1234"
    event = Event()
    manager._tasks.append({
        "id": task_id, "status": status, "status_ar": status,
        "pause_supported": True, "url": "https://example.com/file.zip",
        "quality": "best", "folder_id": "folder-test", "folder_name": "Folder Test",
    })
    manager._cancel_events[task_id] = event
    resume_gate = Event()
    resume_gate.set()
    manager._resume_events[task_id] = resume_gate
    return manager, task_id, event


def test_cancel_task_marks_active_download_for_cancellation():
    manager, task_id, event = _manager_with_task("downloading")

    result = manager.cancel_task(task_id)

    assert result["ok"] is True
    assert event.is_set()
    task = next(item for item in manager._tasks if item["id"] == task_id)
    assert task["status"] == "cancelling"
    assert manager._resume_events[task_id].is_set()


def test_pause_and_resume_change_the_live_task_gate_and_status():
    manager, task_id, _cancel_event = _manager_with_task("downloading")

    paused = manager.pause_task(task_id)
    assert paused["ok"] is True
    task = next(item for item in manager._tasks if item["id"] == task_id)
    assert task["status"] == "paused"
    assert not manager._resume_events[task_id].is_set()

    resumed = manager.resume_task(task_id)
    assert resumed["ok"] is True
    assert task["status"] == "downloading"
    assert manager._resume_events[task_id].is_set()


def test_pause_wins_race_at_download_to_upload_boundary():
    manager, task_id, _cancel_event = _manager_with_task("downloading")
    assert manager.pause_task(task_id)["ok"] is True

    entered_upload = manager._begin_upload(task_id, status="uploading", status_ar="uploading")

    assert entered_upload is False
    assert manager._tasks[0]["status"] == "paused"

    assert manager.resume_task(task_id)["ok"] is True
    entered_upload = manager._begin_upload(task_id, status="uploading", status_ar="uploading")
    assert entered_upload is True
    assert manager._tasks[0]["status"] == "uploading"


def test_clear_finished_preserves_paused_tasks():
    manager, task_id, _cancel_event = _manager_with_task("paused")

    cleared = manager.clear_finished()

    assert cleared == 0
    assert manager._tasks[0]["id"] == task_id


def test_bulk_pause_and_resume_apply_to_real_eligible_tasks():
    manager, task_id, _cancel_event = _manager_with_task("downloading")

    paused = manager.bulk_action("pause")
    assert paused["ok"] is True
    assert paused["succeeded"] == 1
    assert manager._tasks[0]["status"] == "paused"

    resumed = manager.bulk_action("resume")
    assert resumed["ok"] is True
    assert resumed["succeeded"] == 1
    assert manager._tasks[0]["status"] == "downloading"


def test_bulk_retry_failed_restarts_failed_task(monkeypatch):
    manager, task_id, _cancel_event = _manager_with_task("failed")
    calls = []
    monkeypatch.setattr(
        manager, "start_download",
        lambda **kwargs: calls.append(kwargs) or {"ok": True, "message": "started"},
    )

    result = manager.bulk_action("retry_failed")

    assert result["ok"] is True
    assert result["succeeded"] == 1
    assert calls[0]["url"] == "https://example.com/file.zip"


def test_pause_refuses_backend_without_real_pause_support():
    manager, task_id, _cancel_event = _manager_with_task("downloading")
    manager._tasks[0]["pause_supported"] = False

    result = manager.pause_task(task_id)

    assert result["ok"] is False
    assert "غير مدعوم" in result["message"]
    assert manager._tasks[0]["status"] == "downloading"


def test_resume_refuses_non_paused_task():
    manager, task_id, _cancel_event = _manager_with_task("downloading")

    result = manager.resume_task(task_id)

    assert result["ok"] is False
    assert manager._resume_events[task_id].is_set()


def test_retry_task_restarts_only_failed_or_cancelled_with_saved_inputs(monkeypatch):
    manager, task_id, _cancel_event = _manager_with_task("failed")
    calls = []
    monkeypatch.setattr(
        manager, "start_download",
        lambda **kwargs: calls.append(kwargs) or {"ok": True, "message": "started"},
    )

    result = manager.retry_task(task_id)

    assert result["ok"] is True
    assert calls == [{
        "url": "https://example.com/file.zip",
        "quality": "best",
        "folder_id": "folder-test",
        "folder_name": "Folder Test",
    }]


def test_retry_task_refuses_running_task(monkeypatch):
    manager, task_id, _cancel_event = _manager_with_task("downloading")
    monkeypatch.setattr(manager, "start_download", lambda **kwargs: pytest.fail("must not start"))

    result = manager.retry_task(task_id)

    assert result["ok"] is False
    assert "الفاشلة" in result["message"]


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

    for action in ("cancel", "pause", "resume", "retry", "bulk"):
        assert f'@app.post("/api/universal/{action}")' in source
    assert 'fetch("api/universal/" + action' in source
    for button_id in ("btnUdlPauseAll", "btnUdlResumeAll", "btnUdlCancelAll", "btnUdlRetryFailed"):
        assert f'id="{button_id}"' in source
    assert 'runBulkAction("pause"' in source
    assert 'runBulkAction("resume"' in source
    assert 'runBulkAction("cancel"' in source
    assert 'runBulkAction("retry_failed"' in source
    assert 'addTaskAction("إيقاف مؤقت", "pause"' in source
    assert 'addTaskAction("استئناف", "resume"' in source
    assert 'addTaskAction("إعادة المحاولة", "retry"' in source
    assert "pause_supported" in source
    assert "speed_bps" in source
    assert "document.createElement" in source
    assert ".innerHTML =" not in source
    assert ".innerHTML=" not in source


def test_dashboard_universal_downloader_has_per_task_folder_picker_and_sends_folder_name():
    dashboard_path = Path(__file__).parents[1] / "teledrive" / "web_dashboard.py"
    source = dashboard_path.read_text(encoding="utf-8")

    assert 'id="btnUdlChooseFolder"' in source
    assert 'id="udlFolderPickerPanel"' in source
    assert 'drive.list_folders' in source
    assert 'folder_id: udlExplicitFolder.id, folder_name: udlExplicitFolder.name' in source
    assert 'folder_name = str(payload.get("folder_name") or "").strip()[:200] or None' in source
