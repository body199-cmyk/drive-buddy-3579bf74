"""The single ApplicationContext (Constitution Section 2).

Created exactly once per Colab session. Owns every service and the one
AsyncRuntime. `resolve("queue_manager.start_selected")` returns a bound method
and RAISES on a typo, a None service, or a non-callable target.

Phase 1 scope: the context exists, owns the runtime and the services that exist
today. Services added in later phases (action registry, ui binder, folders,
quota gate, ...) attach here, not to new module globals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from . import database as db
from .async_runtime import AsyncRuntime
from .auth_manager import AuthManager
from .config import CONFIG, RuntimeConfig
from .logging_config import get_logger
from .progress_tracker import ProgressTracker
from .drive_auth import DriveAuth
from .drive_folders import DriveFolders
from .flow import FlowService
from .handlers import Handlers
from .progress_tracker import ProgressTracker  # noqa: F401 (re-export order)
from .queue_manager import QueueManager
from .services import (
    CheckpointService,
    ColabExportService,
    DriveQuotaService,
    LogService,
    PreferencesService,
    ScannerService,
    SelectionService,
    SettingsService,
    StatsService,
)
from .package_service import PackageService
from .telegram_auth import TelegramAuth
from .ui_binder import UIBinder

_log = get_logger("teledrive.context")


from .errors import ServicePathError  # single canonical class (was a duplicate here)



@dataclass
class UIState:
    """Runtime UI state. No fake values are ever seeded here."""

    language: str = CONFIG.language
    active_tab: str = "dashboard"
    last_message: str = ""
    telegram_status: str = "DISCONNECTED"
    drive_status: str = "DISCONNECTED"
    extra: dict = field(default_factory=dict)


class ApplicationContext:
    """One context per process. Do not instantiate twice; use create_context()."""

    def __init__(self, config: Optional[RuntimeConfig] = None) -> None:
        self.config: RuntimeConfig = config or CONFIG
        self.aio: AsyncRuntime = AsyncRuntime()
        self.db = db
        self.auth: AuthManager = AuthManager()
        self.queue_manager: QueueManager = QueueManager(self)
        self.progress: ProgressTracker = ProgressTracker()

        self.ui_state: UIState = UIState(language=self.config.language)

        # Auth owners (Phases 3-4): the ONLY holders of a Telegram client and
        # a Drive service object.
        self.telegram_auth = TelegramAuth(self)
        self.drive_auth = DriveAuth(self)

        # Domain services (Phases 5-7).
        self.drive_folders = DriveFolders(self)
        self.drive_quota = DriveQuotaService(self)
        self.selection = SelectionService(self)
        self.scanner = ScannerService(self)
        self.stats = StatsService(self)
        self.log_service = LogService(self)
        self.settings = SettingsService(self)
        self.preferences = PreferencesService(self)
        self.checkpoints = CheckpointService(self)
        self.colab_export = ColabExportService(self)
        self.package_service = PackageService(self)

        # Derived UI flow state (M20-T03). Read-only over the live context.
        # Must exist BEFORE Handlers/UIBinder so ctx.resolve("flow.state")
        # succeeds while the binder validates every spec at build time.
        self.flow = FlowService(self)

        # Binding layer (Phase 2).
        self.handlers = Handlers(self)
        self.binder = UIBinder(self, self.handlers)

        self.queue_manager.bind_context(self)
        self.ui: Any = None          # Gradio launch handle (set by app.launch)
        self.transfer_manager: Any = None
        self.drive_client: Any = None
        self.bootstrap_info: dict = {}

    # ---- owned singletons (one per context, Phase C) ----

    def ensure_drive_client(self):
        """The ONE Drive client for this context."""
        if self.drive_client is None:
            from .drive_client import DriveService

            self.drive_client = DriveService.from_auth(self.drive_auth)
        return self.drive_client

    def ensure_transfer_manager(self, drive_folder_id: Optional[str] = None):
        """The ONE TransferManager for this context; reused on every Start."""
        from .transfer_manager import TransferManager

        drive = self.ensure_drive_client()
        if self.transfer_manager is None:
            self.transfer_manager = TransferManager(
                self.telegram_auth.client if self.telegram_auth else None,
                drive,
                drive_folder_id or "",
                queue=self.queue_manager,
            )
        else:
            self.transfer_manager.drive = drive
            if self.telegram_auth is not None:
                self.transfer_manager.telegram = self.telegram_auth.client
            if drive_folder_id:
                self.transfer_manager.drive_folder_id = drive_folder_id
        return self.transfer_manager

    # ---- lifecycle ----

    def start(self) -> "ApplicationContext":
        self.aio.start()
        return self


    def shutdown(self) -> None:
        if self.ui is not None:
            try:
                self.ui.close()
            except Exception:  # pragma: no cover - defensive
                _log.warning("ui close failed during shutdown")
            self.ui = None
        self.aio.stop()
        try:
            self.db.close()
        except Exception:  # pragma: no cover - defensive
            _log.warning("database close failed during shutdown")

    # ---- strict resolution ----

    def resolve(self, service_path: str) -> Callable[..., Any]:
        if not service_path or "." not in service_path:
            raise ServicePathError(f"invalid service_path: {service_path!r}")
        service_name, _, method_name = service_path.partition(".")
        if not hasattr(self, service_name):
            raise ServicePathError(f"unknown service: {service_name!r}")
        service = getattr(self, service_name)
        if service is None:
            raise ServicePathError(f"service is None: {service_name!r}")
        if not hasattr(service, method_name):
            raise ServicePathError(f"unknown method: {service_path!r}")
        target = getattr(service, method_name)
        if not callable(target):
            raise ServicePathError(f"not callable: {service_path!r}")
        return target


_CONTEXT: Optional[ApplicationContext] = None


def create_context(config: Optional[RuntimeConfig] = None) -> ApplicationContext:
    """Create the process-wide context, starting the single async runtime."""
    global _CONTEXT
    if _CONTEXT is not None and _CONTEXT.aio.is_running:
        return _CONTEXT
    _CONTEXT = ApplicationContext(config).start()
    _log.info("application context created")
    return _CONTEXT


def get_context() -> ApplicationContext:
    if _CONTEXT is None:
        raise RuntimeError("ApplicationContext not created; run bootstrap first")
    return _CONTEXT


def has_context() -> bool:
    return _CONTEXT is not None


def reset_context() -> None:
    """Tear the context down. Tests and Colab restarts only."""
    global _CONTEXT
    if _CONTEXT is not None:
        _CONTEXT.shutdown()
    _CONTEXT = None
