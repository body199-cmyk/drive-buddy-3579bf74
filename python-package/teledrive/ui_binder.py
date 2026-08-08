"""UIBinder — the only module allowed to attach Gradio events.

Constitution Section 4: `wire()` refuses undeclared actions (`UnknownActionError`)
and not-ready actions (`DeadControlError`), resolves the service_path against the
live context at build time, and `assert_complete()` fails the build when a ready
action was never wired.

Constitution 4A.1 rule 6 (orphan controls): every component created through
`button()` is registered. A registered component whose spec is ready but which
was never passed to `wire()` fails the build. A component whose spec is NOT
ready renders hidden + disabled with the neutral `common.unavailable` label and
is never wired — no dead button ever reaches the user.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from . import action_registry
from .errors import DeadControlError, IncompleteBindingError, UnknownActionError
from .i18n import t
from .logging_config import get_logger

_log = get_logger("teledrive.binder")

_EVENTS = ("click", "change", "submit", "select", "input")


def component_update(**props: Any) -> dict[str, Any]:
    """Return the Gradio update payload for the given component properties.

    The binder is the ONLY module coupled to Gradio's event/update API, so a
    handler asks for a *payload* instead of importing gradio itself. When
    gradio is absent (contract tests, CI) a plain mapping is returned; both
    forms are mappings, so ``payload["visible"]`` is always assertable and no
    test needs gradio installed.
    """
    try:
        import gradio as gr  # local import: gradio is optional outside Colab
    except Exception:  # pragma: no cover - Colab always has gradio
        return dict(props)
    return gr.update(**props)


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
        # action_id -> component, for every control created through button()
        self.rendered: dict[str, Any] = {}
        # action_ids rendered as hidden+disabled because the spec is not ready
        self.disabled: list[str] = []

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

    # ---- component factory ----

    def is_ready(self, action_id: str) -> bool:
        spec = action_registry.get(action_id)
        if spec is None:
            raise UnknownActionError(f"undeclared action_id: {action_id!r}")
        return spec.ready


    def button(self, gr, action_id: str, **kwargs):
        """Create a Gradio button for a declared action.

        Ready spec  -> normal, localized button (the caller must still wire it).
        Unready spec-> hidden, non-interactive `common.unavailable` placeholder
                       that is never passed to wire().
        """
        spec = action_registry.get(action_id)
        if spec is None:
            raise UnknownActionError(f"undeclared action_id: {action_id!r}")
        if spec.ready:
            kwargs.setdefault("value", t(spec.label_key))
            component = gr.Button(**kwargs)
        else:
            kwargs.pop("value", None)
            kwargs["interactive"] = False
            kwargs["visible"] = False
            component = gr.Button(value=t("common.unavailable"), **kwargs)
            self.disabled.append(action_id)
            _log.info(
                "control hidden (not ready) action=%s implemented=%s tested=%s",
                action_id, spec.implemented, spec.tested,
            )
        self.rendered[action_id] = component
        return component

    def register(self, component: Any, action_id: str) -> Any:
        """Register a non-button component (radio, dropdown, timer) for orphan checks."""
        if action_registry.get(action_id) is None:
            raise UnknownActionError(f"undeclared action_id: {action_id!r}")
        self.rendered[action_id] = component
        return component

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

    def wire_if_ready(
        self,
        component: Any,
        action_id: str,
        inputs: Sequence[Any] | None = None,
        outputs: Sequence[Any] | None = None,
        event: str = "click",
    ):
        """Wire a ready action; silently skip a declared-but-unready one.

        Unknown action ids still raise — skipping is only ever allowed for a
        control whose spec exists and honestly says it is not ready yet.
        """
        spec = action_registry.get(action_id)
        if spec is None:
            raise UnknownActionError(f"undeclared action_id: {action_id!r}")
        if not spec.ready:
            return None
        return self.wire(component, action_id, inputs, outputs, event)

    # ---- completeness ----

    def missing(self) -> list[str]:
        return [s.action_id for s in action_registry.ready_specs() if s.action_id not in self.wired]

    def orphans(self) -> list[str]:
        return [
            action_id
            for action_id in self.rendered
            if action_id not in self.wired and action_id not in self.disabled
        ]

    def assert_complete(self) -> None:
        missing = self.missing()
        if missing:
            raise IncompleteBindingError("ready but unwired actions: " + ", ".join(sorted(missing)))
        orphans = self.orphans()
        if orphans:
            raise IncompleteBindingError(
                "rendered but never wired controls: " + ", ".join(sorted(orphans))
            )
        _log.info(
            "binder complete: %d actions wired, %d controls hidden as not ready",
            len(self.wired), len(self.disabled),
        )

    def inventory(self) -> list[dict[str, str]]:
        return [vars(record) for record in self.wired.values()]
