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

_EVENTS = ("click", "change", "submit", "select", "input", "release")


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
        # Multiple controls may map to the same action (e.g. a top-bar zip
        # button and a prominent export-section button), so these are lists.
        self.wired: dict[str, list[WireRecord]] = {}
        # action_id -> list[component], one entry per button/register call
        self.rendered: dict[str, list[Any]] = {}
        # action_ids rendered as hidden+disabled because the spec is not ready
        self.disabled: list[str] = []
        # Flow sync (M20-T03): one read-only action chained after every other
        # wired action, so the visible step always matches the live context.
        self._sync_action_id: str = ""
        self._sync_handler = None
        self._sync_outputs: list = []
        self._page_loads: list[tuple[str, Callable[..., Any], list]] = []

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
        Unready with blocked_reason_key -> VISIBLE but disabled, localized label
                                            explaining why (no silent hiding).
        Unready without a key -> legacy hidden placeholder (defensive; forbidden
                                 by assert_complete).
        """
        spec = action_registry.get(action_id)
        if spec is None:
            raise UnknownActionError(f"undeclared action_id: {action_id!r}")
        if spec.ready:
            kwargs.setdefault("value", t(spec.label_key))
            component = gr.Button(**kwargs)
        elif spec.blocked_reason_key:
            kwargs.pop("value", None)
            kwargs["interactive"] = False
            kwargs["visible"] = True
            label = f"{t(spec.label_key)} — {t(spec.blocked_reason_key)}"
            component = gr.Button(value=label, **kwargs)
            self.disabled.append(action_id)
            _log.info(
                "control visible-disabled action=%s reason=%s",
                action_id, spec.blocked_reason_key,
            )
        else:
            kwargs.pop("value", None)
            kwargs["interactive"] = False
            kwargs["visible"] = False
            component = gr.Button(value=t("common.unavailable"), **kwargs)
            self.disabled.append(action_id)
            _log.info(
                "control hidden (not ready, no reason key) action=%s", action_id,
            )
        self.rendered.setdefault(action_id, []).append(component)
        return component

    def register(self, component: Any, action_id: str) -> Any:
        """Register a non-button component (radio, dropdown, timer) for orphan checks."""
        if action_registry.get(action_id) is None:
            raise UnknownActionError(f"undeclared action_id: {action_id!r}")
        self.rendered.setdefault(action_id, []).append(component)
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
        dependency = emitter(handler, list(inputs or []), list(outputs or []))
        if (
            self._sync_handler is not None
            and action_id != self._sync_action_id
            and hasattr(dependency, "then")
        ):
            # Fake components in the contract tests return None from click(),
            # and hasattr(None, "then") is False, so no existing test changes.
            dependency.then(self._sync_handler, [], list(self._sync_outputs))
        rec = WireRecord(
            action_id=action_id,
            handler_name=spec.handler_name,
            service_path=spec.service_path,
            event=event,
            component=type(component).__name__,
        )
        self.wired.setdefault(action_id, []).append(rec)
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

    # ---- flow sync (M20-T03) ----

    def register_sync(self, action_id: str, outputs: Sequence[Any]):
        """Declare the read-only action re-run after every other wired action.

        Must be called before the other wire() calls; anything wired earlier is
        not chained.
        """
        spec, handler = self.validate(action_id)
        self._sync_action_id = action_id
        self._sync_handler = handler
        self._sync_outputs = list(outputs)
        _log.info("sync action registered: %s -> %d outputs",
                  action_id, len(self._sync_outputs))
        return handler

    def load(self, action_id: str, outputs: Sequence[Any] | None = None) -> Callable[..., Any]:
        """Register a ready action to run once on Blocks.load (page open).

        Gradio has no binder.load in older trees; this is the smallest hook that
        keeps assert_complete() honest and lets session.autorestore paint the
        live Telegram chip after a Drive restore.
        """
        spec, handler = self.validate(action_id)
        # M24-T03: the language re-render calls this again for the same action;
        # replace the entry instead of stacking duplicate page-load bindings.
        for index, (registered_id, _handler, _outputs) in enumerate(self._page_loads):
            if registered_id == action_id:
                self._page_loads[index] = (action_id, handler, list(outputs or []))
                return handler
        self._page_loads.append((action_id, handler, list(outputs or [])))
        rec = WireRecord(
            action_id=action_id,
            handler_name=spec.handler_name,
            service_path=spec.service_path,
            event="load",
            component="Blocks",
        )
        self.wired.setdefault(action_id, []).append(rec)
        _log.info("page-load action registered: %s", action_id)
        return handler

    def load_sync(self, block: Any) -> None:
        """Run the sync action once on page load so step 1 is never guessed."""
        loader = getattr(block, "load", None)
        if loader is None:  # pragma: no cover - defensive
            return
        if self._sync_handler is not None:
            loader(self._sync_handler, [], list(self._sync_outputs))
        for _action_id, handler, outputs in getattr(self, "_page_loads", []):
            loader(handler, [], outputs)

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
        action_registry.assert_complete()
        missing = self.missing()
        if missing:
            raise IncompleteBindingError("ready but unwired actions: " + ", ".join(sorted(missing)))
        orphans = self.orphans()
        if orphans:
            raise IncompleteBindingError(
                "rendered but never wired controls: " + ", ".join(sorted(orphans))
            )
        wired_count = sum(len(v) for v in self.wired.values())
        _log.info(
            "binder complete: %d action kinds wired (%d controls), %d visible-disabled/hidden",
            len(self.wired), wired_count, len(self.disabled),
        )

    def inventory(self) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for records in self.wired.values():
            for rec in records:
                out.append(vars(rec))
        return out
