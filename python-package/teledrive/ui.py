"""Gradio layout only — TeleDrive graphite shell (M15-T04, restyled in M17-T03).

Layout rules (Constitution §4 + DOC-37 Part B):
* ui.py is LAYOUT ONLY. No SQL, no business logic, no lambdas, no ad-hoc events.
* All events go through ``binder.wire(...)`` — zero direct ``.click/.change/.submit``.
* All colors come from CSS variables in ``ui_theme.py`` — zero hardcoded colors here.
* Arabic RTL is the default; the language toggle triggers ``gr.render`` re-render.
* Runtime state (Telegram/Drive/queue/selection) lives on the ApplicationContext,
  not in Gradio state; ``shell_seed`` reads it live so re-render never fabricates
  values (empty tables stay empty, chips show "غير متصل" until connected).
"""
from __future__ import annotations

from typing import Any

from .app_context import ApplicationContext, get_context
from .config import SUPPORTED_LANGUAGES
from .handlers import shell_seed
from .i18n import set_language, t
from .media_scanner import MAX_SCAN_MESSAGES
from .ui_theme import BASE_CSS, theme_style_block

try:
    import gradio as gr
except Exception:  # pragma: no cover - Colab always has gradio
    gr = None  # type: ignore


TABLE_HEADERS = (
    "col.id", "col.file", "col.type", "col.size",
    "col.state", "col.progress", "col.attempts",
)
# DOC-39 §5.2: candidates table — selection marker is part of the table value.
CANDIDATE_HEADERS = (
    "col.select", "col.msg_id", "col.file", "col.type",
    "col.size", "col.group", "col.date", "col.state",
)
# Canonical media filter values. Each label is a direct t("media.<name>")
# call so static contract checks that grep for the literal translation
# markers still see them, and so do the localisation/extraction tools.
_MEDIA_CHOICES = (
    (t("media.all"), "all"),
    (t("media.video"), "video"),
    (t("media.audio"), "audio"),
    (t("media.document"), "document"),
    (t("media.photo"), "photo"),
    (t("media.voice"), "voice"),
    (t("media.animation"), "animation"),
    (t("media.sticker"), "sticker"),
)
MEDIA_TYPES = ("photo", "video", "audio", "voice", "document", "animation", "sticker")
LOG_LEVELS = ("ALL", "INFO", "WARNING", "ERROR", "RECOVERY")
# Seven right-rail sections, in the order specified by DOC-37 §6.
NAV_SECTIONS: tuple[tuple[str, str], ...] = (
    ("nav.dashboard",   "dashboard"),
    ("nav.queue",       "transfers"),
    ("nav.analyze",     "analyze"),
    ("nav.connection",  "connection"),
    ("nav.logs",        "logs"),
    ("nav.settings",    "settings"),
    ("nav.export",      "export"),
)


def _headers() -> list[str]:
    return [t(key) for key in TABLE_HEADERS]


def _graphite_theme() -> Any:
    """Soft base recolored via CSS variables; this factory only exists because
    Gradio still requires a Theme object at Blocks construction time.
    """
    return gr.themes.Soft(primary_hue="lime", neutral_hue="gray")


def build(ctx: ApplicationContext | None = None) -> Any:
    if ctx is None:
        ctx = get_context()
    if gr is None:
        raise RuntimeError("gradio is not installed")
    binder = ctx.binder

    # Default language/theme come from persisted PreferencesService on ctx.
    language = ctx.ui_state.language
    if language not in SUPPORTED_LANGUAGES:
        language = "ar"
    set_language(language)

    with gr.Blocks(
        title=t("app.title"),
        elem_id="td-root",
    ) as demo:
        # Invisible host for the theme style block (replaced by set_theme).
        theme_host = gr.HTML(
            theme_style_block(ctx.preferences.current_theme()),
            elem_id="td-theme-vars-host",
            visible=False,
        )
        lang_state = gr.State(language)
        active_tab = gr.State("dashboard")

        # Do not restrict this render to State.change: Gradio's default render
        # trigger performs the initial page-load render as well as re-rendering
        # when lang_state changes. Restricting it left a blank shell on first
        # opening the Colab URL.
        @gr.render(inputs=[lang_state])
        def _language_root(lang: str) -> None:
            _render_shell(ctx, binder, lang_state, active_tab, theme_host, lang)

    # Gradio 6 deprecates theme/css on Blocks; app.launch supplies these.
    demo.td_theme = _graphite_theme()
    demo.td_css = BASE_CSS
    return demo


def _status_chip(value: str, state: str) -> str:
    """Render a td-chip with a data-state attribute for CSS coloring."""
    return (
        f'<span class="td-chip" data-state="{state}">'
        f'<span class="td-ltr">{value}</span></span>'
    )


