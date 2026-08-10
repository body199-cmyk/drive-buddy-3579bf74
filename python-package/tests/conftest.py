"""Pytest fixtures: every test gets a fresh tmp_path TELEDRIVE_ROOT."""
from __future__ import annotations

import importlib
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    root = tmp_path / "teledrive_runtime"
    root.mkdir()
    monkeypatch.setenv("TELEDRIVE_ROOT", str(root))

    # Reload config first so DB_PATH / LOG_PATH / CHECKPOINTS_DIR etc. all
    # point inside tmp_path, then reload database (which opens the sqlite
    # file at module import time) and re-apply migrations.  Path-constants
    # in other modules (checkpoint_manager, logging_config) are rebound
    # via monkeypatch-style setattr so the module identity of classes like
    # InvalidCheckpointError is preserved across tests.
    from teledrive import config, database
    importlib.reload(config)
    importlib.reload(database)

    from teledrive import checkpoint_manager, logging_config
    for _m in (checkpoint_manager, logging_config):
        for attr in ("CHECKPOINTS_DIR", "LOGS_DIR", "LOG_PATH", "DATA_DIR",
                     "TEMP_DIR", "SESSION_DIR", "QUARANTINE_DIR",
                     "TELEGRAM_SESSION"):
            if hasattr(config, attr) and hasattr(_m, attr):
                setattr(_m, attr, getattr(config, attr))

    from teledrive import migrations
    importlib.reload(migrations)
    migrations.apply()
    yield root
    database.close()


@pytest.fixture()
def ctx():
    """The single ApplicationContext, torn down after every test.

    ``importlib.reload(config)`` above creates a fresh RuntimeConfig, but
    ``app_context`` still holds a reference to the PREVIOUS RuntimeConfig
    instance, so fields mutated on ``ctx.config`` (e.g. drive_folder_id)
    would leak into later tests. Reset the shared instance's mutable fields
    so every test starts from the default state.
    """
    from teledrive import app_context

    app_context.reset_context()
    context = app_context.create_context()
    context.config.drive_folder_id = None
    context.config.manual_concurrency = None
    yield context
    app_context.reset_context()
