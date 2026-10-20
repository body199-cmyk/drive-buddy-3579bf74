"""Modern Web Dashboard (FastAPI + AJAX Polling) — M46-T01/T02 contracts.

The dashboard is an adapter over the one ApplicationContext: these tests
prove it serves live (never fabricated) metrics, dispatches only through
the validated React bridge, refuses secret-bearing actions, and really
serves HTTP from its isolated server thread.

M46-T02 regression pinned here: uvicorn answers a startup failure with
``sys.exit``. When the dashboard previously ran as a task on ``ctx.aio``
that ``SystemExit`` killed the whole application loop (web page absent
+ Gradio frozen). A failed dashboard launch must now raise cleanly,
leave ``ctx.web_dashboard`` empty, and leave ``ctx.aio`` fully alive.
"""
from __future__ import annotations

import json
import socket
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

from teledrive import telegram_auth as telegram_auth_module
from teledrive import web_dashboard
from teledrive.web_dashboard import (
    HTML_PAGE,
    TeleDriveWebBridge,
    create_web_app,
    launch_web_dashboard,
    stop_web_dashboard,
)

SOURCE = Path(web_dashboard.__file__).read_text(encoding="utf-8")


def _client(ctx):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")  # TestClient transport (via gradio deps)
    from fastapi.testclient import TestClient

    return TestClient(create_web_app(ctx))


def test_module_imports_without_web_framework_at_top_level():
    # FastAPI/uvicorn are lazy: the classic Gradio fallback must never
    # break just because the modern stack is absent.
    assert "from fastapi import" not in SOURCE.split("def create_web_app")[0]
    assert "import uvicorn" not in SOURCE.split("def launch_web_dashboard")[0]


def test_no_ad_hoc_application_loop_or_wildcard_cors_or_fake_engine():
    # The application loop stays AsyncRuntime's alone; the HTTP server
    # runs in its dedicated thread via server.run() (M46-T02 isolation).
    for needle in ("asyncio.new_event_loop(", "asyncio.run(", "run_until_complete("):
        assert needle not in SOURCE
    assert "server.run()" in SOURCE
    assert "ctx.aio.schedule(server.serve())" not in SOURCE
    assert 'allow_origins=["*"]' not in SOURCE
    # The Drive payload's private download runner must not come back:
    # transfers belong to QueueManager/TransferManager only.
    assert "iter_messages" not in SOURCE
    assert "download_media" not in SOURCE
    assert "fast_telethon" not in SOURCE


def test_page_is_self_contained_and_polls_relative_metrics():
    assert "api/metrics" in HTML_PAGE
    assert "configurePolling(1000)" in HTML_PAGE
    assert "setInterval(pollMetrics,interval)" in HTML_PAGE
    # Zero external CDN: no script/link is fetched from the network.
    assert 'src="http' not in HTML_PAGE
    assert 'href="http' not in HTML_PAGE
    # Server strings are rendered safely, never through innerHTML.
    assert "textContent" in HTML_PAGE
    assert "innerHTML" not in HTML_PAGE


def test_page_exposes_the_missing_controls_without_moving_telegram_secrets():
    for element_id in (
        "telegramLoginLink", "btnTelegramLogout", "selectedFolderName",
        "folderList", "newFolderName", "themeIn", "concurrencyIn",
        "autoRefreshIn", "btnRecovery", "btnCheckpoint", "btnBuildZip",
        "btnRememberLink", "btnClearRememberedLink", "candidateSearchIn",
        "btnApplyFilters", "btnResetFilters", "btnSelectRange",
        "btnSelectGroup", "selectGroupIn", "btnQueueRefresh",
        "btnClearCompleted", "btnClearIncomplete",
    ):
        assert f'id="{element_id}"' in HTML_PAGE
    for action_id in (
        "drive.list_folders", "drive.create_folder", "drive.select_folder",
        "settings.set_theme", "settings.set_concurrency",
        "settings.set_auto_refresh", "telegram.logout",
        "analyze.remember_link", "analyze.clear_remembered_link",
        "analyze.apply_filters", "analyze.select_range",
        "analyze.select_group", "queue.refresh", "queue.clear_completed",
        "queue.clear_incomplete", "queue.pause_item", "queue.resume_item",
        "queue.stop_item", "queue.retry_item",
    ):
        assert f'"{action_id}"' in HTML_PAGE
    # Secret-bearing Telegram login actions must stay outside the HTTP page.
    for action_id in (
        "telegram.set_credentials", "telegram.send_code",
        "telegram.verify_code", "telegram.verify_password",
    ):
        assert action_id not in HTML_PAGE