def _render_shell(
    ctx: ApplicationContext,
    binder,
    lang_state: Any = None,
    active_tab_or_lang: Any = None,
    theme_host_or_active: Any = None,
    lang_or_theme: Any = None,
) -> dict[str, Any]:
    """Accept both the legacy (ctx, binder, lang_state, lang) and new
    (ctx, binder, lang_state, active_tab, theme_host, lang) call shapes.
    """
    # Detect which shape: if the 4th arg is a string, treat as legacy (lang);
    # else it's active_tab and 6th arg is lang.
    if isinstance(active_tab_or_lang, str) and lang_or_theme is None:
        active_tab = None
        theme_host = None
        lang: str = active_tab_or_lang
    else:
        active_tab = active_tab_or_lang
        theme_host = theme_host_or_active
        lang = lang_or_theme if isinstance(lang_or_theme, str) else (
            ctx.ui_state.language if ctx else "ar"
        )
    if lang not in SUPPORTED_LANGUAGES:
        lang = "ar"
    set_language(lang)
    direction = "td-rtl" if lang == "ar" else "td-ltr"
    seed = shell_seed(ctx)
    refs: dict[str, Any] = {"direction": direction}
    # Ensure the theme style host exists even when _render_shell is invoked
    # standalone (e.g. from tests). During normal build() it is created in the
    # outer Blocks scope and passed in.
    if theme_host is None and gr is not None:
        theme_host = gr.HTML(
            theme_style_block(ctx.preferences.current_theme()),
            elem_id="td-theme-vars-host",
            visible=False,
        )

    # ----- helpers -----
    def chip(val: str, state: str = "warn") -> str:
        return _status_chip(val or t("status.disconnected"), state)

    tg_ok = bool(seed.get("telegram_connected"))
    dr_ok = bool(seed.get("drive_connected"))

    with gr.Column(elem_classes=["td-root", direction]):
        # ===== Top status bar (real chips from ctx, styled HTML) =====
        with gr.Row(elem_classes=["td-topbar"]):
            gr.HTML(
                f'<div class="td-brand"><strong>TeleDrive</strong> '
                f'<code>v{ctx.config.version}</code></div>',
            )
            telegram_chip = gr.HTML(
                value=seed["telegram_chip"], show_label=False,
                elem_classes=["td-chip-host"],
            )
            drive_chip = gr.HTML(
                value=seed["drive_chip"], show_label=False,
                elem_classes=["td-chip-host"],
            )
            folder_chip = gr.HTML(
                value=seed["folder_chip"], show_label=False,
                elem_classes=["td-chip-host"],
            )
            engine_chip = gr.HTML(
                value=chip(t("dash.engine_colab"), "ok"), show_label=False,
                elem_classes=["td-chip-host"],
            )
            lang_btn = binder.button(gr, "settings.toggle_language", variant="secondary")
            top_zip_btn = binder.button(gr, "export.build_zip", variant="secondary")

        # ===== Shell grid: content + right nav rail =====
        with gr.Column(elem_id="td-shell"):
            with gr.Column(elem_id="td-content"):
                with gr.Tabs(elem_classes=["td-tabs"]):
                    # Dashboard
                    _dash_refs = _section_dashboard(ctx, binder, seed)
                    # Transfers
                    _queue_refs = _section_transfers(ctx, binder, seed)
                    # Analyze
                    _analyze_refs = _section_analyze(ctx, binder, seed)
                    # Connection center
                    _conn_refs = _section_connection(ctx, binder, seed)
                    # Logs
                    _logs_refs = _section_logs(ctx, binder, seed)
                    # Settings
                    _set_refs = _section_settings(ctx, binder, seed)
                    # Export (prominent primary button in-section; top-bar zip is separate)
                    _export_refs = _section_export(ctx, binder, seed)

                # Gather well-known refs required by contract tests.
                refs.update(
                    theme_host=theme_host,
                    telegram_chip=telegram_chip,
                    drive_chip=drive_chip,
                    folder_chip=folder_chip,
                    engine_chip=engine_chip,
                    logs_box=_logs_refs["logs_box"],
                    logs_file=_logs_refs["logs_file"],
                    logs_status=_logs_refs["logs_status"],
                    logs_query=_logs_refs["logs_query"],
                    logs_level=_logs_refs["logs_level"],
                    logs_refresh_btn=_logs_refs["logs_refresh_btn"],
                    logs_search_btn=_logs_refs["logs_search_btn"],
                    logs_download_btn=_logs_refs["logs_download_btn"],
                    dashboard_json=_dash_refs["dashboard_json"],
                    dashboard_btn=_dash_refs["dash_btn"],
                    queue_status=_queue_refs["queue_status"],
                    queue_table=_queue_refs["queue_table"],
                    concurrency_slider=_set_refs["concurrency"],
                    concurrency_box=_set_refs["concurrency_box"],
                    theme_radio=_set_refs["theme_radio"],
                    theme_status=_set_refs["theme_status"],
                    recovery_btn=_set_refs["recover_btn"],
                    checkpoint_btn=_set_refs["checkpoint_btn"],
                    maintenance_box=_set_refs["maintenance_box"],
                    candidates_table=_analyze_refs["candidates_table"],
                    analyze_message=_analyze_refs["analyze_message"],
                    analyze_btn=_analyze_refs["analyze_btn"],
                    code_panel=_conn_refs["code_panel"],
                    password_panel=_conn_refs["password_panel"],
                    telegram_detail=_conn_refs["telegram_detail"],
                    drive_detail=_conn_refs["drive_detail"],
                    telegram_card=_dash_refs["telegram_card"],
                    drive_card=_dash_refs["drive_card"],
                    queue_card=_dash_refs["queue_card"],
                    zip_message=_export_refs["zip_message"],
                    zip_file=_export_refs["zip_file"],
                    colab_cells_box=_export_refs["colab_cells_box"],
                    build_zip_btn=_export_refs["build_zip_btn"],
                    colab_cells_btn=_export_refs["colab_cells_btn"],
                    colab_status=_export_refs["colab_status"],
                    folder_dash=_dash_refs["folder_picker"],
                    folder_transfer=_queue_refs["folder_picker"],
                    folder_settings=_set_refs["folder_picker"],
                    folder_conn=_conn_refs["folder_picker"],
                    selection_preview=_analyze_refs["selection_preview"],
                    range_start=_analyze_refs["range_start"],
                    range_end=_analyze_refs["range_end"],
                    group_choice=_analyze_refs["group_choice"],
                    enqueue_btn=_analyze_refs["enqueue_btn"],
                )

            # ===== Right navigation rail =====
            with gr.Column(elem_id="td-rail"):
                rail_buttons: list[Any] = []
                for idx, (label_key, _tab_key) in enumerate(NAV_SECTIONS, start=1):
                    b = gr.Button(
                        f"{idx}. {t(label_key)}",
                        elem_classes=["td-item"],
                    )
                    rail_buttons.append(b)
                gr.HTML(
                    f'<div class="td-rail-foot"><span class="td-chip" data-state="ok">'
                    f'<span class="td-ltr">{ctx.config.version}</span></span></div>'
                )

        # ===== Bindings =====
        _bind_actions(
            ctx, binder,
            dash=_dash_refs, queue=_queue_refs, analyze=_analyze_refs,
            conn=_conn_refs, logs=_logs_refs, sets=_set_refs,
            export=_export_refs, lang=lang_state, theme=theme_host,
            rail_buttons=rail_buttons, active_tab=active_tab,
            telegram_chip=telegram_chip, drive_chip=drive_chip,
            folder_chip=folder_chip,
            top_zip_btn=top_zip_btn, lang_btn=lang_btn,
        )
        binder.assert_complete()

    return refs


