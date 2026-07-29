"""Gradio layout only.

This module declares components and asks the UIBinder to attach them. It contains
no business logic, no lambdas, no ad-hoc event handlers and no hardcoded
user-facing strings — every label comes from i18n and every behaviour comes from
a named handler declared in ACTION_SPECS.
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
            language_btn = gr.Button(t("btn.language"))
            language_box = gr.Textbox(label=t("btn.language"),
                                      value=ctx.ui_state.language, interactive=False)
            theme_radio = gr.Radio(["light", "dark"], value="light", label=t("btn.theme"))
            theme_box = gr.Textbox(label=t("btn.theme"), interactive=False)

        # ---------------- Connection Center ----------------
        with gr.Tab(t("nav.connection")):
            with gr.Group():
                gr.Markdown(f"### {t('nav.telegram')}")
                api_id = gr.Textbox(label=t("form.api_id"), type="password")
                api_hash = gr.Textbox(label=t("form.api_hash"), type="password")
                credentials_btn = gr.Button(t("btn.connect_telegram"))
                phone = gr.Textbox(label=t("form.phone"))
                with gr.Row():
                    send_code_btn = gr.Button(t("btn.send_code"))
                    resend_code_btn = gr.Button(t("btn.resend_code"))
                code = gr.Textbox(label=t("form.code"))
                verify_btn = gr.Button(t("btn.verify"))
                password = gr.Textbox(label=t("form.password"), type="password")
                verify_password_btn = gr.Button(t("btn.verify_password"))
                with gr.Row():
                    telegram_logout_btn = gr.Button(t("btn.logout"))
                    telegram_status_btn = gr.Button(t("btn.refresh"))
                telegram_detail = gr.Textbox(label=t("dash.telegram_status"), interactive=False)
                telegram_chip = gr.Textbox(label=t("nav.telegram"), interactive=False)

            with gr.Group():
                gr.Markdown(f"### {t('nav.drive')}")
                with gr.Row():
                    drive_connect_btn = gr.Button(t("btn.link_drive"))
                    drive_reconnect_btn = gr.Button(t("btn.drive_reconnect"))
                    drive_status_btn = gr.Button(t("btn.refresh"))
                drive_detail = gr.Textbox(label=t("dash.drive_status"), interactive=False)
                drive_chip = gr.Textbox(label=t("nav.drive"), interactive=False)
                parent_id = gr.Textbox(label=t("form.parent_folder"), value="root")
                list_folders_btn = gr.Button(t("btn.drive_list_folders"))
                folder_choice = gr.Dropdown(choices=[], label=t("form.folder"),
                                            allow_custom_value=True)
                new_folder_name = gr.Textbox(label=t("form.new_folder"))
                create_folder_btn = gr.Button(t("btn.drive_create_folder"))
                created_folder = gr.Textbox(label=t("form.folder"), interactive=False)
                select_folder_btn = gr.Button(t("btn.drive_select_folder"))
                selected_folder = gr.Textbox(label=t("form.selected_folder"), interactive=False)
                folder_message = gr.Textbox(label=t("nav.drive"), interactive=False)
                quota_btn = gr.Button(t("btn.refresh_quota"))
                quota_line = gr.Textbox(label=t("dash.drive_space"), interactive=False)
                quota_json = gr.JSON(label=t("dash.drive_space"))

        # ---------------- Analyze ----------------
        with gr.Tab(t("nav.link")):
            link = gr.Textbox(label=t("form.link"))
            scope = gr.Radio(list(SCOPE_CHOICES), value="auto", label=t("form.scope"))
            analyze_btn = gr.Button(t("btn.analyze"))
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
                filters_btn = gr.Button(t("btn.apply_filters"))
            with gr.Row():
                select_all_btn = gr.Button(t("btn.select_all"))
                clear_selection_btn = gr.Button(t("btn.clear_selection"))
                enqueue_btn = gr.Button(t("btn.enqueue_selected"))

        # ---------------- Transfers ----------------
        with gr.Tab(t("nav.queue")):
            with gr.Row():
                start_btn = gr.Button(t("btn.start"))
                pause_btn = gr.Button(t("btn.pause"))
                resume_btn = gr.Button(t("btn.resume"))
                stop_btn = gr.Button(t("btn.stop"))
            with gr.Row():
                retry_failed_btn = gr.Button(t("btn.retry_failed"))
                clear_completed_btn = gr.Button(t("btn.clear_completed"))
                refresh_queue_btn = gr.Button(t("btn.refresh"))
            queue_status = gr.Textbox(label=t("dash.queue_status"), interactive=False)
            queue_table = gr.Dataframe(headers=_headers(), interactive=False)
            item_id = gr.Textbox(label=t("col.id"))
            with gr.Row():
                pause_item_btn = gr.Button(t("btn.pause_item"))
                resume_item_btn = gr.Button(t("btn.resume_item"))
                stop_item_btn = gr.Button(t("btn.stop_item"))
                retry_item_btn = gr.Button(t("btn.retry_item"))

        # ---------------- Dashboard ----------------
        with gr.Tab(t("nav.dashboard")):
            dashboard_btn = gr.Button(t("btn.refresh"))
            dashboard_json = gr.JSON(label=t("nav.dashboard"))

        # ---------------- Logs ----------------
        with gr.Tab(t("nav.logs")):
            logs_refresh_btn = gr.Button(t("btn.refresh"))
            logs_query = gr.Textbox(label=t("btn.search_logs"))
            logs_search_btn = gr.Button(t("btn.search_logs"))
            logs_box = gr.Textbox(label=t("nav.logs"), lines=20, interactive=False)
            logs_download_btn = gr.Button(t("btn.download_logs"))
            logs_file = gr.File(label=t("btn.download_logs"))

        # ---------------- Settings ----------------
        with gr.Tab(t("nav.settings")):
            concurrency = gr.Radio(list(CONCURRENCY_CHOICES),
                                   value=ctx.config.concurrency, label=t("form.concurrency"))
            concurrency_box = gr.Textbox(label=t("form.concurrency"), interactive=False)
            recover_btn = gr.Button(t("btn.recover"))
            checkpoint_btn = gr.Button(t("btn.checkpoint"))
            maintenance_box = gr.Textbox(label=t("nav.settings"), interactive=False)

        # ---------------- Export ----------------
        with gr.Tab(t("nav.export")):
            build_zip_btn = gr.Button(t("btn.build_zip"))
            zip_message = gr.Textbox(label=t("nav.export"), interactive=False)
            zip_file = gr.File(label=t("btn.build_zip"))
            colab_cells_btn = gr.Button(t("btn.colab_cells"))
            colab_cells_box = gr.Textbox(label=t("btn.colab_cells"), lines=20, interactive=False)

        # ---------------- Bindings ----------------
        telegram_outputs = [telegram_detail, telegram_chip]
        drive_outputs = [drive_detail, drive_chip]
        analyze_outputs = [analyze_message, candidates_table]
        queue_outputs = [queue_status, queue_table]

        binder.wire(credentials_btn, "telegram.set_credentials", [api_id, api_hash], telegram_outputs)
        binder.wire(send_code_btn, "telegram.send_code", [phone], telegram_outputs)
        binder.wire(resend_code_btn, "telegram.resend_code", [], telegram_outputs)
        binder.wire(verify_btn, "telegram.verify_code", [code], telegram_outputs)
        binder.wire(verify_password_btn, "telegram.verify_password", [password], telegram_outputs)
        binder.wire(telegram_logout_btn, "telegram.logout", [], telegram_outputs)
        binder.wire(telegram_status_btn, "telegram.status", [], telegram_outputs)

        binder.wire(drive_connect_btn, "drive.connect", [], drive_outputs)
        binder.wire(drive_reconnect_btn, "drive.reconnect", [], drive_outputs)
        binder.wire(drive_status_btn, "drive.status", [], drive_outputs)
        binder.wire(list_folders_btn, "drive.list_folders", [parent_id],
                    [folder_message, folder_choice])
        binder.wire(create_folder_btn, "drive.create_folder", [new_folder_name, parent_id],
                    [folder_message, created_folder])
        binder.wire(select_folder_btn, "drive.select_folder", [folder_choice],
                    [folder_message, selected_folder])
        binder.wire(quota_btn, "drive.refresh_quota", [], [quota_line, quota_json])

        binder.wire(analyze_btn, "analyze.run", [link, scope], analyze_outputs)
        binder.wire(
            filters_btn, "analyze.apply_filters",
            [media_types, extensions, min_size, max_size, date_from, date_to, include, exclude],
            analyze_outputs,
        )
        binder.wire(select_all_btn, "analyze.select_all", [], analyze_outputs)
        binder.wire(clear_selection_btn, "analyze.clear_selection", [], analyze_outputs)
        binder.wire(enqueue_btn, "analyze.enqueue_selected", [], analyze_outputs)

        binder.wire(start_btn, "queue.start_selected", [], queue_outputs)
        binder.wire(pause_btn, "queue.pause", [], queue_outputs)
        binder.wire(resume_btn, "queue.resume", [], queue_outputs)
        binder.wire(stop_btn, "queue.stop", [], queue_outputs)
        binder.wire(retry_failed_btn, "queue.retry_failed", [], queue_outputs)
        binder.wire(clear_completed_btn, "queue.clear_completed", [], queue_outputs)
        binder.wire(refresh_queue_btn, "queue.refresh", [], queue_outputs)
        binder.wire(pause_item_btn, "queue.pause_item", [item_id], queue_outputs)
        binder.wire(resume_item_btn, "queue.resume_item", [item_id], queue_outputs)
        binder.wire(stop_item_btn, "queue.stop_item", [item_id], queue_outputs)
        binder.wire(retry_item_btn, "queue.retry_item", [item_id], queue_outputs)

        binder.wire(dashboard_btn, "dashboard.refresh", [], [dashboard_json])

        binder.wire(logs_refresh_btn, "logs.refresh", [], [logs_box])
        binder.wire(logs_search_btn, "logs.search", [logs_query], [logs_box])
        binder.wire(logs_download_btn, "logs.download", [], [logs_file])

        binder.wire(concurrency, "settings.set_concurrency", [concurrency], [concurrency_box],
                    event="change")
        binder.wire(language_btn, "settings.toggle_language", [], [language_box])
        binder.wire(theme_radio, "settings.set_theme", [theme_radio], [theme_box], event="change")

        binder.wire(recover_btn, "recovery.restore", [], [maintenance_box])
        binder.wire(checkpoint_btn, "maintenance.checkpoint", [], [maintenance_box])

        binder.wire(build_zip_btn, "export.build_zip", [], [zip_message, zip_file])
        binder.wire(colab_cells_btn, "export.colab_cells", [], [colab_cells_box])

        # Fails the build when any ready action was never attached to a control.
        binder.assert_complete()

    return demo