def test_page_analyze_modes_are_the_canonical_scanner_modes():
    """M46-T03/M47-T02 regressions: ``channel`` is not a scanner mode, and
    defaulting to ``message`` made a bare channel link always fail. The
    page now defaults to a browser-side Auto choice that resolves to a
    canonical scanner mode before the bridge is called, while every
    manual scanner mode and its inputs remain available."""
    import re

    from teledrive.media_scanner import SCAN_MODES

    mode_select = re.search(r'<select id="modeIn"[^>]*>(.*?)</select>', HTML_PAGE, re.S)
    assert mode_select, "mode dropdown missing"
    offered = re.findall(r'<option value="([a-z_]+)"', mode_select.group(1))
    assert offered[0] == "auto", "Auto must be the safe default for channel links"
    assert 'value="auto" selected' in mode_select.group(1)
    assert set(offered) == {"auto", *SCAN_MODES}
    assert "function inspectTelegramLink" in HTML_PAGE
    assert "function resolveAnalyzeMode" in HTML_PAGE
    assert 'return info.kind==="message" ? "message" : "chat"' in HTML_PAGE
    assert 'mode:mode,mediaTypes:selectedMediaTypes()' in HTML_PAGE
    # The inputs each mode consumes exist and are actually sent.
    for element_id in ("messageIdIn", "startIdIn", "endIdIn", "limitIn"):
        assert f'id="{element_id}"' in HTML_PAGE
    for payload_key in ("messageId", "startId", "endId", "limit"):
        assert f"{payload_key}:" in HTML_PAGE or f"{payload_key}=" in HTML_PAGE
    assert "syncModeFields" in HTML_PAGE
    assert 'mode==="auto" || mode==="latest" || mode==="chat"' in HTML_PAGE


def test_page_renders_analyze_candidates_with_selection():
    """M46-T03/M47-T02: analyze results must be visible and selectable in
    their own internally scrolling pane (about ten rows high), rather
    than stretching the whole page for a large channel."""
    assert 'id="cBody"' in HTML_PAGE
    assert 'id="candidatePane"' in HTML_PAGE
    assert 'class="scroll-pane candidate-pane"' in HTML_PAGE
    assert ".candidate-pane{height:430px;max-height:62vh}" in HTML_PAGE
    assert "overscroll-behavior:contain" in HTML_PAGE
    assert "visibleRows.slice(0,1000)" in HTML_PAGE
    assert "state.candidates" in HTML_PAGE
    assert "item.messageId" in HTML_PAGE
    assert "item.groupId" in HTML_PAGE
    assert '"analyze.toggle_row"' in HTML_PAGE
    assert "sourceId:item.sourceId" in HTML_PAGE
    assert '"analyze.clear_selection"' in HTML_PAGE


def test_page_script_has_no_escaped_quote_artifacts():
    """The page is a Python raw string: a stray backslash before a quote
    in the embedded JS is a browser SyntaxError that kills the whole
    script (caught by `node --check` during M46-T03)."""
    assert '\\"' not in HTML_PAGE