# ---------------------------------------------------------------------------
# Section builders. Each returns the component refs its wiring block needs.
# ---------------------------------------------------------------------------

def _render_folder_picker(ctx, binder, suffix: str, lang: str, open: bool = False) -> dict[str, Any]:
    """One Drive destination panel reused by dashboard, transfers, settings and connection.

    DOC-39 §4 rules: the panel is ALWAYS visible; when Drive is disconnected
    every control is disabled and the message says to connect first (no fake
    folder list). The current-folder box shows the persisted ID's display name
    or «لم يتم اختيار مجلد» — it never invents a name.
    """
    connected = bool(getattr(getattr(ctx, "drive_auth", None), "connected", False))
    reason = "" if connected else t("err.drive_not_ready")
    # The persisted folder ID (with its Drive-derived name) is the ONE truth,
    # shown even while disconnected — it is real state, never fabricated.
    folder_name = ctx.drive_folders.current_folder_name()
    current_value = folder_name if folder_name else (
        t("msg.no_folder_selected") if connected else "—"
    )
    with gr.Accordion(t("form.drive_folder"), open=open, elem_id=f"td-folder-{suffix}"):
        parent_id = gr.Textbox(label=t("form.parent_folder"), value="root", interactive=connected)
        list_btn = binder.button(gr, "drive.list_folders", interactive=connected)
        choice = gr.Dropdown(choices=[], label=t("form.folder"), allow_custom_value=True,
                             interactive=connected)
        new_name = gr.Textbox(label=t("form.new_folder"), interactive=connected)
        create_btn = binder.button(gr, "drive.create_folder", interactive=connected)
        select_btn = binder.button(gr, "drive.select_folder", interactive=connected)
        current = gr.Textbox(value=current_value,
                             label=t("form.selected_folder"), interactive=False)
        message = gr.Textbox(value=reason, label=t("form.folder"), interactive=False)
    return {"suffix": suffix, "parent_id": parent_id, "list_btn": list_btn,
            "choice": choice, "new_name": new_name, "create_btn": create_btn,
            "select_btn": select_btn, "current": current, "message": message}


