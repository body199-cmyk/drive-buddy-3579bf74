import os
import tempfile
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    root = tmp_path / "teledrive_runtime"
    root.mkdir()
    monkeypatch.setenv("TELEDRIVE_ROOT", str(root))
    # Force config reload by re-importing.
    import importlib
    from teledrive import config, database
    importlib.reload(config)
    importlib.reload(database)
    from teledrive import migrations, storage_manager
    importlib.reload(migrations)
    importlib.reload(storage_manager)
    migrations.apply()
    yield root
    database.close()


@pytest.fixture()
def ctx():
    """The single ApplicationContext, torn down after every test."""
    from teledrive import app_context

    app_context.reset_context()
    context = app_context.create_context()
    yield context
    app_context.reset_context()
