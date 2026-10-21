from __future__ import annotations

import importlib
import subprocess

import pytest

from teledrive.universal_downloader import UniversalDownloadManager


def test_ensure_packages_installs_gdown_when_yt_dlp_already_exists(monkeypatch):
    available = {"yt_dlp": True, "gdown": False}
    install_calls = []

    def fake_import(module_name):
        if not available.get(module_name, False):
            raise ImportError(module_name)
        return object()

    def fake_run(args, **kwargs):
        install_calls.append(args)
        available["gdown"] = True
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.setattr(subprocess, "run", fake_run)

    UniversalDownloadManager(ctx=None)._ensure_packages()

    assert len(install_calls) == 1
    assert "gdown" in install_calls[0]
    assert "yt-dlp[default]" in install_calls[0]
    assert "--upgrade" in install_calls[0]


def test_ensure_packages_reports_failed_install(monkeypatch):
    available = {"yt_dlp": True, "gdown": False}

    def fake_import(module_name):
        if not available.get(module_name, False):
            raise ImportError(module_name)
        return object()

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(
            args, 1, stdout="", stderr="network unavailable"
        )

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="network unavailable"):
        UniversalDownloadManager(ctx=None)._ensure_packages()
