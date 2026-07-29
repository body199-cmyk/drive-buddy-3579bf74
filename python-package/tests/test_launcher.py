"""Launcher contract tests (Constitution: one context, no default public link)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from teledrive import action_registry, app_context

LAUNCHER_PATH = Path(__file__).resolve().parent.parent / "teledrive_launcher.py"


def _load_launcher():
    spec = importlib.util.spec_from_file_location("teledrive_launcher", LAUNCHER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["teledrive_launcher"] = module
    spec.loader.exec_module(module)
    return module


def test_launcher_imports_the_real_bootstrap_api():
    module = _load_launcher()
    from teledrive import bootstrap

    assert module.bootstrap is bootstrap
    assert callable(bootstrap.run)
    assert not hasattr(bootstrap, "bootstrap"), "bootstrap exposes run(), not bootstrap()"


def test_check_mode_needs_no_credentials(monkeypatch, capsys):
    module = _load_launcher()
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)

    assert module.main(["--check"]) == 0
    out = capsys.readouterr().out
    assert "binding check ok" in out
    assert str(len(list(action_registry.ready_specs()))) in out


def test_check_mode_resolves_every_ready_service_path():
    ctx = app_context.create_context()
    for spec in action_registry.ready_specs():
        assert callable(ctx.resolve(spec.service_path))


def test_launch_uses_the_single_context_and_never_shares_by_default(monkeypatch):
    module = _load_launcher()
    calls: dict[str, object] = {}
    contexts: list[object] = []

    def fake_launch(ctx=None, share=False, inline=True):
        calls["share"] = share
        calls["ctx"] = ctx
        contexts.append(ctx)
        return ctx

    monkeypatch.setattr(module, "launch", fake_launch)
    assert module.main([]) == 0
    assert calls["share"] is False
    assert calls["ctx"] is app_context.get_context()
    assert len(contexts) == 1


def test_share_is_explicit_opt_in(monkeypatch):
    module = _load_launcher()
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        module,
        "launch",
        lambda ctx=None, share=False, inline=True: seen.update(share=share),
    )
    module.main(["--share"])
    assert seen["share"] is True


def test_app_launch_does_not_create_a_second_context(monkeypatch):
    from teledrive import app

    ctx = app_context.create_context()
    created: list[int] = []
    monkeypatch.setattr(app.bootstrap, "run", lambda: created.append(1))

    class FakeDemo:
        def launch(self, **kwargs):
            self.kwargs = kwargs

    demo = FakeDemo()
    monkeypatch.setattr(app, "build", lambda c: demo)

    returned = app.launch(ctx)
    assert returned is ctx
    assert created == [], "launch(ctx) must not bootstrap a second time"
    assert demo.kwargs["share"] is False


@pytest.mark.parametrize("flag", ["--check", "--share", "--no-share"])
def test_parser_accepts_documented_flags(flag):
    module = _load_launcher()
    assert module.build_parser().parse_args([flag]) is not None


def test_launch_defaults_to_non_blocking_and_stores_the_handle(monkeypatch):
    from teledrive import app

    ctx = app_context.create_context()

    class FakeDemo:
        def __init__(self):
            self.kwargs = {}
            self.closed = False

        def launch(self, **kwargs):
            self.kwargs = kwargs

        def close(self):
            self.closed = True

    demo = FakeDemo()
    monkeypatch.setattr(app, "build", lambda c: demo)

    app.launch(ctx)
    assert demo.kwargs["prevent_thread_lock"] is True
    assert ctx.ui is demo

    app.launch(ctx, blocking=True)
    assert demo.kwargs["prevent_thread_lock"] is False
    ctx.ui = None


def test_cli_launcher_blocks_so_the_process_stays_alive(monkeypatch):
    module = _load_launcher()
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        module,
        "launch",
        lambda ctx=None, share=False, inline=True, blocking=False: seen.update(
            blocking=blocking
        ),
    )
    module.main([])
    assert seen["blocking"] is True
