"""Gradio layout only — TeleDrive graphite shell (M15-T04).

This module declares components and asks the UIBinder to attach them. It contains
no business logic, no lambdas, no ad-hoc event handlers and no hardcoded
user-facing strings — every label comes from i18n and every behaviour comes from
a named handler declared in ACTION_SPECS.

Shell contract (M15-T04):

* Arabic RTL is the default; the language toggle re-renders the shell in
  English LTR through ONE ``gr.State`` + ONE ``gr.render`` pass. Runtime state
  (Telegram login, queue, transfers, selection) lives on the ApplicationContext,
  not in the layout, so a re-render never destroys it — every component is
  *seeded* from live state via ``handlers.shell_seed`` and a re-render can
  never reset the OTP/2FA panels to a visibility that contradicts the state
  machine, nor fabricate rows, logs, quotas or statuses.
* The graphite dark theme + lime accent is handed to ``gr.Blocks`` as theme/css.
  Gradio 6 moved those to ``launch()``, which is owned by ``app.launch`` (not
  this module); per the pinned 6.20.0 launch path the constructor kwargs remain
  the only working injection point from layout code and are used deliberately.
* Every actionable control is created through ``binder.button(...)`` or an
  ``is_ready`` gate: a control whose spec is not implemented+tested renders
  hidden and disabled (or a read-only note naming it unavailable) instead of
  reaching the browser dead. Navigation is native ``gr.Tabs`` layout — no view
  switching buttons exist, so nothing "changes the view only".
"""
from __future__ import annotations

from typing import Any

from .app_context import ApplicationContext, get_context
from .config import HARD_CONCURRENCY_CAP, SUPPORTED_LANGUAGES
from .handlers import shell_seed
from .i18n import set_language, t

try:
    import gradio as gr
except Exception:  # pragma: no cover - Colab always has gradio
    gr = None  # type: ignore

TABLE_HEADERS = ("col.id", "col.file", "col.type", "col.size",
                 "col.state", "col.progress", "col.attempts")
MEDIA_TYPES = ("photo", "video", "audio", "voice", "document", "animation", "sticker")
SCOPE_CHOICES = ("auto", "message", "chat")

