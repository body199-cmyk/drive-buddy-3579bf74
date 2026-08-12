"""Handlers must call the exact service_path declared in ACTION_SPECS."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from teledrive import action_registry


class Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, action_id, *args, **kwargs):
        self.calls.append(action_id)
        raise _Stop(action_id)


class _Stop(Exception):
    pass


ARGS = {
    "telegram.set_credentials": ("1", "hash"),
    "telegram.send_code": ("+971500000000",),
    "telegram.verify_code": ("12345",),
    "telegram.verify_password": ("pw",),
    "drive.list_folders": ("root",),
    "drive.create_folder": ("name", "root"),
    "drive.select_folder": ("name :: id",),
    "analyze.run": ("https://t.me/x/1", "auto"),
    "analyze.set_mode": ("message",),
    "analyze.apply_filters": ([], "", None, None, "", "", "", ""),
    "analyze.toggle_row": (SimpleNamespace(index=(0, 0), value="☐"),),
    "analyze.select_range": ("1", "10"),
    "analyze.select_group": ("My Chat :: 12345",),
    "logs.search": ("query",),
    "settings.set_concurrency": ("safe",),
    "settings.set_theme": ("dark",),
    "queue.pause_item": ("id",),
    "queue.resume_item": ("id",),
    "queue.stop_item": ("id",),
    "queue.retry_item": ("id",),
    "react.bridge.request": ({
        "requestId": "contract-request",
        "actionId": "queue.refresh",
        "payload": {},
        "language": "ar",
    },),
}


@pytest.mark.parametrize("spec", action_registry.ACTION_SPECS, ids=lambda s: s.action_id)
def test_handler_calls_declared_service(ctx, monkeypatch, spec):
    recorder = Recorder()
    monkeypatch.setattr(ctx.handlers, "call", recorder)
    handler = getattr(ctx.handlers, spec.handler_name)
    handler(*ARGS.get(spec.action_id, ()))
    assert recorder.calls == [spec.action_id]


@pytest.mark.parametrize("spec", action_registry.ACTION_SPECS, ids=lambda s: s.action_id)
def test_handler_never_raises_to_the_ui(ctx, monkeypatch, spec):
    def boom(*args, **kwargs):
        raise RuntimeError("api_hash=SECRET123 boom")

    monkeypatch.setattr(ctx.handlers, "call", boom)
    handler = getattr(ctx.handlers, spec.handler_name)
    result = handler(*ARGS.get(spec.action_id, ()))
    text = str(result)
    assert "SECRET123" not in text
    assert "Traceback" not in text


class ServiceSpy:
    """Records that the declared service method itself was invoked."""

    def __init__(self):
        self.hits = 0

    def __call__(self, *args, **kwargs):
        self.hits += 1
        raise _Stop("service reached")


@pytest.mark.parametrize("spec", action_registry.ACTION_SPECS, ids=lambda s: s.action_id)
def test_handler_reaches_the_real_service_object(ctx, monkeypatch, spec):
    """End-to-end spy: no stubbing of Handlers.call, patch the service itself.

    This proves the declared service_path resolves on the live context AND that
    the handler dispatches through it, closing the gap left by the
    Handlers.call-level spy above.
    """
    service_name, _, method_name = spec.service_path.partition(".")
    service = getattr(ctx, service_name)
    assert service is not None, f"{spec.action_id}: service {service_name!r} is None"
    assert hasattr(service, method_name), f"{spec.action_id}: {spec.service_path} missing"

    spy = ServiceSpy()
    monkeypatch.setattr(service, method_name, spy)
    handler = getattr(ctx.handlers, spec.handler_name)
    handler(*ARGS.get(spec.action_id, ()))
    assert spy.hits == 1, f"{spec.action_id} never reached {spec.service_path}"
