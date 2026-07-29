"""Gradio layout only.

This module declares components and asks the UIBinder to attach them. It contains
no business logic, no lambdas, no ad-hoc event handlers and no hardcoded
user-facing strings — every label comes from i18n and every behaviour comes from
a named handler declared in ACTION_SPECS.

Every actionable control is created through `binder.button(...)`, so a control
whose spec is not implemented+tested renders hidden and disabled instead of
being wired to nothing (Constitution 4A.1 rules 2, 3 and 6).
"""
from __future__ import annotations

from typing import Any

from .app_context import ApplicationContext, get_context
from .i18n import t

try:
    import gradio as gr
except Exception:  # pragma: no cover - Colab always has gradio
    gr = None  # type: ignore

TABLE_HEADERS = ("col.id", "col.file", "col.type", "col.size",
                 "col.state", "col.progress", "col.attempts")
MEDIA_TYPES = ("photo", "video", "audio", "voice", "document", "animation", "sticker")
CONCURRENCY_CHOICES = ("safe", "balanced", "fast")
SCOPE_CHOICES = ("auto", "message", "chat")


def _headers() -> list[str]:
    return [t(key) for key in TABLE_HEADERS]


def build(ctx: ApplicationContext | None = None) -> Any:
    """Build the Gradio app and fail the build if any control is unwired."""
    if ctx is None:
        ctx = get_context()
    if gr is None:
        raise RuntimeError("gradio is not installed")
    binder = ctx.binder

    with gr.Blocks(title=t("app.title"), theme=gr.themes.Soft()) as demo:
        gr.Markdown(f"# {t('app.title')}\n{t('app.subtitle')}")

        with gr.Row():
            language_btn = binder.button(gr, "settings.toggle_language")
            language_box = gr.Textbox(label=t("btn.language"),
                                      value=ctx.ui_state.language, interactive=False)
            theme_ready = binder.is_ready("settings.set_theme")
            theme_radio = gr.Radio(["light", "dark"], value="light", label=t("btn.theme"),
                                   interactive=theme_ready, visible=theme_ready)
            theme_box = gr.Textbox(label=t("btn.theme"), interactive=False,
                                   visible=theme_ready)

        # ---------------- Connection Center ----------------
        with gr.Tab(t("nav.connection")):
            with gr.Group():
                gr.Markdown(f"### {t('nav.telegram')}")
                api_id = gr.Textbox(label=t("form.api_id"), type="password")
                api_hash = gr.Textbox(label=t("form.api_hash"), type="password")
                credentials_btn = binder.button(gr, "telegram.set_credentials")
                phone = gr.Textbox(label=t("form.phone"))
                with gr.Row():
                    send_code_btn = binder.button(gr, "telegram.send_code")
                    resend_code_btn = binder.button(gr, "telegram.resend_code")
                code = gr.Textbox(label=t("form.code"))
                verify_btn = binder.button(gr, "telegram.verify_code")
                password = gr.Textbox(label=t("form.password"), type="password")
                verify_password_btn = binder.button(gr, "telegram.verify_password")
                with gr.Row():
                    telegram_logout_btn = binder.button(gr, "telegram.logout")
                    telegram_status_btn = binder.button(gr, "telegram.status")
                telegram_detail = gr.Textbox(label=t("dash.telegram_status"), interactive=False)
                telegram_chip = gr.Textbox(label=t("nav.telegram"), interactive=False)

            with gr.Group():
                gr.Markdown(f"### {t('nav.drive')}")
                with gr.Row():
                    drive_connect_btn = binder.button(gr, "drive.connect")
                    drive_reconnect_btn = binder.button(gr, "drive.reconnect")
                    drive_status_btn = binder.button(gr, "drive.status")
                drive_detail = gr.Textbox(label=t("dash.drive_status"), interactive=False)
                drive_chip = gr.Textbox(label=t("nav.drive"), interactive=False)
                parent_id = gr.Textbox(label=t("form.parent_folder"), value="root")
                list_folders_btn = binder.button(gr, "drive.list_folders")
                folder_choice = gr.Dropdown(choices=[], label=t("form.folder"),
                                            allow_custom_value=True)
                new_folder_name = gr.Textbox(label=t("form.new_folder"))
                create_folder_btn = binder.button(gr, "drive.create_folder")
                created_folder = gr.Textbox(label=t("form.folder"), interactive=False)
                select_folder_btn = binder.button(gr, "drive.select_folder")
                selected_folder = gr.Textbox(label=t("form.selected_folder"), interactive=False)
                folder_message = gr.Textbox(label=t("nav.drive"), interactive=False)
                quota_btn = binder.button(gr, "drive.refresh_quota")
                quota_line = gr.Textbox(label=t("dash.drive_space"), interactive=False)
                quota_json = gr.JSON(label=t("dash.drive_space"))

        # ---------------- Analyze ----------------
        with gr.Tab(t("nav.link")):
            link = gr.Textbox(label=t("form.link"))
            scope = gr.Radio(list(SCOPE_CHOICES), value="auto", label=t("form.scope"))
            analyze_btn = binder.button(gr, "analyze.run")
            analyze_message = gr.Textbox(label=t("nav.link"), interactive=False)
            candidates_table = gr.Dataframe(headers=_headers(), interactive=False)
            with gr.Accordion(t("form.filters"), open=False):
                media_types = gr.CheckboxGroup(list(MEDIA_TYPES), label=t("col.type"))
                extensions = gr.Textbox(label=t("form.extensions"))
                min_size = gr.Number(label=t("form.min_size_mb"), value=None)
                max_size = gr.Number(label=t("form.max_size_mb"), value=None)
                date_from = gr.Textbox(label=t("form.date_from"))
                date_to = gr.Textbox(label=t("form.date_to"))
                include = gr.Textbox(label=t("form.include"))
                exclude = gr.Textbox(label=t("form.exclude"))
                filters_btn = binder.button(gr, "analyze.apply_filters")
            with gr.Row():
                select_all_btn = binder.button(gr, "analyze.select_all")
                clear_selection_btn = binder.button(gr, "analyze.clear_selection")
                enqueue_btn = binder.button(gr, "analyze.enqueue_selected")

        # ---------------- Transfers ----------------
        with gr.Tab(t("nav.queue")):
            with gr.Row():
                start_btn = binder.button(gr, "queue.start_selected")
                pause_btn = binder.button(gr, "queue.pause")
                resume_btn = binder.button(gr, "queue.resume")
                stop_btn = binder.button(gr, "queue.stop")
            with gr.Row():
                retry_failed_btn = binder.button(gr, "queue.retry_failed")
                clear_completed_btn = binder.button(gr, "queue.clear_completed")
                refresh_queue_btn = binder.button(gr, "queue.refresh")
            queue_status = gr.Textbox(label=t("dash.queue_status"), interactive=False)
            queue_table = gr.Dataframe(headers=_headers(), interactive=False)
            item_id = gr.Textbox(label=t("col.id"))
            with gr.Row():
                pause_item_btn = binder.button(gr, "queue.pause_item")
                resume_item_btn = binder.button(gr, "queue.resume_item")
                stop_item_btn = binder.button(gr, "queue.stop_item")
                retry_item_btn = binder.button(gr, "queue.retry_item")

        # ---------------- Dashboard ----------------
        with gr.Tab(t("nav.dashboard")):
            dashboard_btn = binder.button(gr, "dashboard.refresh")
            dashboard_json = gr.JSON(label=t("nav.dashboard"))

        # ---------------- Logs ----------------
        with gr.Tab(t("nav.logs")):
            logs_refresh_btn = binder.button(gr, "logs.refresh")
            logs_query = gr.Textbox(label=t("btn.search_logs"))
            logs_search_btn = binder.button(gr, "logs.search")
            logs_box = gr.Textbox(label=t("nav.logs"), lines=20, interactive=False)
            logs_download_btn = binder.button(gr, "logs.download")
            logs_file = gr.File(label=t("btn.download_logs"))

        # ---------------- Settings ----------------
        with gr.Tab(t("nav.settings")):
            concurrency_ready = binder.is_ready("settings.set_concurrency")
            concurrency = gr.Radio(list(CONCURRENCY_CHOICES),
                                   value=ctx.config.concurrency, label=t("form.concurrency"),
                                   interactive=concurrency_ready, visible=concurrency_ready)
            concurrency_box = gr.Textbox(label=t("form.concurrency"), interactive=False,
                                         visible=concurrency_ready)
            recover_btn = binder.button(gr, "recovery.restore")
            checkpoint_btn = binder.button(gr, "maintenance.checkpoint")
            maintenance_box = gr.Textbox(label=t("nav.settings"), interactive=False)

        # ---------------- Export ----------------
        with gr.Tab(t("nav.export")):
            build_zip_btn = binder.button(gr, "export.build_zip")
            zip_message = gr.Textbox(label=t("nav.export"), interactive=False)
            zip_file = gr.File(label=t("btn.build_zip"))
            colab_cells_btn = binder.button(gr, "export.colab_cells")
            colab_cells_box = gr.Textbox(label=t("btn.colab_cells"), lines=20, interactive=False)

        # ---------------- Bindings ----------------
        # wire_if_ready attaches ready actions and skips the ones this repo does
        # not yet prove with a test; those controls were already rendered hidden
        # and disabled by binder.button(), so nothing dead is reachable.
        telegram_outputs = [telegram_detail, telegram_chip]
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

        binder.wire_if_ready(analyze_btn, "analyze.run", [link, scope], analyze_outputs)
        binder.wire_if_ready(
            filters_btn, "analyze.apply_filters",
            [media_types, extensions, min_size, max_size, date_from, date_to, include, exclude],
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
        binder.wire_if_ready(language_btn, "settings.toggle_language", [], [language_box])
        binder.wire_if_ready(theme_radio, "settings.set_theme", [theme_radio], [theme_box],
                             event="change")

        binder.wire_if_ready(recover_btn, "recovery.restore", [], [maintenance_box])
        binder.wire_if_ready(checkpoint_btn, "maintenance.checkpoint", [], [maintenance_box])

        binder.wire_if_ready(build_zip_btn, "export.build_zip", [], [zip_message, zip_file])
        binder.wire_if_ready(colab_cells_btn, "export.colab_cells", [], [colab_cells_box])

        # Fails the build when any ready action was never attached to a control,
        # or when a rendered control was never wired.
        binder.assert_complete()

    return demo