def test_page_dom_references_and_prior_controls_survive_the_redesign():
    """M47-T02 guardrail: reorganizing the page must not lose a control or
    leave JavaScript pointing at a missing element."""
    import re

    ids = re.findall(r'id="([^"]+)"', HTML_PAGE)
    assert len(ids) == len(set(ids)), "duplicate element ids would break wiring"
    refs = set(re.findall(r'\$\("([^"]+)"\)', HTML_PAGE))
    refs.update(re.findall(r'setText\("([^"]+)"', HTML_PAGE))
    refs.update(re.findall(r'(?:numOrNull|floatOrNull)\("([^"]+)"', HTML_PAGE))
    assert refs <= set(ids), f"missing DOM ids: {sorted(refs - set(ids))}"

    for element_id in (
        "btnRefreshMetrics", "telegramLoginLink", "btnTelegramStatus",
        "btnTelegramLogout", "btnDriveConnect", "btnDriveReconnect",
        "btnDriveStatus", "btnDriveQuota", "btnFolderUp",
        "btnFolderRefresh", "btnCreateFolder", "btnAnalyze",
        "btnSelectAll", "btnClearSel", "btnEnqueue", "btnStart",
        "btnPause", "btnResume", "btnStop", "btnRetry", "btnConcurrency",
        "btnLogsRefresh", "btnLogsSearch", "btnLogsDownload",
        "btnRecovery", "btnCheckpoint", "btnBuildZip", "btnColabCells",
        "newFolderName", "linkIn", "modeIn", "messageIdIn", "startIdIn",
        "endIdIn", "limitIn", "themeIn", "concurrencyIn", "autoRefreshIn",
        "logsLevel", "logsQuery",
    ):
        assert element_id in ids

    for action_id in (
        "telegram.status", "telegram.logout", "drive.connect",
        "drive.reconnect", "drive.status", "drive.refresh_quota",
        "drive.list_folders", "drive.create_folder", "drive.select_folder",
        "analyze.run", "analyze.toggle_row", "analyze.select_all",
        "analyze.clear_selection", "analyze.enqueue_selected",
        "settings.set_theme", "settings.set_concurrency",
        "settings.set_auto_refresh", "logs.refresh", "logs.search",
        "logs.download", "recovery.restore", "maintenance.checkpoint",
        "export.build_zip", "export.colab_cells",
    ):
        assert f'"{action_id}"' in HTML_PAGE


def test_page_has_three_themes_clear_workflow_and_independent_panes():
    import re

    theme_select = re.search(r'<select id="themeIn"[^>]*>(.*?)</select>', HTML_PAGE, re.S)
    assert theme_select
    assert re.findall(r'<option value="([a-z]+)"', theme_select.group(1)) == [
        "light", "dim", "dark",
    ]
    for theme in ("light", "dim", "dark"):
        assert f'data-theme-choice="{theme}"' in HTML_PAGE
    assert '--bg:#15202b' in HTML_PAGE  # X Dim background
    assert '--blue:#1d9bf0' in HTML_PAGE  # X blue action colour
    assert 'const THEMES=["light","dim","dark"]' in HTML_PAGE
    assert "function saveTheme" in HTML_PAGE
    assert "if(THEMES.includes(st.webTheme)) applyTheme(st.webTheme)" in HTML_PAGE
    assert "st.analyze.sourceLink" in HTML_PAGE

    for step_id in (
        "stepLinkConnect", "stepLinkDestination", "stepLinkAnalyze",
        "stepLinkResults", "stepLinkTransfer", "nextStepText",
    ):
        assert f'id="{step_id}"' in HTML_PAGE
    assert "function updateWorkflow" in HTML_PAGE
    assert 'class="scroll-pane queue-pane"' in HTML_PAGE
    assert ".queue-pane{height:350px;max-height:54vh}" in HTML_PAGE
    assert "queue.pause_item" in HTML_PAGE and "queue.retry_item" in HTML_PAGE


def test_metrics_reflect_the_real_empty_runtime(ctx):
    metrics = TeleDriveWebBridge(ctx).get_system_metrics()
    assert metrics["ok"] is True
    assert metrics["is_running"] is False
    assert metrics["total_speed_mbps"] == 0.0
    assert metrics["progress"]["done_files"] == 0
    # Empty queue stays empty — no synthesized rows for presentation.
    assert metrics["state"]["queue"] == []
    assert metrics["free_disk_bytes"] > 0
    json.dumps(metrics)  # fully JSON-serializable for the polling page


def test_http_endpoints(ctx):
    client = _client(ctx)
    page = client.get("/")
    assert page.status_code == 200
    assert "TeleDrive v5.0 Turbo" in page.text

    health = client.get("/api/health")
    assert health.status_code == 200 and health.json()["ok"] is True

    metrics = client.get("/api/metrics")
    assert metrics.status_code == 200
    assert metrics.headers["cache-control"].startswith("no-store")
    assert metrics.json()["state"]["queue"] == []

    state = client.get("/api/state")
    assert state.status_code == 200
    assert state.json()["actionId"] == "bridge.snapshot"


class _FakeScanDocument:
    def __init__(self, message_id: int):
        self.id = f"doc-{message_id}"
        self.file_unique_id = self.id
        self.size = 1000 + message_id
        self.mime_type = "video/mp4"
        self.attributes = [SimpleNamespace(file_name=f"video{message_id}.mp4")]


