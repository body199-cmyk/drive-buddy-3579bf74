"""M15-T06 — Colab proxy launch contract tests (mocks/fakes only).

These prove the launcher makes the UI reachable through the official Colab
``proxyPort`` proxy instead of the misleading ``https://localhost:<port>`` link,
without ever spinning up a real Gradio server, a real event loop, or a real
Telegram/Drive client. ``google.colab`` is faked via ``sys.modules`` so the
helper can be exercised on a non-Colab CI runner.

Pinned dependency: Gradio 6.20.0 — ``Blocks.launch`` takes ``server_name`` and
``server_port`` positionally and ``root_path`` as a keyword-only argument. The
exact signature was verified against the installed 6.20.0 wheel, not guessed.
"""
from __future__ import annotations

import os
import sys
import types
from types import SimpleNamespace

import pytest

from teledrive import app


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------


class FakeDemo:
    """Stand-in for a Gradio Blocks object: records launch kwargs, no server."""

    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    def launch(self, **kwargs: object) -> None:
        self.kwargs = dict(kwargs)

    def close(self) -> None:  # called by ApplicationContext.shutdown on teardown
        self.closed = True


@pytest.fixture()
def fake_demo(monkeypatch) -> FakeDemo:
    demo = FakeDemo()
    monkeypatch.setattr(app, "build", lambda c: demo)
    return demo


@pytest.fixture()
def fake_colab(monkeypatch) -> SimpleNamespace:
    """Inject a fake ``google.colab.output.eval_js`` returning a fixed proxy URL.

    Mirrors exactly what ``colab_proxy_url`` imports: ``google.colab.output``.
    The returned URL is the kind Colab's ``proxyPort`` produces
    (``https://...prod.colab.dev/``).
    """
    proxy_url = "https://5380-runtime.prod.colab.dev/"
    google = types.ModuleType("google")
    colab = types.ModuleType("google.colab")
    output = types.ModuleType("google.colab.output")
    kernel = types.ModuleType("google.colab.kernel")
    eval_js_calls: list[str] = []

    def eval_js(code: str) -> str:
        eval_js_calls.append(code)
        return proxy_url

    output.eval_js = eval_js
    colab.output = output
    colab.kernel = kernel
    google.colab = colab
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.colab", colab)
    monkeypatch.setitem(sys.modules, "google.colab.output", output)
    monkeypatch.setitem(sys.modules, "google.colab.kernel", kernel)
    return SimpleNamespace(proxy=proxy_url, eval_js_calls=eval_js_calls)


# --------------------------------------------------------------------------
# colab_proxy_url / is_colab
# --------------------------------------------------------------------------


def test_colab_proxy_url_returns_mocked_proxy_url(fake_colab):
    url = app.colab_proxy_url(7860)
    assert url == fake_colab.proxy
    # the helper must call the official proxyPort with the integer port
    assert fake_colab.eval_js_calls == ["google.colab.kernel.proxyPort(7860)"]


def test_colab_proxy_url_none_off_colab_without_importing():
    # A non-Colab runtime must not have google.colab available ...
    assert "google.colab" not in sys.modules
    # ... must return None (not raise) ...
    assert app.colab_proxy_url(7860) is None
    # ... and must not have imported google.colab as a side effect.
    assert "google.colab" not in sys.modules


def test_is_colab_false_off_colab_without_importing():
    assert app.is_colab() is False
    assert "google.colab" not in sys.modules


def test_is_colab_true_when_google_colab_importable(fake_colab):
    assert app.is_colab() is True


# --------------------------------------------------------------------------
# launch kwargs for the pinned Gradio 6.20.0 signature
# --------------------------------------------------------------------------


def test_launch_kwargs_match_pinned_gradio_contract():
    kw = app._launch_kwargs(
        share=False, inline=False, blocking=False, port=7860, root_path="https://x/"
    )
    # exactly the keys we intend to pass — no more, no less
    assert set(kw) == {
        "share",
        "inline",
        "quiet",
        "prevent_thread_lock",
        "server_name",
        "server_port",
        "root_path",
    }
    assert kw["share"] is False
    assert kw["inline"] is False
    assert kw["quiet"] is True
    assert kw["prevent_thread_lock"] is True
    assert kw["server_name"] == app.BIND_ADDRESS == "0.0.0.0"
    assert kw["server_port"] == 7860
    assert kw["root_path"] == "https://x/"


def test_launch_uses_share_false_binds_port_and_address_no_tunnel(ctx, fake_demo):
    app.launch(ctx)
    kw = fake_demo.kwargs
    assert kw["share"] is False, "no public Gradio tunnel by default"
    assert kw["server_name"] == "0.0.0.0", "must bind 0.0.0.0 for the Colab proxy"
    assert kw["server_port"] == app.DEFAULT_PORT == 7860
    assert kw["inline"] is False
    assert kw["quiet"] is True
    assert kw["prevent_thread_lock"] is True


