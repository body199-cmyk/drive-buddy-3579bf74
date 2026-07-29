"""Handlers must call the exact service_path declared in ACTION_SPECS."""
from __future__ import annotations

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
    "analyze.apply_filters": ([], "", None, None, "", "", "", ""),
    "logs.search": ("query",),
    "settings.set_concurrency": ("safe",),
    "settings.set_theme": ("dark",),
    "queue.pause_item": ("id",),
    "queue.resume_item": ("id",),
    "queue.stop_item": ("id",),
    "queue.retry_item": ("id",),
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