class _FakeScanMessage:
    def __init__(self, message_id: int):
        self.id = message_id
        self.date = "2026-01-01T00:00:00+00:00"
        self.media = object()
        self.photo = None
        self.video = _FakeScanDocument(message_id)
        self.voice = None
        self.audio = None
        self.sticker = None
        self.gif = None
        self.animation = None
        self.document = None


class _FakeScanTelegram:
    def __init__(self):
        self.messages = [_FakeScanMessage(1), _FakeScanMessage(2)]

    async def get_entity(self, _chat):
        return SimpleNamespace(
            id=12345, title="TestChat", username="testchat", broadcast=True
        )

    async def get_message(self, _chat, message_id):
        return next(item for item in self.messages if item.id == int(message_id))

    async def iter_messages(self, _chat, limit=None, **_kwargs):
        for item in self.messages[:limit]:
            yield item


def test_http_analyze_channel_and_message_links(ctx):
    """The exact HTTP bridge payload used by the redesigned page must
    return real candidates for both a channel and a direct message, and
    must name the reason when manual message mode is used incorrectly."""
    ctx.telegram_auth.state = telegram_auth_module.AUTHORIZED
    ctx.telegram_auth.client = _FakeScanTelegram()
    client = _client(ctx)

    def analyze(link, mode, message_id=None):
        response = client.post(
            "/api/action",
            json={
                "actionId": "analyze.run",
                "payload": {
                    "link": link,
                    "mode": mode,
                    "mediaTypes": ["all"],
                    "messageId": message_id,
                    "startId": None,
                    "endId": None,
                    "limit": 200,
                },
                "language": "ar",
            },
        )
        assert response.status_code == 200
        return response.json()

    channel = analyze("https://t.me/testchat", "chat")
    assert channel["status"] == "ok"
    candidates = channel["state"]["candidates"]
    assert [item["name"] for item in candidates] == ["video1.mp4", "video2.mp4"]
    assert [item["messageId"] for item in candidates] == [1, 2]
    assert {item["groupId"] for item in candidates} == {"-10012345"}

    message = analyze("https://t.me/testchat/2", "message")
    assert message["status"] == "ok"
    assert [item["messageId"] for item in message["state"]["candidates"]] == [2]

    wrong_mode = analyze("https://t.me/testchat", "message")
    assert wrong_mode["status"] == "error"
    assert "وضع الرسالة يحتاج رقم رسالة موجبًا" in wrong_mode["message"]


def test_index_and_metrics_render_saved_dim_theme(ctx):
    ctx.handlers.h_settings_set_theme("dim")
    client = _client(ctx)
    assert 'data-theme="dim"' in client.get("/").text
    assert client.get("/api/metrics").json()["state"]["webTheme"] == "dim"


def test_index_renders_saved_theme_and_escaped_secure_gradio_handoff(ctx):
    ctx.handlers.h_settings_set_theme("dark")
    ctx.gradio_proxy_url = "https://colab.example/gradio?cell=4&view=secure"
    page = _client(ctx).get("/").text
    assert 'data-theme="dark"' in page
    assert 'data-gradio-available="true"' in page
    assert 'href="https://colab.example/gradio?cell=4&amp;view=secure"' in page
    assert "__INITIAL_THEME__" not in page
    assert "__GRADIO_URL__" not in page


def test_index_refuses_non_http_gradio_login_link(ctx):
    ctx.gradio_proxy_url = "javascript:alert(1)"
    page = _client(ctx).get("/").text
    assert 'data-gradio-available="false"' in page
    assert 'href="#"' in page
    assert "javascript:" not in page