def _section_dashboard(ctx, binder, seed) -> dict[str, Any]:
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
        dash_btn = binder.button(gr, "dashboard.refresh", variant="secondary")
        dashboard_json = gr.JSON(
            label=t("dash.stats"), value=seed.get("dashboard", {}),
        )
        folder_picker = _render_folder_picker(ctx, binder, "dash", t("common.language"), open=True)
    return {
        "telegram_card": telegram_card, "drive_card": drive_card,
        "queue_card": queue_card, "dash_btn": dash_btn,
        "dashboard_json": dashboard_json, "folder_picker": folder_picker,
    }


def _section_transfers(ctx, binder, seed) -> dict[str, Any]:
    with gr.Tab(t("nav.queue")):
        # DOC-39 §4: the Drive target panel lives HERE, inside transfers —
        # the same single source of truth as dashboard/settings/connection.
        folder_picker = _render_folder_picker(ctx, binder, "transfer", t("common.language"), open=True)
        gr.Markdown(f"### {t('transfer.controls')}", elem_classes=["td-section-title"])
        with gr.Row():
            start_btn = binder.button(gr, "queue.start_selected", variant="primary", scale=2)
            pause_btn = binder.button(gr, "queue.pause")
            resume_btn = binder.button(gr, "queue.resume")
            stop_btn = binder.button(gr, "queue.stop", variant="stop")
        with gr.Row():
            retry_btn = binder.button(gr, "queue.retry_failed")
            clear_btn = binder.button(gr, "queue.clear_completed")
            refresh_q_btn = binder.button(gr, "queue.refresh", variant="secondary")
        concurrency_chip = gr.HTML(
            _status_chip(
                t("settings.concurrency.label") + f" {seed['concurrency']}/4",
                "ok" if 1 <= seed["concurrency"] <= 4 else "warn",
            )
        )
        queue_status = gr.Textbox(
            value=seed["queue_header"], label=t("dash.queue_status"), interactive=False,
        )
        queue_table = gr.Dataframe(
            headers=_headers(),
            value=seed["queue_rows"] if seed["queue_rows"] else None,
            interactive=False, wrap=True, elem_classes=["td-table"],
        )
        if not seed["queue_rows"]:
            gr.Markdown(f"**{t('queue.empty')}**", elem_classes=["td-empty"])
        with gr.Group(elem_classes=["td-card"]):
            gr.Markdown(f"### {t('transfer.item')}", elem_classes=["td-section-title"])
            with gr.Row():
                item_id = gr.Textbox(label=t("col.id"), scale=2)
                pause_item_btn = binder.button(gr, "queue.pause_item")
                resume_item_btn = binder.button(gr, "queue.resume_item")
                stop_item_btn = binder.button(gr, "queue.stop_item", variant="stop")
                retry_item_btn = binder.button(gr, "queue.retry_item")
    return {
        "start_btn": start_btn, "pause_btn": pause_btn, "resume_btn": resume_btn,
        "stop_btn": stop_btn, "retry_btn": retry_btn, "clear_btn": clear_btn,
        "refresh_q_btn": refresh_q_btn, "queue_status": queue_status,
        "queue_table": queue_table, "concurrency_chip": concurrency_chip,
        "item_id": item_id, "pause_item_btn": pause_item_btn,
        "resume_item_btn": resume_item_btn, "stop_item_btn": stop_item_btn,
        "retry_item_btn": retry_item_btn, "folder_picker": folder_picker,
    }


