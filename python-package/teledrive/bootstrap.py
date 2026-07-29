"""One-shot bootstrap: folders, DB, logging, then the single ApplicationContext."""
from __future__ import annotations

from . import migrations
from .app_context import ApplicationContext, create_context
from .config import all_dirs, TEMP_DIR
from .logging_config import setup as setup_logging
from .utils import safe_disk_free


def run() -> ApplicationContext:
    """Prepare the local runtime and return the one shared context."""
    for d in all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    log = setup_logging()
    version = migrations.apply()
    free = safe_disk_free(TEMP_DIR)
    ctx = create_context()
    ctx.bootstrap_info = {
        "schema_version": version,
        "dirs": [str(d) for d in all_dirs()],
        "free_bytes": free,
    }
    log.info(
        "bootstrap ok schema=%s free=%s loop=%s", version, free, ctx.aio.is_running
    )
    return ctx