# Graphite dark surfaces + lime accent + semantic states. Visual tokens only —
# no user-facing copy here, so this stays outside the locale contract.
GRAPHITE_CSS = """
:root, .gradio-container, .dark {
  --td-bg: #111418;
  --td-surface: #191d23;
  --td-elevated: #20252d;
  --td-border: #2e3540;
  --td-text: #e8ebf0;
  --td-muted: #97a1b0;
  --td-lime: #a3e635;
  --td-lime-dim: rgba(163, 230, 53, 0.14);
  --td-success: #4ade80;
  --td-warning: #fbbf24;
  --td-error: #f87171;
  --td-info: #60a5fa;
  --td-radius: 14px;
}
body, .gradio-container {
  background: var(--td-bg) !important;
  color: var(--td-text) !important;
}
.gradio-container {
  font-family: "Segoe UI", "Noto Naskh Arabic", "Noto Sans Arabic", Tahoma, Arial, sans-serif;
  --body-background-fill: var(--td-bg);
  --block-background-fill: var(--td-surface);
  --block-border-color: var(--td-border);
  --body-text-color: var(--td-text);
  --block-label-text-color: var(--td-muted);
  --block-title-text-color: var(--td-muted);
  --input-border-color: var(--td-border);
  --border-color-primary: var(--td-border);
  --color-accent: var(--td-lime);
}
.td-root.td-rtl { direction: rtl; text-align: right; }
.td-root.td-ltr { direction: ltr; text-align: left; }

/* ---- top bar ---- */
.td-topbar {
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-radius: var(--td-radius);
  margin-bottom: 14px;
}
.td-brand { font-size: 17px; letter-spacing: 0.3px; color: var(--td-text); }
.td-brand strong { color: var(--td-text); }
.td-brand code {
  color: var(--td-lime);
  background: var(--td-lime-dim);
  border-radius: 6px;
  padding: 1px 6px;
  font-size: 12px;
}
.td-chip { min-width: 150px; }
.td-chip input {
  background: var(--td-elevated);
  border: 1px solid var(--td-border) !important;
  border-radius: 999px;
  color: var(--td-text) !important;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  padding: 4px 12px;
}
@media (max-width: 720px) { .td-topbar { flex-wrap: wrap; } }

/* ---- side navigation rail (native Tabs, styled) ---- */
.td-tabs { display: flex; gap: 16px; align-items: stretch; }
.td-tabs > :first-child {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 0 0 236px;
  padding: 10px;
  align-self: flex-start;
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-radius: var(--td-radius);
}
.td-tabs > :first-child button {
  width: 100%;
  justify-content: flex-start;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--td-muted);
  font-weight: 600;
  box-shadow: none;
}
.td-tabs > :first-child button:hover { color: var(--td-text); background: var(--td-elevated); }
.td-tabs > :first-child button.selected,
.td-tabs > :first-child button.active,
.td-tabs > :first-child button[aria-selected="true"] {
  color: var(--td-lime);
  background: var(--td-lime-dim);
  border-color: var(--td-lime);
}
.td-tabs .tabitem { flex: 1 1 auto; min-width: 0; }
@media (max-width: 900px) {
  .td-tabs { flex-direction: column !important; }
  .td-tabs > :first-child { flex: 1 1 auto; flex-direction: row; flex-wrap: wrap; position: static; }
  .td-tabs > :first-child button { width: auto; flex: 1 1 40%; }
}

/* ---- cards and surfaces ---- */
.td-card {
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-radius: var(--td-radius);
  padding: 14px;
  gap: 10px;
}
.td-section-title { color: var(--td-muted); font-size: 14px; font-weight: 700; }

/* ---- buttons ---- */
.gradio-container button { border-radius: 10px !important; }
.gradio-container button.primary {
  background: var(--td-lime) !important;
  border-color: var(--td-lime) !important;
  color: #14170d !important;
  font-weight: 700;
}
.gradio-container button.secondary {
  background: var(--td-elevated) !important;
  border: 1px solid var(--td-border) !important;
  color: var(--td-text) !important;
}
.gradio-container button.stop {
  background: rgba(248, 113, 113, 0.12) !important;
  border-color: var(--td-error) !important;
  color: var(--td-error) !important;
  font-weight: 700;
}

/* ---- semantic panels ---- */
.td-panel-otp {
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-inline-start: 4px solid var(--td-info);
  border-radius: var(--td-radius);
  padding: 10px 14px;
}
.td-panel-2fa {
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-inline-start: 4px solid var(--td-warning);
  border-radius: var(--td-radius);
  padding: 10px 14px;
}

/* ---- tables ---- */
.td-table { border: 1px solid var(--td-border); border-radius: var(--td-radius); overflow: hidden; }
.td-table table { background: var(--td-surface); }
.td-table th { background: var(--td-elevated) !important; color: var(--td-muted) !important; font-weight: 700; }
.td-table td { color: var(--td-text); border-color: var(--td-border) !important; }
.td-table tr:hover td { background: var(--td-elevated); }

/* ---- logs ---- */
.td-logs textarea {
  font-family: "Cascadia Mono", "Fira Code", Consolas, monospace;
  font-size: 12px;
  background: #0d1013 !important;
  color: #c9d1d9 !important;
  border: 1px solid var(--td-border) !important;
  border-radius: var(--td-radius);
  direction: ltr;
  text-align: left;
}
"""


def _headers() -> list[str]:
    return [t(key) for key in TABLE_HEADERS]


def _graphite_theme() -> Any:
    """Soft base recolored to graphite + lime; the CSS above finishes the job."""
    return gr.themes.Soft(primary_hue="lime", neutral_hue="gray")