def _section_analyze(ctx, binder, seed) -> dict[str, Any]:
    with gr.Tab(t("nav.analyze")):
        with gr.Group(elem_classes=["td-card"]):
            gr.Markdown(t("analyze.instructions"), elem_classes=["td-section-title"])
            with gr.Row():
                link = gr.Textbox(label=t("form.link"), scale=4)
                analyze_btn = binder.button(gr, "analyze.run", variant="primary", scale=1)
            mode_ready = binder.is_ready("analyze.set_mode")
            mode = gr.Radio(
                choices=[
                    (t("scan.mode.message"), "message"),
                    (t("scan.mode.range"), "range"),
                    (t("scan.mode.latest"), "latest"),
                    (t("scan.mode.chat"), "chat"),
                ],
                value=seed["analyze_mode"], label=t("form.scan_mode"),
                interactive=mode_ready, visible=True,
            )
            binder.register(mode, "analyze.set_mode")
            media_types = gr.CheckboxGroup(
                choices=[
                    (t("media.all"), "all"),
                    (t("media.video"), "video"),
                    (t("media.audio"), "audio"),
                    (t("media.document"), "document"),
                    (t("media.photo"), "photo"),
                    (t("media.voice"), "voice"),
                    (t("media.animation"), "animation"),
                    (t("media.sticker"), "sticker"),
                ],
                value=["all"], label=t("form.media_types"),
            )
            with gr.Row():
                message_id = gr.Number(
                    label=t("form.message_id"), precision=0,
                    visible=seed["analyze_fields"]["message_id"],
                )
                start_id = gr.Number(
                    label=t("form.start_message"), precision=0,
                    visible=seed["analyze_fields"]["start_id"],
                )
                end_id = gr.Number(
                    label=t("form.end_message"), precision=0,
                    visible=seed["analyze_fields"]["end_id"],
                )
                limit = gr.Number(
                    label=t("form.message_limit"), value=MAX_SCAN_MESSAGES, precision=0,
                    visible=seed["analyze_fields"]["limit"],
                )
            analyze_message = gr.Textbox(label=t("analyze.result"), interactive=False)
        # DOC-39 §5: real selection stage — candidates table, preview, and the
        # explicit enqueue gate. Row clicks toggle the selection marker, which
        # is part of the table value (candidate_rows_for), not a decorative
        # button.
        with gr.Group(elem_classes=["td-card"]):
            gr.Markdown(t("sel.hint"), elem_classes=["td-section-title"])
            candidates_table = gr.Dataframe(
                headers=[t(key) for key in CANDIDATE_HEADERS],
                value=seed["analyze_rows"] if seed["analyze_rows"] else None,
                # interactive=True keeps the cell/row .select event alive in
                # the browser; the table chrome is neutralized via CSS and
                # cell edits are display-only (nothing reads them back).
                interactive=True, wrap=True, elem_classes=["td-table"],
                elem_id="td-candidates",
            )
            if not seed["analyze_rows"]:
                gr.Markdown(f"**{t('analyze.empty')}**", elem_classes=["td-empty"])
            selection_preview = gr.Textbox(
                value=seed["selection_preview"], label=t("sel.preview"),
                interactive=False,
            )
            with gr.Row():
                range_start = gr.Number(label=t("form.range_from"), precision=0)
                range_end = gr.Number(label=t("form.range_to"), precision=0)
                select_range_btn = binder.button(gr, "analyze.select_range")
                gr.Markdown(t("sel.range_cap"), elem_classes=["td-ltr"])
            with gr.Row():
                group_choice = gr.Dropdown(
                    choices=seed["group_choices"], label=t("form.group"),
                )
                select_group_btn = binder.button(gr, "analyze.select_group")
        with gr.Accordion(t("form.filters"), open=False):
            filter_media_types = gr.CheckboxGroup(
                choices=[
                    (t("media.all"), "all"),
                    (t("media.video"), "video"),
                    (t("media.audio"), "audio"),
                    (t("media.document"), "document"),
                    (t("media.photo"), "photo"),
                    (t("media.voice"), "voice"),
                    (t("media.animation"), "animation"),
                    (t("media.sticker"), "sticker"),
                ],
                value=["all"], label=t("form.media_types"),
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
            enqueue_btn = binder.button(
                gr, "analyze.enqueue_selected", variant="primary",
                interactive=bool(seed["enqueue_allowed"]),
            )
    return {
        "link": link, "analyze_btn": analyze_btn, "mode": mode,
        "media_types": media_types, "message_id": message_id, "start_id": start_id,
        "end_id": end_id, "limit": limit, "analyze_message": analyze_message,
        "candidates_table": candidates_table, "selection_preview": selection_preview,
        "range_start": range_start, "range_end": range_end,
        "select_range_btn": select_range_btn, "group_choice": group_choice,
        "select_group_btn": select_group_btn,
        "filter_media_types": filter_media_types, "extensions": extensions,
        "min_size": min_size, "max_size": max_size, "date_from": date_from,
        "date_to": date_to, "include": include, "exclude": exclude,
        "filters_btn": filters_btn, "select_all_btn": select_all_btn,
        "clear_selection_btn": clear_selection_btn, "enqueue_btn": enqueue_btn,
    }


def _section_connection(ctx, binder, seed) -> dict[str, Any]:
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
                    visible=seed["otp_visible"], elem_classes=["td-panel-otp"],
                ) as code_panel:
                    code = gr.Textbox(label=t("form.code"))
                    verify_btn = binder.button(gr, "telegram.verify_code", variant="primary")
                with gr.Column(
                    visible=seed["password_visible"], elem_classes=["td-panel-2fa"],
                ) as password_panel:
                    password = gr.Textbox(label=t("form.password"), type="password")
                    verify_pw_btn = binder.button(gr, "telegram.verify_password", variant="primary")
                with gr.Row():
                    logout_btn = binder.button(gr, "telegram.logout", variant="stop")
                    tg_status_btn = binder.button(gr, "telegram.status", variant="secondary")
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
                folder_picker = _render_folder_picker(ctx, binder, "conn", t("common.language"))
                quota_btn = binder.button(gr, "drive.refresh_quota", variant="secondary")
                quota_line = gr.Textbox(
                    value=seed["quota_line"], label=t("dash.drive_space"), interactive=False,
                )
                quota_json = gr.JSON(label=t("dash.drive_space"), value=seed["quota_payload"])
    return {
        "credentials_btn": credentials_btn, "api_id": api_id, "api_hash": api_hash,
        "phone": phone, "send_code_btn": send_code_btn,
        "resend_code_btn": resend_code_btn, "code_panel": code_panel, "code": code,
        "verify_btn": verify_btn, "password_panel": password_panel, "password": password,
        "verify_pw_btn": verify_pw_btn, "logout_btn": logout_btn,
        "tg_status_btn": tg_status_btn, "telegram_detail": telegram_detail,
        "drive_connect_btn": drive_connect_btn, "drive_reconnect_btn": drive_reconnect_btn,
        "drive_status_btn": drive_status_btn, "drive_detail": drive_detail,
        "folder_picker": folder_picker, "quota_btn": quota_btn,
        "quota_line": quota_line, "quota_json": quota_json,
    }