def test_web_folder_actions_browse_create_and_select_through_live_drive(ctx):
    folder_mime = "application/vnd.google-apps.folder"

    class Execute:
        def __init__(self, callback):
            self.callback = callback

        def execute(self):
            return self.callback()

    class FakeDrive:
        def __init__(self):
            self.folders = [{"id": "folder-a", "name": "Alpha", "mimeType": folder_mime}]

        def about(self):
            class About:
                def get(self, **_kwargs):
                    return Execute(lambda: {
                        "user": {"emailAddress": "drive@example.test"},
                        "storageQuota": {"limit": "1000", "usage": "250"},
                    })
            return About()

        def files(self):
            drive = self

            class Files:
                def list(self, **_kwargs):
                    return Execute(lambda: {"files": [
                        {"id": item["id"], "name": item["name"]}
                        for item in drive.folders
                    ]})

                def create(self, body=None, **_kwargs):
                    item = {
                        "id": "folder-new",
                        "name": body["name"],
                        "mimeType": folder_mime,
                    }
                    drive.folders.append(item)
                    return Execute(lambda: {"id": item["id"], "name": item["name"]})

                def get(self, fileId=None, **_kwargs):
                    item = next(folder for folder in drive.folders if folder["id"] == fileId)
                    return Execute(lambda: item)

            return Files()

    drive = FakeDrive()
    ctx.drive_auth._factory = lambda: drive
    ctx.handlers.h_drive_connect()
    client = _client(ctx)

    listed = client.post(
        "/api/action", json={"actionId": "drive.list_folders", "payload": {"parentId": "root"}}
    ).json()
    assert listed["status"] == "ok"
    assert listed["data"]["folders"] == [{"id": "folder-a", "name": "Alpha"}]

    created = client.post(
        "/api/action",
        json={"actionId": "drive.create_folder", "payload": {"name": "Archive", "parentId": "root"}},
    ).json()
    assert created["status"] == "ok"
    assert created["state"]["folder"] == {"id": "folder-new", "name": "Archive"}

    selected = client.post(
        "/api/action", json={"actionId": "drive.select_folder", "payload": {"folderId": "folder-a"}}
    ).json()
    assert selected["status"] == "ok"
    assert selected["state"]["folder"] == {"id": "folder-a", "name": "Alpha"}


def test_action_endpoint_uses_the_validated_bridge(ctx):
    client = _client(ctx)
    ok = client.post(
        "/api/action",
        json={"actionId": "queue.refresh", "payload": {}, "language": "ar"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "ok"
    assert ok.json()["requestId"].startswith("web-")  # server-generated id

    unknown = client.post("/api/action", json={"actionId": "nope.nope", "payload": {}})
    assert unknown.json()["status"] == "error"
    assert unknown.json()["errorKey"] == "bridge.unknown_action"


def test_secret_actions_are_refused_over_http(ctx):
    client = _client(ctx)
    refused = client.post(
        "/api/action",
        json={
            "actionId": "telegram.set_credentials",
            "payload": {"api_id": "123", "api_hash": "must-not-travel"},
        },
    )
    body = refused.json()
    assert body["status"] == "blocked"
    assert body["errorKey"] in {"bridge.secure_gradio_only", "bridge.secret_payload_refused"}
    assert "must-not-travel" not in refused.text


def test_queue_routes_are_allowlisted(ctx):
    client = _client(ctx)
    refused = client.post("/api/queue/wipe_everything")
    assert refused.json()["ok"] is False
    assert refused.json()["errorKey"] == "web.unknown_queue_action"

    paused = client.post("/api/queue/pause")  # idle pause is a safe no-op
    assert paused.status_code == 200
    assert "metrics" in paused.json()


def test_busy_port_raises_cleanly_and_the_application_loop_survives(ctx):
    """M46-T02: a dead dashboard must never take ctx.aio down with it."""
    pytest.importorskip("uvicorn")
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    port = int(blocker.getsockname()[1])
    try:
        assert ctx.aio.is_running
        with pytest.raises(RuntimeError, match="already in use"):
            launch_web_dashboard(ctx, port=port)
        # No zombie handle, and the one application loop is untouched:
        # this is exactly what kept Gradio responsive in the live bug.
        assert ctx.web_dashboard is None
        assert ctx.aio.is_running

        async def _ping() -> str:
            return "pong"

        assert ctx.aio.run(_ping(), timeout=5) == "pong"
    finally:
        blocker.close()


def test_launch_serves_from_isolated_thread_and_is_idempotent(ctx):
    pytest.importorskip("uvicorn")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])
    server = launch_web_dashboard(ctx, port=port)
    try:
        assert ctx.web_dashboard is server
        # A second launch must never create a second HTTP server.
        assert launch_web_dashboard(ctx, port=port) is server
        deadline = time.time() + 15
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(  # noqa: S310 - loopback test server
                    f"http://127.0.0.1:{port}/api/health", timeout=2
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                assert payload["ok"] is True
                break
            except Exception as exc:  # server still starting
                last_error = exc
                time.sleep(0.2)
        else:  # pragma: no cover - failure path
            raise AssertionError(f"web dashboard never became healthy: {last_error}")
    finally:
        assert stop_web_dashboard(ctx) is True
        assert ctx.web_dashboard is None
        assert stop_web_dashboard(ctx) is False  # idempotent
