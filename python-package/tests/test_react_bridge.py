"""M24 bridge proofs: React -> official Gradio event -> existing handlers."""
from __future__ import annotations

import logging

from teledrive import action_registry, database as db
from teledrive.drive_auth import CONNECTED
from teledrive.errors import TeleDriveError
from teledrive.models import MediaItem
from teledrive.react_panel import ReactPanel
from teledrive.services import ScanResult

PROVES = ("react.bridge.request",)


def _request(action_id: str, payload=None, request_id: str = "request-1"):
    return {
        "requestId": request_id,
        "actionId": action_id,
        "payload": payload or {},
        "language": "ar",
    }


def _bridge(ctx):
    return ctx.handlers.react_bridge


def test_react_bridge_rejects_unknown_action(ctx):
    response = _bridge(ctx).handle(_request("missing.action"))
    assert response["status"] == "error"
    assert response["errorKey"] == "bridge.unknown_action"


def test_react_bridge_rejects_blocked_action(ctx):
    response = _bridge(ctx).handle(_request("telegram.verify_code"))
    assert response["status"] == "blocked"
    assert response["errorKey"] == "bridge.secure_gradio_only"


def test_react_bridge_calls_existing_registered_handler(ctx, monkeypatch):
    calls = []

    def handler():
        calls.append("queue.refresh")
        return "ok", []

    monkeypatch.setattr(ctx.handlers, "h_queue_refresh", handler)
    response = _bridge(ctx).handle(_request("queue.refresh"))
    assert response["status"] == "ok"
    assert calls == ["queue.refresh"]
    assert action_registry.get("react.bridge.request") is not None


def test_react_bridge_redacts_response_and_error(ctx, monkeypatch):
    secret = "0123456789abcdef0123456789abcdef"
    sentinel = f"api_hash={secret}"

    def safe_result(*_args):
        return {"value": sentinel}, "ok"

    monkeypatch.setattr(ctx.handlers, "h_logs_search", safe_result)
    response = _bridge(ctx).handle(_request("logs.search", {"query": "x"}))
    assert response["status"] == "ok"
    assert secret not in str(response)
    assert "<redacted>" in str(response)

    def failed_result(*_args):
        return f"⚠️ {sentinel} [abcd1234]", None

    monkeypatch.setattr(ctx.handlers, "h_logs_search", failed_result)
    failed = _bridge(ctx).handle(_request("logs.search", {"query": "x"}, "request-2"))
    assert failed["status"] == "error"
    assert secret not in str(failed)
    assert "abcd1234" in failed["message"]


def test_react_bridge_does_not_log_credentials(ctx, caplog):
    sentinel = "credential-value-that-must-not-be-logged"
    caplog.set_level(logging.DEBUG)
    response = _bridge(ctx).handle(
        _request("queue.refresh", {"password": sentinel})
    )
    assert response["status"] == "blocked"
    assert response["errorKey"] == "bridge.secret_payload_refused"
    assert sentinel not in caplog.text


def test_react_bridge_snapshot_has_real_empty_state(ctx):
    snapshot = _bridge(ctx).initial_response()["state"]
    assert snapshot["telegram"]["status"] == "DISCONNECTED"
    assert snapshot["drive"]["status"] == "DISCONNECTED"
    assert snapshot["drive"]["quotaUsed"] is None
    assert snapshot["folder"] == {"id": None, "name": None}
    assert snapshot["queue"] == []
    assert snapshot["candidates"] == []
    assert snapshot["concurrency"] == 2


def test_react_bridge_folder_id_is_persisted_by_existing_service(ctx):
    class Execute:
        def execute(self):
            return {
                "id": "folder-real-id",
                "name": "Live folder",
                "mimeType": "application/vnd.google-apps.folder",
            }

    class Files:
        def get(self, **_kwargs):
            return Execute()

    class Drive:
        def files(self):
            return Files()

    ctx.drive_auth.state = CONNECTED
    ctx.drive_auth.service = Drive()
    response = _bridge(ctx).handle(
        _request("drive.select_folder", {"folderId": "folder-real-id"})
    )
    assert response["status"] == "ok"
    assert response["state"]["folder"]["id"] == "folder-real-id"
    assert db.get_setting("drive_folder_id") == "folder-real-id"


def test_react_bridge_returns_localized_analyze_validation_failure(ctx, monkeypatch):
    def invalid_analyze(*_args, **_kwargs):
        raise TeleDriveError("message id missing", "err.scan_message_id")

    monkeypatch.setattr(ctx.scanner, "analyze", invalid_analyze)

    response = _bridge(ctx).handle(
        _request(
            "analyze.run",
            {
                "link": "https://t.me/example/10",
                "mode": "message",
                "mediaTypes": ["all"],
            },
        )
    )

    assert response["status"] == "error"
    assert response["errorKey"] == "bridge.action_failed"
    assert "وضع الرسالة يحتاج رقم رسالة موجبًا" in response["message"]
    assert "Action completed" not in response["message"]


def test_react_bridge_does_not_enqueue_during_analyze(ctx, monkeypatch):
    candidate = MediaItem(
        id="candidate-live",
        source_key="source-live",
        safe_name="live.bin",
        message_id=10,
        size_bytes=12,
    )
    enqueue_calls = []

    def analyze(*_args, **_kwargs):
        ctx.selection.set_candidates([candidate])
        return ScanResult(total=1, total_bytes=12, scope="message", rows=[])

    monkeypatch.setattr(ctx.scanner, "analyze", analyze)
    monkeypatch.setattr(
        ctx.queue_manager,
        "bulk_enqueue",
        lambda items: enqueue_calls.append(list(items)),
    )
    response = _bridge(ctx).handle(
        _request(
            "analyze.run",
            {
                "link": "https://t.me/example/10",
                "mode": "message",
                "messageId": 10,
                "mediaTypes": ["all"],
            },
        )
    )
    assert response["status"] == "ok"
    assert response["state"]["candidates"][0]["sourceId"] == "candidate-live"
    assert enqueue_calls == []
    assert db.list_items() == []


def test_react_bridge_uses_single_application_context(ctx):
    bridge = _bridge(ctx)
    assert bridge._ctx is ctx
    assert ctx.handlers.live_ui_state.ctx is ctx
    assert ctx.handlers is ctx.handlers


def test_react_bridge_does_not_create_event_loop(ctx):
    runtime = ctx.aio
    thread = runtime._thread
    response = _bridge(ctx).handle(_request("queue.refresh"))
    assert response["status"] == "ok"
    assert ctx.aio is runtime
    assert ctx.aio._thread is thread


def test_react_bridge_uses_registered_action_once():
    matches = [
        spec for spec in action_registry.ACTION_SPECS
        if spec.action_id == "react.bridge.request"
    ]
    assert len(matches) == 1
    assert matches[0].service_path == "handlers.bridge_request"


def test_react_panel_uses_official_submit_value_transport(ctx):
    panel = ReactPanel(value=ctx.handlers.bridge_initial_response())
    assert "trigger('submit')" in panel.js_on_load
    assert "watch('value'" in panel.js_on_load
    assert "fetch(" not in panel.js_on_load
    assert "XMLHttpRequest" not in panel.js_on_load
    assert "WebSocket" not in panel.js_on_load
    assert panel.preprocess(panel.value)["actionId"] == "bridge.snapshot"
