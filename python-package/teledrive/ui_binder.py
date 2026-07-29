"""UIBinder — the only module allowed to attach Gradio events.

Constitution Section 4: `wire()` refuses undeclared actions (`UnknownActionError`)
and not-ready actions (`DeadControlError`), resolves the service_path against the
live context at build time, and `assert_complete()` fails the build when a ready
action was never wired.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from . import action_registry
from .errors import DeadControlError, IncompleteBindingError, UnknownActionError
from .logging_config import get_logger

_log = get_logger("teledrive.binder")

_EVENTS = ("click", "change", "submit", "select", "input")


@dataclass
class WireRecord:
    action_id: str
    handler_name: str
    service_path: str
    event: str
    component: str


class UIBinder:
    def __init__(self, ctx, handlers) -> None:
        self.ctx = ctx
        self.handlers = handlers
        self.wired: dict[str, WireRecord] = {}

    # ---- validation ----

    def validate(self, action_id: str):
        spec = action_registry.get(action_id)
        if spec is None:
            raise UnknownActionError(f"undeclared action_id: {action_id!r}")
        if not spec.ready:
            raise DeadControlError(
                f"action {action_id!r} is not implemented+tested "
                f"(implemented={spec.implemented}, tested={spec.tested})"
            )
        handler = getattr(self.handlers, spec.handler_name, None)
        if handler is None or not callable(handler):
            raise DeadControlError(f"missing handler {spec.handler_name!r} for {action_id!r}")
        if getattr(handler, "action_id", None) != action_id:
            raise DeadControlError(
                f"handler {spec.handler_name!r} is not decorated for {action_id!r}"
            )
        # Raises ServicePathError when the path does not resolve on the live context.
        self.ctx.resolve(spec.service_path)
        return spec, handler

    # ---- wiring ----

    def wire(
        self,
        component: Any,
        action_id: str,
        inputs: Sequence[Any] | None = None,
        outputs: Sequence[Any] | None = None,
        event: str = "click",
    ) -> Callable[..., Any]:
        spec, handler = self.validate(action_id)
        if event not in _EVENTS:
            raise UnknownActionError(f"unsupported event {event!r}")
        emitter = getattr(component, event, None)
        if emitter is None:
            raise DeadControlError(f"component has no {event!r} event for {action_id!r}")
        emitter(handler, list(inputs or []), list(outputs or []))
        self.wired[action_id] = WireRecord(
            action_id=action_id,
            handler_name=spec.handler_name,
            service_path=spec.service_path,
            event=event,
            component=type(component).__name__,
        )
        _log.info("wired action=%s event=%s service=%s", action_id, event, spec.service_path)
        return handler

    def load(self, block: Any, action_id: str, outputs: Sequence[Any] | None = None):
        """Wire a page-load refresh for a read-only action."""
        spec, handler = self.validate(action_id)
        block.load(handler, [], list(outputs or []))
        self.wired.setdefault(
            action_id,
            WireRecord(action_id, spec.handler_name, spec.service_path, "load", "Blocks"),
        )
        return handler

    # ---- completeness ----

    def missing(self) -> list[str]:
        return [s.action_id for s in action_registry.ready_specs() if s.action_id not in self.wired]

    def assert_complete(self) -> None:
        missing = self.missing()
        if missing:
            raise IncompleteBindingError("ready but unwired actions: " + ", ".join(sorted(missing)))
        _log.info("binder complete: %d actions wired", len(self.wired))

    def inventory(self) -> list[dict[str, str]]:
        return [vars(record) for record in self.wired.values()]
