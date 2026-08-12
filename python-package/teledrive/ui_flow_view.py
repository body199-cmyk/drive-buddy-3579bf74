"""FlowState -> Gradio updates (M20-T03).

This is the UI layer, so it is allowed to import gradio. It is the only place
besides ui.py that does. Twelve outputs, in the exact order declared by
``flow_outputs`` in ui.py; ERROR_ARITY["flow.sync"] must stay in sync with it.
"""
from __future__ import annotations

from .flow import STEP_ORDER, FlowState
from .i18n import t
from .ui_binder import component_update
from .utils import human_bytes

STEP_TITLE_KEYS = (
    "flow.step1.title",
    "flow.step2.title",
    "flow.step3.title",
    "flow.step4.title",
    "flow.step5.title",
)


def _current_index(state: FlowState) -> int:
    try:
        return STEP_ORDER.index(state.step) + 1
    except ValueError:  # pragma: no cover - defensive
        return 1


def _stepper(state: FlowState) -> str:
    current = _current_index(state)
    parts = []
    for index, key in enumerate(STEP_TITLE_KEYS, start=1):
        name = t(key)
        if index < current:
            parts.append(f"✅ {index}. {name}")
        elif index == current:
            parts.append(f"🔵 **{index}. {name}**")
        else:
            parts.append(f"⚪ {index}. {name}")
    return "<div class='td-stepper'>" + " · ".join(parts) + "</div>"


def _chips(state: FlowState) -> str:
    def chip(label: str, ok: bool, extra: str = "") -> str:
        mark = "🟢" if ok else "⚪"
        return f"{mark} {label}{extra}"

    folder = f" · `{state.folder_id}`" if state.folder_id else ""
    return " &nbsp; ".join(
        (
            chip(t("nav.telegram"), state.telegram_ready),
            chip(t("nav.drive"), state.drive_ready),
            chip(t("sel.target_folder"), state.folder_ready, folder),
            chip(t("dash.queue_status"), state.running, f" · {state.active}/{state.queued}"),
        )
    )


def _summary(state: FlowState) -> str:
    if state.selected == 0:
        return t("sel.hint")
    return (
        f"**{t('sel.count')}:** {state.selected} / {state.visible} &nbsp;·&nbsp; "
        f"**{t('sel.total_size')}:** {human_bytes(state.selected_bytes)} &nbsp;·&nbsp; "
        f"**{t('sel.required_space')}:** {human_bytes(state.selected_bytes)} &nbsp;·&nbsp; "
        f"**{t('sel.target_folder')}:** {state.folder_id or t('msg.no_folder_selected')}"
    )


def _hint(state: FlowState) -> str:
    if state.queued == 0 and state.active == 0:
        return t("queue.empty")
    return (
        f"**{t('dash.remaining')}:** {state.queued} &nbsp;·&nbsp; "
        f"**{t('state.Downloading')}/{t('state.Uploading')}:** {state.active} &nbsp;·&nbsp; "
        f"**{t('dash.done')}:** {state.done} &nbsp;·&nbsp; "
        f"**{t('dash.failed')}:** {state.failed}"
    )


def visibility(state: FlowState) -> dict[str, bool]:
    """Which steps the LIVE context says the user has really reached.

    Shared by ``render`` (post-action updates) and by ui.py's first paint, so
    the server-rendered page and every later sync agree by construction.
    """
    connected = state.telegram_ready and state.drive_ready and state.folder_ready
    show_2 = connected
    show_3 = connected and state.analyzed > 0
    show_4 = show_3 and (state.selected > 0 or state.queued > 0 or state.active > 0)
    show_5 = state.queued > 0 or state.active > 0 or state.done > 0 or state.failed > 0
    return {
        "step1": True,
        "step2": show_2,
        "step3": show_3,
        "step4": show_4,
        "step5": show_5,
        "analyze": show_2,
        "enqueue": state.selected > 0,
        "start": state.queued > 0 and state.folder_ready and not state.running,
    }


def texts(state: FlowState) -> dict[str, str]:
    """The three derived text blocks, reused by the first paint."""
    return {
        "stepper": _stepper(state),
        "chips": _chips(state),
        "summary": _summary(state),
        "hint": _hint(state),
    }


def render(state: FlowState):
    """Twelve updates, in ui.py's ``flow_outputs`` order."""
    show = visibility(state)
    text = texts(state)

    return (
        component_update(value=text["stepper"]),      # 1  flow_banner
        component_update(value=text["chips"]),        # 2  chips_md
        component_update(visible=show["step1"]),      # 3  step1_group
        component_update(visible=show["step2"]),      # 4  step2_group
        component_update(visible=show["step3"]),      # 5  step3_group
        component_update(visible=show["step4"]),      # 6  step4_group
        component_update(visible=show["step5"]),      # 7  step5_group
        component_update(value=text["summary"]),      # 8  selection_summary
        component_update(value=text["hint"]),         # 9  queue_hint
        component_update(interactive=show["analyze"]),   # 10 analyze_btn
        component_update(interactive=show["enqueue"]),   # 11 enqueue_btn
        component_update(interactive=show["start"]),     # 12 start_btn
    )