def build(ctx: ApplicationContext | None = None) -> Any:
    """Build the Gradio shell; bindings are validated on every render pass."""
    if ctx is None:
        ctx = get_context()
    if gr is None:
        raise RuntimeError("gradio is not installed")
    binder = ctx.binder
    language = ctx.ui_state.language
    if language not in SUPPORTED_LANGUAGES:
        language = ctx.config.language if ctx.config.language in SUPPORTED_LANGUAGES else "ar"
    set_language(language)

    with gr.Blocks(title=t("app.title"), theme=_graphite_theme(), css=GRAPHITE_CSS) as demo:
        # The ONE language switch source: written only by settings.toggle_language.
        lang_state = gr.State(language)

        @gr.render(inputs=[lang_state])
        def _language_root(lang: str) -> None:
            _render_shell(ctx, binder, lang_state, lang)

    return demo


def _render_shell(ctx: ApplicationContext, binder, lang_state: Any, lang: str) -> dict[str, Any]:
    """Draw the whole shell for one language pass and validate the bindings.

    Seeds every component from LIVE context state (``shell_seed``) so this pass
    is idempotent against the runtime: re-running it for a language switch
    keeps the login panels, tables, logs and statuses exactly where the state
    machine and the database say they are. Returns component references used by
    the contract tests; Gradio ignores the return value of a render function.
    """
    if lang not in SUPPORTED_LANGUAGES:
        lang = ctx.config.language if ctx.config.language in SUPPORTED_LANGUAGES else "ar"
    set_language(lang)
    direction = "td-rtl" if lang == "ar" else "td-ltr"
    seed = shell_seed(ctx)
    refs: dict[str, Any] = {"direction": direction}

    with gr.Column(elem_classes=["td-root", direction]) as root:
        # ---------------- top bar ----------------
        with gr.Row(elem_classes=["td-topbar"]):
            gr.Markdown(
                f"**TeleDrive** `v{ctx.config.version}`", elem_classes=["td-brand"]
            )
            telegram_chip = gr.Textbox(
                value=seed["telegram_label"], show_label=False, interactive=False,
                max_lines=1, elem_classes=["td-chip"],
            )
            drive_chip = gr.Textbox(
                value=seed["drive_label"], show_label=False, interactive=False,
                max_lines=1, elem_classes=["td-chip"],
            )
            language_btn = binder.button(gr, "settings.toggle_language", variant="secondary")
            zip_btn = binder.button(gr, "export.build_zip", variant="secondary")

        with gr.Tabs(elem_classes=["td-tabs"]):
            # ---------------- Dashboard ----------------
            with gr.Tab(t("nav.dashboard")):
                with gr.Row():
                    telegram_card = gr.Textbox(
                        value=seed["telegram_detail"], label=t("dash.telegram_status"),
                        interactive=False, elem_classes=["td-card"],
                    )
                    drive_card = gr.Textbox(
                        value=seed["drive_detail"], label=t("dash.drive_status"),
                        interactive=False, elem_classes=["td-card"],
                    )
                    queue_card = gr.Textbox(
                        value=seed["queue_header"], label=t("dash.queue_status"),
                        interactive=False, elem_classes=["td-card"],
                    )
                dashboard_btn = binder.button(gr, "dashboard.refresh", variant="secondary")
                dashboard_json = gr.JSON(label=t("dash.stats"), value=seed["dashboard"])

            # ---------------- Transfers (main workspace) ----------------
            with gr.Tab(t("nav.queue")):
                gr.Markdown(f"### {t('transfer.controls')}", elem_classes=["td-section-title"])
                with gr.Row():
                    start_btn = binder.button(gr, "queue.start_selected", variant="primary", scale=2)
                    pause_btn = binder.button(gr, "queue.pause")
                    resume_btn = binder.button(gr, "queue.resume")
                    stop_btn = binder.button(gr, "queue.stop", variant="stop")
                with gr.Row():
                    retry_failed_btn = binder.button(gr, "queue.retry_failed")
                    clear_completed_btn = binder.button(gr, "queue.clear_completed")
                    refresh_queue_btn = binder.button(gr, "queue.refresh", variant="secondary")
                queue_status = gr.Textbox(
                    value=seed["queue_header"], label=t("dash.queue_status"), interactive=False
                )
                queue_table = gr.Dataframe(
                    headers=_headers(), value=seed["queue_rows"] or None,
                    interactive=False, wrap=True, elem_classes=["td-table"],
                )
                with gr.Group(elem_classes=["td-card"]):
                    gr.Markdown(f"### {t('transfer.item')}", elem_classes=["td-section-title"])
                    with gr.Row():
                        item_id = gr.Textbox(label=t("col.id"), scale=2)
                        pause_item_btn = binder.button(gr, "queue.pause_item")
                        resume_item_btn = binder.button(gr, "queue.resume_item")
                        stop_item_btn = binder.button(gr, "queue.stop_item", variant="stop")
                        retry_item_btn = binder.button(gr, "queue.retry_item")

            # ---------------- Analyze ----------------
            with gr.Tab(t("nav.link")):
                with gr.Group(elem_classes=["td-card"]):
                    gr.Markdown(t("analyze.instructions"), elem_classes=["td-section-title"])
                    with gr.Row():
                        link = gr.Textbox(label=t("form.link"), scale=4)
                        analyze_btn = binder.button(gr, "analyze.run", variant="primary", scale=1)
                    with gr.Row():
                        mode = gr.Radio(
                            choices=["message", "range", "latest", "chat"],
                            value="chat",
                            label=t("form.scan_mode"),
                            scale=2,
                        )
                        media_types = gr.CheckboxGroup(
                            choices=["all", "video", "audio", "document", "photo", "voice", "animation", "sticker"],
                            value=["all"],
                            label=t("form.media_types"),
                            scale=3,
                        )
                    with gr.Row():
                        message_id = gr.Number(label=t("form.message_id"), precision=0, minimum=1)
                        start_id = gr.Number(label=t("form.start_message"), precision=0, minimum=1)
                        end_id = gr.Number(label=t("form.end_message"), precision=0, minimum=1)
                        limit = gr.Number(label=t("form.message_limit"), value=1000, precision=0, minimum=1, maximum=1000)
                    analyze_message = gr.Textbox(label=t("btn.analyze"), interactive=False)
                    candidates_table = gr.Dataframe(
                        headers=_headers(),
                        value=seed["analyze_rows"] or None,
                        interactive=False,
                        wrap=True,
                        elem_classes=["td-table"],
                    )
                    with gr.Accordion(t("form.filters"), open=False):
                        filter_media_types = gr.CheckboxGroup(
                            choices=["all", "video", "audio", "document", "photo", "voice", "animation", "sticker"],
                            value=["all"],
                            label=t("form.media_types"),
                        )
                        extensions = gr.Textbox(label=t("form.extensions"))
                        with gr.Row():
                            min_size = gr.Number(label=t("form.min_size_mb"), value=None)
                            max_size = gr.Number(label=t("form.max_size_mb"), value=None)
                        with gr.Row():
                            date_from = gr.Textbox(label=t("form.date_from"))
                            date_to = gr.Textbox(label=t("form.date_to"))
                        include = gr.Textbox(label=t("form.include"))
                        exclude = gr.Textbox(label=t("form.exclude"))
                        filters_btn = binder.button(gr, "analyze.apply_filters", variant="secondary")
                    with gr.Row():
                        select_all_btn = binder.button(gr, "analyze.select_all")
                        clear_selection_btn = binder.button(gr, "analyze.clear_selection")
                        enqueue_btn = binder.button(gr, "analyze.enqueue_selected", variant="primary")

            # ---------------- Connection Center ----------------
            with gr.Tab(t("nav.connection")):
                with gr.Row():
                    with gr.Column(elem_classes=["td-card"]):
                        gr.Markdown(f"### {t('nav.telegram')}", elem_classes=["td-section-title"])
                        with gr.Row():
                            api_id = gr.Textbox(label=t("form.api_id"), type="password")
                            api_hash = gr.Textbox(label=t("form.api_hash"), type="password")
                        credentials_btn = binder.button(gr, "telegram.set_credentials", variant="primary")
                        phone = gr.Textbox(label=t("form.phone"))
                        with gr.Row():
                            send_code_btn = binder.button(gr, "telegram.send_code")
                            resend_code_btn = binder.button(gr, "telegram.resend_code")
                        with gr.Column(
                            visible=seed["otp_visible"], elem_classes=["td-panel-otp"]
                        ) as code_panel:
                            code = gr.Textbox(label=t("form.code"))
                            verify_btn = binder.button(gr, "telegram.verify_code", variant="primary")
                        with gr.Column(
                            visible=seed["password_visible"], elem_classes=["td-panel-2fa"]
                        ) as password_panel:
                            password = gr.Textbox(label=t("form.password"), type="password")
                            verify_password_btn = binder.button(gr, "telegram.verify_password", variant="primary")
                        with gr.Row():
                            telegram_logout_btn = binder.button(gr, "telegram.logout", variant="stop")
                            telegram_status_btn = binder.button(gr, "telegram.status", variant="secondary")
                        telegram_detail = gr.Textbox(
                            value=seed["telegram_detail"], label=t("dash.telegram_status"),
                            interactive=False,
                        )
                    with gr.Column(elem_classes=["td-card"]):
                        gr.Markdown(f"### {t('nav.drive')}", elem_classes=["td-section-title"])
                        with gr.Row():
                            drive_connect_btn = binder.button(gr, "drive.connect", variant="primary")
                            drive_reconnect_btn = binder.button(gr, "drive.reconnect")
                            drive_status_btn = binder.button(gr, "drive.status", variant="secondary")
                        drive_detail = gr.Textbox(
                            value=seed["drive_detail"], label=t("dash.drive_status"),
                            interactive=False,
                        )
                        with gr.Accordion(t("form.folder"), open=False):
                            parent_id = gr.Textbox(label=t("form.parent_folder"), value="root")
                            list_folders_btn = binder.button(gr, "drive.list_folders")
                            folder_choice = gr.Dropdown(
                                choices=[], label=t("form.folder"), allow_custom_value=True
                            )
                            new_folder_name = gr.Textbox(label=t("form.new_folder"))
                            create_folder_btn = binder.button(gr, "drive.create_folder")
                            created_folder = gr.Textbox(label=t("form.folder"), interactive=False)
                            select_folder_btn = binder.button(gr, "drive.select_folder")
                            selected_folder = gr.Textbox(label=t("form.selected_folder"), interactive=False)
                            folder_message = gr.Textbox(label=t("form.folder"), interactive=False)
                        quota_btn = binder.button(gr, "drive.refresh_quota", variant="secondary")
                        quota_line = gr.Textbox(
                            value=seed["quota_line"], label=t("dash.drive_space"), interactive=False
                        )
                        quota_json = gr.JSON(label=t("dash.drive_space"), value=seed["quota_payload"])

            # ---------------- Logs ----------------
            with gr.Tab(t("nav.logs")):
                with gr.Row():
                    logs_query = gr.Textbox(label=t("btn.search_logs"), scale=3)
                    logs_search_btn = binder.button(gr, "logs.search")
                    logs_refresh_btn = binder.button(gr, "logs.refresh", variant="secondary")
                    logs_download_btn = binder.button(gr, "logs.download")
                logs_box = gr.Textbox(
                    value=seed["logs"], label=t("nav.logs"), lines=18,
                    interactive=False, elem_classes=["td-logs"],
                )
                logs_file = gr.File(label=t("btn.download_logs"))

            # ---------------- Settings ----------------
            with gr.Tab(t("nav.settings")):
                concurrency_ready = binder.is_ready("settings.set_concurrency")
                concurrency_note = gr.Textbox(
                    label=t("form.concurrency"),
                    value=(
                        f"{t('form.current_value')}: {seed['concurrency']}/{HARD_CONCURRENCY_CAP}"
                        + ("" if concurrency_ready else f" · {t('common.unavailable')}")
                    ),
                    interactive=False,
                    visible=not concurrency_ready,
                )
                concurrency = gr.Slider(
                    minimum=1, maximum=HARD_CONCURRENCY_CAP, step=1,
                    value=seed["concurrency"], label=t("form.concurrency"),
                    interactive=concurrency_ready, visible=concurrency_ready,
                )
                concurrency_box = gr.Textbox(
                    label=t("form.concurrency"), interactive=False, visible=concurrency_ready
                )
                with gr.Accordion(t("settings.advanced"), open=False):
                    theme_ready = binder.is_ready("settings.set_theme")
                    theme_radio = gr.Radio(
                        ["light", "dark"], value=seed["theme"], label=t("btn.theme"),
                        interactive=theme_ready, visible=theme_ready,
                    )
                    theme_box = gr.Textbox(
                        label=t("btn.theme"), interactive=False, visible=theme_ready
                    )
                    with gr.Row():
                        recover_btn = binder.button(gr, "recovery.restore")
                        checkpoint_btn = binder.button(gr, "maintenance.checkpoint")
                    maintenance_box = gr.Textbox(label=t("nav.maintenance"), interactive=False)

            # ---------------- Colab code & export ----------------
            with gr.Tab(t("nav.export")):
                zip_message = gr.Textbox(label=t("btn.build_zip"), interactive=False)
                zip_file = gr.File(label=t("btn.build_zip"))
                colab_cells_btn = binder.button(gr, "export.colab_cells", variant="secondary")
                colab_cells_box = gr.Textbox(label=t("btn.colab_cells"), lines=18, interactive=False)

        # ---------------- Bindings ----------------
        # wire_if_ready attaches ready actions and skips the ones this repo does
        # not yet prove with a test; those controls were already rendered hidden
        # and disabled by binder.button(), so nothing dead is reachable.
        telegram_outputs = [telegram_detail, telegram_chip, code_panel, password_panel]
        drive_outputs = [drive_detail, drive_chip]
        analyze_outputs = [analyze_message, candidates_table]
        queue_outputs = [queue_status, queue_table]

        binder.wire_if_ready(credentials_btn, "telegram.set_credentials",
                             [api_id, api_hash], telegram_outputs)
        binder.wire_if_ready(send_code_btn, "telegram.send_code", [phone], telegram_outputs)
        binder.wire_if_ready(resend_code_btn, "telegram.resend_code", [], telegram_outputs)
        binder.wire_if_ready(verify_btn, "telegram.verify_code", [code], telegram_outputs)
        binder.wire_if_ready(verify_password_btn, "telegram.verify_password",
                             [password], telegram_outputs)
        binder.wire_if_ready(telegram_logout_btn, "telegram.logout", [], telegram_outputs)
        binder.wire_if_ready(telegram_status_btn, "telegram.status", [], telegram_outputs)

        binder.wire_if_ready(drive_connect_btn, "drive.connect", [], drive_outputs)
        binder.wire_if_ready(drive_reconnect_btn, "drive.reconnect", [], drive_outputs)
        binder.wire_if_ready(drive_status_btn, "drive.status", [], drive_outputs)
        binder.wire_if_ready(list_folders_btn, "drive.list_folders", [parent_id],
                             [folder_message, folder_choice])
        binder.wire_if_ready(create_folder_btn, "drive.create_folder",
                             [new_folder_name, parent_id], [folder_message, created_folder])
        binder.wire_if_ready(select_folder_btn, "drive.select_folder", [folder_choice],
                             [folder_message, selected_folder])
        binder.wire_if_ready(quota_btn, "drive.refresh_quota", [], [quota_line, quota_json])

        binder.wire_if_ready(
            analyze_btn,
            "analyze.run",
            [link, mode, message_id, start_id, end_id, limit, media_types],
            analyze_outputs,
        )
        binder.wire_if_ready(
            filters_btn, "analyze.apply_filters",
            [filter_media_types, extensions, min_size, max_size, date_from, date_to, include, exclude],
            analyze_outputs,
        )
        binder.wire_if_ready(select_all_btn, "analyze.select_all", [], analyze_outputs)
        binder.wire_if_ready(clear_selection_btn, "analyze.clear_selection", [], analyze_outputs)
        binder.wire_if_ready(enqueue_btn, "analyze.enqueue_selected", [], analyze_outputs)

        binder.wire_if_ready(start_btn, "queue.start_selected", [], queue_outputs)
        binder.wire_if_ready(pause_btn, "queue.pause", [], queue_outputs)
        binder.wire_if_ready(resume_btn, "queue.resume", [], queue_outputs)
        binder.wire_if_ready(stop_btn, "queue.stop", [], queue_outputs)
        binder.wire_if_ready(retry_failed_btn, "queue.retry_failed", [], queue_outputs)
        binder.wire_if_ready(clear_completed_btn, "queue.clear_completed", [], queue_outputs)
        binder.wire_if_ready(refresh_queue_btn, "queue.refresh", [], queue_outputs)
        binder.wire_if_ready(pause_item_btn, "queue.pause_item", [item_id], queue_outputs)
        binder.wire_if_ready(resume_item_btn, "queue.resume_item", [item_id], queue_outputs)
        binder.wire_if_ready(stop_item_btn, "queue.stop_item", [item_id], queue_outputs)
        binder.wire_if_ready(retry_item_btn, "queue.retry_item", [item_id], queue_outputs)

        binder.wire_if_ready(dashboard_btn, "dashboard.refresh", [], [dashboard_json])

        binder.wire_if_ready(logs_refresh_btn, "logs.refresh", [], [logs_box])
        binder.wire_if_ready(logs_search_btn, "logs.search", [logs_query], [logs_box])
        binder.wire_if_ready(logs_download_btn, "logs.download", [], [logs_file])

        binder.wire_if_ready(concurrency, "settings.set_concurrency", [concurrency],
                             [concurrency_box], event="change")
        binder.wire_if_ready(language_btn, "settings.toggle_language", [], [lang_state])
        binder.wire_if_ready(theme_radio, "settings.set_theme", [theme_radio], [theme_box],
                             event="change")

        binder.wire_if_ready(recover_btn, "recovery.restore", [], [maintenance_box])
        binder.wire_if_ready(checkpoint_btn, "maintenance.checkpoint", [], [maintenance_box])

        binder.wire_if_ready(zip_btn, "export.build_zip", [], [zip_message, zip_file])
        binder.wire_if_ready(colab_cells_btn, "export.colab_cells", [], [colab_cells_box])

        # Fails the render pass when any ready action was never attached to a
        # control, or when a rendered control was never wired.
        binder.assert_complete()

        refs.update(
            root=root,
            code_panel=code_panel,
            password_panel=password_panel,
            telegram_chip=telegram_chip,
            drive_chip=drive_chip,
            telegram_detail=telegram_detail,
            drive_detail=drive_detail,
            telegram_card=telegram_card,
            drive_card=drive_card,
            queue_card=queue_card,
            queue_status=queue_status,
            queue_table=queue_table,
            analyze_message=analyze_message,
            candidates_table=candidates_table,
            logs_box=logs_box,
            dashboard_json=dashboard_json,
            quota_line=quota_line,
            quota_json=quota_json,
            concurrency_note=concurrency_note,
        )
    return refs