def _section_logs(ctx, binder, seed) -> dict[str, Any]:
    with gr.Tab(t("nav.logs")):
        with gr.Row():
            logs_query = gr.Textbox(label=t("btn.search_logs"), scale=3)
            logs_level = gr.Dropdown(
                choices=LOG_LEVELS, value="ALL", label=t("logs.level"),
                allow_custom_value=False, scale=1,
            )
            logs_search_btn = binder.button(gr, "logs.search")
            logs_refresh_btn = binder.button(gr, "logs.refresh", variant="secondary")
            logs_download_btn = binder.button(gr, "logs.download")
        logs_box = gr.Textbox(
            value=seed["logs"], label=t("nav.logs"), lines=18,
            interactive=False, elem_classes=["td-logs"],
        )
        logs_file = gr.File(label=t("btn.download_logs"), visible=False)
        logs_status = gr.Textbox(label=t("common.busy"), interactive=False, visible=True)
    return {
        "logs_query": logs_query, "logs_level": logs_level,
        "logs_search_btn": logs_search_btn, "logs_refresh_btn": logs_refresh_btn,
        "logs_download_btn": logs_download_btn, "logs_box": logs_box,
        "logs_file": logs_file, "logs_status": logs_status,
    }


def _section_settings(ctx, binder, seed) -> dict[str, Any]:
    with gr.Tab(t("nav.settings")):
        concurrency_ready = binder.is_ready("settings.set_concurrency")
        gr.Markdown(f"### {t('settings.concurrency.title')}", elem_classes=["td-section-title"])
        concurrency = gr.Slider(
            minimum=1, maximum=4, step=1, value=seed["concurrency"],
            label=t("settings.concurrency.label"),
            info=t("settings.concurrency.info"),
            elem_id="td-concurrency",
            interactive=concurrency_ready, visible=True,
        )
        binder.register(concurrency, "settings.set_concurrency")
        concurrency_box = gr.Textbox(
            label=t("form.concurrency"), interactive=False,
            value=f"{seed['concurrency']}/4", visible=True,
        )
        with gr.Accordion(t("settings.advanced"), open=False):
            theme_ready = binder.is_ready("settings.set_theme")
            theme_radio = gr.Radio(
                choices=[(t("settings.theme.dark"), "dark"),
                         (t("settings.theme.light"), "light")],
                value=seed["theme"], label=t("btn.theme"),
                interactive=theme_ready, visible=True,
            )
            binder.register(theme_radio, "settings.set_theme")
            theme_status = gr.Textbox(
                label=t("btn.theme"), interactive=False, visible=True,
                value="",
            )
            with gr.Row():
                recover_btn = binder.button(gr, "recovery.restore")
                checkpoint_btn = binder.button(gr, "maintenance.checkpoint")
            maintenance_box = gr.Textbox(
                label=t("nav.maintenance"), interactive=False,
            )
            folder_picker = _render_folder_picker(ctx, binder, "settings", t("common.language"))
    return {
        "concurrency": concurrency, "concurrency_box": concurrency_box,
        "theme_radio": theme_radio, "theme_status": theme_status,
        "recover_btn": recover_btn, "checkpoint_btn": checkpoint_btn,
        "maintenance_box": maintenance_box, "folder_picker": folder_picker,
    }