def test_launch_blocking_flips_prevent_thread_lock(ctx, fake_demo):
    app.launch(ctx, blocking=True)
    assert fake_demo.kwargs["prevent_thread_lock"] is False


def test_launch_passes_proxy_url_as_root_path(ctx, fake_demo, fake_colab):
    app.launch(ctx)
    # root_path is keyword-only in Gradio 6.20.0; it must be the proxy origin so
    # /config, events, assets and queue resolve through the Colab proxy.
    assert fake_demo.kwargs["root_path"] == fake_colab.proxy


def test_launch_off_colab_passes_none_root_path(ctx, fake_demo):
    app.launch(ctx)
    assert fake_demo.kwargs["root_path"] is None


def test_launch_share_true_skips_proxy_and_root_path(ctx, fake_demo, fake_colab):
    # Explicit opt-in to a public tunnel: no Colab proxy URL is fetched and
    # root_path is left unset (Gradio prints its own share URL).
    app.launch(ctx, share=True)
    assert fake_colab.eval_js_calls == []
    assert fake_demo.kwargs["root_path"] is None
    assert fake_demo.kwargs["share"] is True


# --------------------------------------------------------------------------
# the printed primary URL is the proxy URL, not localhost
# --------------------------------------------------------------------------


def test_launch_prints_proxy_url_not_localhost(ctx, fake_demo, fake_colab, capsys):
    app.launch(ctx)
    out = capsys.readouterr().out
    assert f"TeleDrive URL: {fake_colab.proxy}" in out
    # the primary URL line must not be a misleading localhost link
    assert "localhost" not in out


def test_launch_off_colab_prints_localhost_url(ctx, fake_demo, capsys):
    app.launch(ctx)
    out = capsys.readouterr().out
    assert "TeleDrive URL: http://localhost:7860/" in out


def test_launch_proxy_failure_prints_actionable_message(ctx, fake_demo, monkeypatch, capsys):
    # On Colab but proxyPort fails: keep the server state explicit, name the
    # port, and tell the owner how to recover — do NOT print localhost.
    monkeypatch.setattr(app, "is_colab", lambda: True)
    monkeypatch.setattr(app, "colab_proxy_url", lambda port=7860: None)
    app.launch(ctx)
    out = capsys.readouterr().out
    assert "TeleDrive URL: UNAVAILABLE" in out
    assert "7860" in out
    assert "listening" in out
    assert "localhost" not in out


def test_launch_share_true_prints_no_teledrive_url_line(ctx, fake_demo, capsys):
    app.launch(ctx, share=True)
    out = capsys.readouterr().out
    assert "TeleDrive URL:" not in out  # Gradio prints its own share URL


# --------------------------------------------------------------------------
# VPN/proxy: loopback bypass is scoped to localhost only
# --------------------------------------------------------------------------


def test_merge_no_proxy_preserves_existing_and_dedupes():
    assert app._merge_no_proxy("", "localhost,127.0.0.1,::1") == "localhost,127.0.0.1,::1"
    assert (
        app._merge_no_proxy("corp.proxy:8080", "localhost,127.0.0.1,::1")
        == "corp.proxy:8080,localhost,127.0.0.1,::1"
    )
    # already-present hosts are not duplicated
    assert app._merge_no_proxy("localhost,127.0.0.1,::1", "localhost") == "localhost,127.0.0.1,::1"


def test_ensure_localhost_bypasses_proxy_merges_existing(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "corp.proxy:8080")
    monkeypatch.setenv("no_proxy", "corp.proxy:8080")
    app._ensure_localhost_bypasses_proxy()
    # the owner's external proxy entry is preserved; loopback is appended
    assert os.environ["NO_PROXY"] == "corp.proxy:8080,localhost,127.0.0.1,::1"
    assert os.environ["no_proxy"] == "corp.proxy:8080,localhost,127.0.0.1,::1"


def test_ensure_localhost_bypasses_proxy_sets_when_empty(monkeypatch):
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    app._ensure_localhost_bypasses_proxy()
    assert os.environ["NO_PROXY"] == "localhost,127.0.0.1,::1"
    assert os.environ["no_proxy"] == "localhost,127.0.0.1,::1"


def test_launch_passes_gradio_6_presentation_options(ctx, fake_demo):
    fake_demo.td_theme, fake_demo.td_css = "theme", "css"
    app.launch(ctx)
    assert fake_demo.kwargs["theme"] == "theme"
    assert fake_demo.kwargs["css"] == "css"