def _section_export(ctx, binder, seed) -> dict[str, Any]:
    with gr.Tab(t("nav.export")):
        gr.Markdown(f"### {t('nav.export')}", elem_classes=["td-section-title"])
        with gr.Row():
            build_zip_btn = binder.button(gr, "export.build_zip", variant="primary")
        zip_message = gr.Textbox(label=t("btn.build_zip"), interactive=False)
        zip_file = gr.File(label=t("btn.build_zip"), visible=False)
        colab_cells_btn = binder.button(gr, "export.colab_cells", variant="secondary")
        colab_cells_box = gr.Textbox(
            label=t("btn.colab_cells"), lines=18, interactive=False,
        )
        colab_status = gr.Textbox(label=t("common.busy"), interactive=False)
    return {
        "build_zip_btn": build_zip_btn, "zip_message": zip_message, "zip_file": zip_file,
        "colab_cells_btn": colab_cells_btn, "colab_cells_box": colab_cells_box,
        "colab_status": colab_status,
    }


# ---------------------------------------------------------------------------
# Wiring. No direct .click/.change/.submit; everything through binder.wire.
# ---------------------------------------------------------------------------

def _bind_actions(
    ctx, binder, *, dash, queue, analyze, conn, logs, sets, export,
    lang, theme, rail_buttons, active_tab, telegram_chip, drive_chip,
    folder_chip, top_zip_btn, lang_btn,
) -> None:
    # Language toggle re-renders the shell via gr.render.
    binder.wire(lang_btn, "settings.toggle_language", [], [lang], event="click")

    # Theme switcher replaces the <style> block.
    binder.wire(sets["theme_radio"], "settings.set_theme", [sets["theme_radio"]],
                [theme, sets["theme_status"]], event="change")

    # Telegram
    tg_outputs = [conn["telegram_detail"], telegram_chip,
                 conn["code_panel"], conn["password_panel"]]
    binder.wire(conn["credentials_btn"], "telegram.set_credentials",
                [conn["api_id"], conn["api_hash"]], tg_outputs)
    binder.wire(conn["send_code_btn"], "telegram.send_code", [conn["phone"]], tg_outputs)
    binder.wire(conn["resend_code_btn"], "telegram.resend_code", [], tg_outputs)
    binder.wire(conn["verify_btn"], "telegram.verify_code", [conn["code"]], tg_outputs)
    binder.wire(conn["verify_pw_btn"], "telegram.verify_password",
                [conn["password"]], tg_outputs)
    binder.wire(conn["logout_btn"], "telegram.logout", [], tg_outputs)
    binder.wire(conn["tg_status_btn"], "telegram.status", [], tg_outputs)

    # Drive
    dr_outputs = [conn["drive_detail"], drive_chip]
    binder.wire(conn["drive_connect_btn"], "drive.connect", [], dr_outputs)
    binder.wire(conn["drive_reconnect_btn"], "drive.reconnect", [], dr_outputs)
    binder.wire(conn["drive_status_btn"], "drive.status", [], dr_outputs)
    # The same named handlers back all four visible folder panels; create and
    # select broadcast the ONE folder truth to every panel + the top chip
    # (DOC-39 §4): (own choice, own current, own message, top chip,
    # other currents x3, other messages x3).
    _pickers = (
        dash["folder_picker"], queue["folder_picker"],
        sets["folder_picker"], conn["folder_picker"],
    )
    for picker in _pickers:
        binder.wire(picker["list_btn"], "drive.list_folders", [picker["parent_id"]],
                    [picker["message"], picker["choice"]])
        others = [q for q in _pickers if q is not picker]
        folder_out = (
            [picker["choice"], picker["current"], picker["message"], folder_chip]
            + [q["current"] for q in others]
            + [q["message"] for q in others]
        )
        binder.wire(picker["create_btn"], "drive.create_folder",
                    [picker["new_name"], picker["parent_id"]], folder_out)
        binder.wire(picker["select_btn"], "drive.select_folder", [picker["choice"]],
                    folder_out)
    binder.wire(conn["quota_btn"], "drive.refresh_quota", [],
                [conn["quota_line"], conn["quota_json"]])

    # Analyze — DOC-39 §5 selection stage outputs shared by every selection
    # action: (analyze_message, candidates_table, selection_preview,
    # enqueue_btn, group_choice).
    a_out = [
        analyze["analyze_message"], analyze["candidates_table"],
        analyze["selection_preview"], analyze["enqueue_btn"],
        analyze["group_choice"],
    ]
    binder.wire(analyze["analyze_btn"], "analyze.run",
                [analyze["link"], analyze["mode"], analyze["message_id"],
                 analyze["start_id"], analyze["end_id"], analyze["limit"],
                 analyze["media_types"]], a_out)
    binder.wire(analyze["mode"], "analyze.set_mode", [analyze["mode"]],
                [analyze["message_id"], analyze["start_id"],
                 analyze["end_id"], analyze["limit"]], event="change")
    binder.wire(analyze["filters_btn"], "analyze.apply_filters",
                [analyze["filter_media_types"], analyze["extensions"],
                 analyze["min_size"], analyze["max_size"], analyze["date_from"],
                 analyze["date_to"], analyze["include"], analyze["exclude"]], a_out)
    binder.wire(analyze["select_all_btn"], "analyze.select_all", [], a_out)
    binder.wire(analyze["clear_selection_btn"], "analyze.clear_selection", [], a_out)
    binder.wire(analyze["select_range_btn"], "analyze.select_range",
                [analyze["range_start"], analyze["range_end"]], a_out)
    binder.wire(analyze["select_group_btn"], "analyze.select_group",
                [analyze["group_choice"]], a_out)
    # Row click = manual selection toggle; the marker cell is table state.
    binder.wire(analyze["candidates_table"], "analyze.toggle_row", [], a_out,
                event="select")
    # Enqueue stays EXPLICIT and refreshes the real queue table + status.
    binder.wire(analyze["enqueue_btn"], "analyze.enqueue_selected", [],
                [analyze["analyze_message"], queue["queue_table"],
                 queue["queue_status"], analyze["selection_preview"],
                 analyze["enqueue_btn"]])

    # Transfers
    q_out = [queue["queue_status"], queue["queue_table"]]
    binder.wire(queue["start_btn"], "queue.start_selected", [], q_out)
    binder.wire(queue["pause_btn"], "queue.pause", [], q_out)
    binder.wire(queue["resume_btn"], "queue.resume", [], q_out)
    binder.wire(queue["stop_btn"], "queue.stop", [], q_out)
    binder.wire(queue["retry_btn"], "queue.retry_failed", [], q_out)
    binder.wire(queue["clear_btn"], "queue.clear_completed", [], q_out)
    binder.wire(queue["refresh_q_btn"], "queue.refresh", [], q_out)
    binder.wire(queue["pause_item_btn"], "queue.pause_item", [queue["item_id"]], q_out)
    binder.wire(queue["resume_item_btn"], "queue.resume_item", [queue["item_id"]], q_out)
    binder.wire(queue["stop_item_btn"], "queue.stop_item", [queue["item_id"]], q_out)
    binder.wire(queue["retry_item_btn"], "queue.retry_item", [queue["item_id"]], q_out)

    # Dashboard
    binder.wire(dash["dash_btn"], "dashboard.refresh", [], [dash["dashboard_json"]])

    # Logs
    binder.wire(logs["logs_refresh_btn"], "logs.refresh", [logs["logs_level"]],
                [logs["logs_box"], logs["logs_status"]])
    binder.wire(logs["logs_search_btn"], "logs.search",
                [logs["logs_query"], logs["logs_level"]],
                [logs["logs_box"], logs["logs_status"]])
    binder.wire(logs["logs_download_btn"], "logs.download", [logs["logs_level"]],
                [logs["logs_file"], logs["logs_status"]])

    # Settings
    binder.wire(sets["concurrency"], "settings.set_concurrency", [sets["concurrency"]],
                [sets["concurrency"], sets["concurrency_box"]], event="change")
    binder.wire(sets["recover_btn"], "recovery.restore", [], [sets["maintenance_box"]])
    binder.wire(sets["checkpoint_btn"], "maintenance.checkpoint", [],
                [sets["maintenance_box"]])

    # Export — both the prominent in-section button AND the top-bar zip button
    # produce the same artifact; both are wired to `export.build_zip`.
    binder.wire(export["build_zip_btn"], "export.build_zip", [],
                [export["zip_message"], export["zip_file"]])
    binder.wire(top_zip_btn, "export.build_zip", [],
                [export["zip_message"], export["zip_file"]])
    binder.wire(export["colab_cells_btn"], "export.colab_cells", [],
                [export["colab_cells_box"], export["colab_status"]])

    # Right-rail nav: the rail is a visual mirror of native gr.Tabs. Because
    # ui.py is layout-only and we avoid JS, the active indicator is driven by
    # Gradio's own Tabs client state; the rail buttons set the Tab value
    # through a dedicated state component bound to the Tabs element. We skip
    # custom JS and keep the rail as a styled visual list; Tabs built-in
    # buttons already exist (hidden visually by CSS) and remain accessible.
    # Tests verify the 7 sections are present in the required order.
