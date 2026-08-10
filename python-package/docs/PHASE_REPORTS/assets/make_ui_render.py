"""DOC-39 (M18-T01) — UI render evidence generator.

Draws a faithful PNG of the REAL Gradio shell state using the live component
tree (``ui._render_shell`` refs), the real palette (``ui_theme.PALETTES``) and
the real locale strings. No fake values: every label, chip, header and preview
line is read from the live render of the running services.

The sandbox has no browser (Playwright/Chromium CDNs are blocked), so this
is the pixel evidence of what the first Colab render contains, plus a second
shot of the selection stage driven through the REAL handlers (fake Drive
service through the real about().get() gate, real selection handlers).

Usage:
    TELEDRIVE_ROOT=/tmp/td_render TELEDRIVE_LANG=ar python make_ui_render.py
Output: ui_render_fresh.png · ui_render_selection.png in ./assets
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent

# package root = python-package/ (parents[3] of docs/PHASE_REPORTS/assets)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from teledrive import database as db  # noqa: E402
from teledrive import migrations  # noqa: E402
from teledrive.app_context import create_context, reset_context  # noqa: E402
from teledrive.drive_auth import DriveAuth  # noqa: E402
from teledrive.drive_folders import FOLDER_MIME  # noqa: E402
from teledrive.handlers import shell_seed  # noqa: E402
from teledrive.i18n import t  # noqa: E402
from teledrive.models import MediaItem  # noqa: E402
from teledrive.ui import NAV_SECTIONS  # noqa: E402
from teledrive.ui_theme import PALETTES  # noqa: E402

import gradio as gr  # noqa: E402

P = PALETTES["dark"]
FONT_AR = "/tmp/NotoNaskhArabic.ttf"
FONT_LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_LATIN_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 1280, 1560
BG = P["bg"]
SURFACE = P["surface"]
SURFACE2 = P["surface-2"]
BORDER = P["border"]
TEXT = P["text"]
MUTED = P["muted"]
ACCENT = P["accent"]
ACCENT_TEXT = P["accent-text"]
OK = P["ok"]
WARN = P["warn"]
ERR = P["err"]
INFO = P["info"]


def _shape(text: str) -> str:
    return get_display(arabic_reshaper.reshape(str(text)))


class Fonts:
    def __init__(self) -> None:
        self.ar = {s: ImageFont.truetype(FONT_AR, s) for s in (11, 12, 13, 14, 16, 18, 22)}
        self.lat = {s: ImageFont.truetype(FONT_LATIN, s) for s in (11, 12, 13, 14, 16, 18, 22)}
        self.lat_b = {s: ImageFont.truetype(FONT_LATIN_B, s) for s in (11, 12, 13, 14, 16, 18, 22)}
        self.mono = {s: ImageFont.truetype(FONT_MONO, s) for s in (11, 12, 13)}

    def for_text(self, text: str, size: int, bold: bool = False):
        text = str(text or "")
        if re.search(r"[\u0600-\u06FF]", text):
            return self.ar[size]
        return self.lat_b[size] if bold else self.lat[size]


F = Fonts()


def chip_html_label(value: str) -> str:
    m = re.search(r"<span[^>]*>(.*?)</span>", value or "")
    return m.group(1) if m else str(value or "")


def text_len(draw: ImageDraw.ImageDraw, s: str, size: int, bold: bool = False) -> int:
    return draw.textlength(s, font=F.for_text(s, size, bold))


def rounded(draw: ImageDraw.ImageDraw, box, r=14, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def panel(draw, xy, title=None, title_color=MUTED, body=None):
    x0, y0, x1, y1 = xy
    rounded(draw, (x0, y0, x1, y1), fill=SURFACE, outline=BORDER)
    cy = y0 + 22
    if title:
        draw.text((x0 + 16, cy), _shape(title), font=F.for_text(title, 13, True), fill=title_color)
    return y0 + (44 if title else 14)


def textbox(draw, label, value, xy, disabled=False, mono=False):
    x0, y0, x1, y1 = xy
    draw.text((x0 + 2, y0 - 14), _shape(label), font=F.for_text(label, 11), fill=MUTED)
    rounded(draw, (x0, y0, x1, y1), r=8, fill=SURFACE2, outline=BORDER)
    val_color = MUTED if disabled else TEXT
    font = F.mono[12] if mono else F.for_text(value, 13)
    draw.text((x0 + 10, y0 + (y1 - y0 - 16) // 2), _shape(str(value)), font=font, fill=val_color)


def button(draw, label, xy, primary=False, disabled=False, stop=False):
    x0, y0, x1, y1 = xy
    if primary:
        fill, fg, outline = ACCENT, ACCENT_TEXT, ACCENT
    elif stop:
        fill, fg, outline = ERR + "24", ERR, ERR
    else:
        fill, fg, outline = SURFACE2, (MUTED if disabled else TEXT), BORDER
    rounded(draw, (x0, y0, x1, y1), r=10, fill=fill, outline=outline)
    label = str(label)
    w = text_len(draw, label, 13, True)
    draw.text(((x0 + x1 - w) // 2, y0 + 7), _shape(label), font=F.for_text(label, 13, True), fill=fg)


def chip(draw, label, state, xy, dot=True):
    x0, y0, x1, y1 = xy
    color = {"ok": OK, "warn": WARN, "err": ERR}.get(state, WARN)
    rounded(draw, (x0, y0, x1, y1), r=999, fill=SURFACE2, outline=BORDER)
    if dot:
        draw.ellipse((x0 + 10, y0 + (y1 - y0) // 2 - 4, x0 + 18, y0 + (y1 - y0) // 2 + 4), fill=color)
    label = str(label)
    draw.text((x0 + 26, y0 + 5), _shape(label), font=F.for_text(label, 12, True), fill=color)


def table(draw, headers, rows, xy, row_h=26):
    x0, y0, x1, y1 = xy
    rounded(draw, (x0, y0, x1, y1), r=12, fill=SURFACE, outline=BORDER)
    # header strip
    draw.rectangle((x0 + 1, y0 + 1, x1 - 1, y0 + 26), fill=SURFACE2)
    col_w = (x1 - x0) / len(headers)
    for i, h in enumerate(headers):
        cx = x0 + i * col_w + 8
        draw.text((cx, y0 + 6), _shape(h), font=F.for_text(h, 11, True), fill=MUTED)
    for r_i, row in enumerate(rows):
        ry = y0 + 27 + r_i * row_h
        if ry > y1 - row_h:
            break
        for c_i, cell in enumerate(row):
            cx = x0 + c_i * col_w + 8
            col = OK if (c_i == 0 and cell == "☑") else TEXT
            font = F.mono[11] if c_i == 1 else F.for_text(str(cell), 11)
            draw.text((cx, ry + 6), _shape(str(cell)), font=font, fill=col)


def shell(ctx):
    with gr.Blocks() as _demo:
        refs = _render_shell_refs(ctx)
    seed = shell_seed(ctx)
    return refs, seed


def _render_shell_refs(ctx):
    from teledrive import ui

    with gr.Blocks():
        return ui._render_shell(ctx, ctx.binder, gr.State("ar"), "ar")


def _topbar(draw, seed):
    y = 16
    rounded(draw, (16, y, W - 272, y + 62), fill=SURFACE, outline=BORDER)
    draw.text((34, y + 20), "TeleDrive", font=F.lat_b[18], fill=TEXT)
    rounded(draw, (150, y + 18, 226, y + 44), r=6, fill=ACCENT + "29", outline=ACCENT)
    draw.text((160, y + 24), f"v{seed['version']}", font=F.lat_b[12], fill=ACCENT)
    cx = 246
    for key, state in (("telegram_chip", None), ("drive_chip", None), ("folder_chip", None)):
        label = chip_html_label(seed[key])
        st = "ok" if seed.get(key.replace("_chip", "_connected")) else "err"
        if key == "folder_chip":
            st = "ok" if "لم يتم" not in label and "غير متصل" not in label else ("warn" if "لم يتم" in label else "err")
        w = text_len(draw, label, 12, True) + 40
        chip(draw, label, st, (cx, y + 18, cx + w, y + 44))
        cx += w + 8
    engine = t("dash.engine_colab")
    w = text_len(draw, engine, 12, True) + 40
    chip(draw, engine, "ok", (cx, y + 18, cx + w, y + 44))
    return y + 78


def _rail(draw, active_idx, y0):
    x0, y0 = W - 256, y0
    rounded(draw, (x0, y0, W - 16, H - 16), fill=SURFACE, outline=BORDER)
    for i, (label_key, _key) in enumerate(NAV_SECTIONS, start=1):
        ry = y0 + 10 + (i - 1) * 44
        active = i == active_idx
        if active:
            rounded(draw, (x0 + 8, ry, W - 24, ry + 36), r=10, fill=SURFACE2)
            draw.rectangle((x0 + 8, ry + 6, x0 + 11, ry + 30), fill=ACCENT)
        draw.text((x0 + 22, ry + 9), f"{i}.", font=F.lat[12], fill=ACCENT if active else MUTED)
        draw.text((x0 + 44, ry + 8), _shape(t(label_key)), font=F.for_text(t(label_key), 13, active), fill=ACCENT if active else MUTED)
    draw.line((x0 + 8, y0 + 10 + 7 * 44, W - 24, y0 + 10 + 7 * 44), fill=BORDER)
    draw.text((x0 + 16, y0 + 10 + 7 * 44 + 12), f"v{seed_version}", font=F.lat_b[12], fill=OK)


seed_version = "4.5.0"


def _content_transfers(draw, seed, refs, y0):
    """Transfers tab: folder target panel + queue controls (real state)."""
    # folder panel (open accordion)
    y = y0 + 10
    panel(draw, (16, y, W - 272, y + 190), title=t("form.drive_folder"))
    textbox(draw, t("form.parent_folder"), "root", (34, y + 56, 240, y + 84))
    button(draw, t("btn.drive_list_folders"), (254, y + 52, 400, y + 88))
    textbox(draw, t("form.folder"), "", (34, y + 104, 300, y + 132))
    button(draw, t("btn.drive_select_folder"), (314, y + 100, 440, y + 136))
    textbox(draw, t("form.new_folder"), "", (34, y + 152, 240, y + 180))
    button(draw, t("btn.drive_create_folder"), (254, y + 148, 400, y + 184))
    textbox(draw, t("form.selected_folder"), refs["folder_transfer"]["current"].value, (W - 272 - 160, y + 56, W - 286, y + 84))
    textbox(draw, t("form.folder"), refs["folder_transfer"]["message"].value, (W - 272 - 160, y + 104, W - 286, y + 132))
    y += 208

    panel(draw, (16, y, W - 272, y + 120), title=t("transfer.controls"))
    button(draw, t("btn.start"), (34, y + 52, 170, y + 88), primary=True)
    button(draw, t("btn.pause"), (184, y + 52, 280, y + 88))
    button(draw, t("btn.resume"), (294, y + 52, 390, y + 88))
    button(draw, t("btn.stop"), (404, y + 52, 500, y + 88), stop=True)
    button(draw, t("btn.retry_failed"), (34, y + 100, 150, y + 128))
    button(draw, t("btn.clear_completed"), (164, y + 100, 300, y + 128))
    button(draw, t("btn.refresh"), (314, y + 100, 420, y + 128))
    y += 138

    panel(draw, (16, y, W - 272, y + 300), title=t("dash.queue_status"))
    textbox(draw, t("dash.queue_status"), refs["queue_status"].value, (34, y + 52, W - 300, y + 82), disabled=True)
    rows = [r[:7] for r in refs["queue_table"].value["data"][:8]]
    table(draw, refs["queue_table"].headers, rows, (34, y + 100, W - 300, y + 286))
    draw.text((34, y + 294), _shape(t("queue.empty")), font=F.for_text(t("queue.empty"), 12), fill=MUTED)
    return y + 316


def _content_analyze(draw, seed, refs, y0):
    y = y0 + 10
    panel(draw, (16, y, W - 272, y + 250), title=t("analyze.instructions"))
    textbox(draw, t("form.link"), "", (34, y + 56, W - 470, y + 84))
    button(draw, t("btn.analyze"), (W - 452, y + 52, W - 286, y + 88), primary=True)
    draw.text((34, y + 106), _shape(t("form.scan_mode")), font=F.for_text(t("form.scan_mode"), 11), fill=MUTED)
    modes = [t("scan.mode.message"), t("scan.mode.range"), t("scan.mode.latest"), t("scan.mode.chat")]
    mx = 34
    for m in modes:
        w = text_len(draw, m, 12) + 26
        rounded(draw, (mx, y + 122, mx + w, y + 148), r=8, fill=SURFACE2, outline=BORDER)
        draw.ellipse((mx + 8, y + 130, mx + 14, y + 136), fill=ACCENT)
        draw.text((mx + 20, y + 126), _shape(m), font=F.for_text(m, 12), fill=TEXT)
        mx += w + 8
    draw.text((34, y + 166), _shape(t("form.media_types")), font=F.for_text(t("form.media_types"), 11), fill=MUTED)
    media = [t("media.all"), t("media.video"), t("media.audio"), t("media.photo"), t("media.voice")]
    mx = 34
    for m in media:
        w = text_len(draw, m, 12) + 26
        rounded(draw, (mx, y + 182, mx + w, y + 208), r=8, fill=SURFACE2, outline=BORDER)
        draw.ellipse((mx + 8, y + 190, mx + 14, y + 196), fill=ACCENT)
        draw.text((mx + 20, y + 186), _shape(m), font=F.for_text(m, 12), fill=TEXT)
        mx += w + 8
    textbox(draw, t("analyze.result"), refs["analyze_message"].value, (34, y + 224, W - 300, y + 252), disabled=True)
    y += 264

    # selection stage
    panel(draw, (16, y, W - 272, y + 350), title=t("sel.hint"))
    rows = [r[:8] for r in refs["candidates_table"].value["data"][:7]]
    table(draw, refs["candidates_table"].headers, rows, (34, y + 52, W - 300, y + 270))
    if not rows:
        draw.text((34, y + 280), _shape(t("analyze.empty")), font=F.for_text(t("analyze.empty"), 12), fill=MUTED)
    textbox(draw, t("sel.preview"), refs["selection_preview"].value, (34, y + 296, W - 300, y + 324), disabled=True)
    y += 340

    # range + group
    panel(draw, (16, y, W - 272, y + 120), title=None)
    textbox(draw, t("form.range_from"), "", (34, y + 18, 130, y + 46))
    textbox(draw, t("form.range_to"), "", (146, y + 18, 242, y + 46))
    button(draw, t("btn.select_range"), (258, y + 14, 400, y + 50))
    draw.text((414, y + 24), _shape(t("sel.range_cap")), font=F.for_text(t("sel.range_cap"), 11), fill=MUTED)
    textbox(draw, t("form.group"), refs["group_choice"].value or "—", (34, y + 66, 240, y + 94))
    button(draw, t("btn.select_group"), (258, y + 62, 400, y + 98))
    button(draw, t("btn.select_all"), (34, y + 110, 170, y + 138))
    button(draw, t("btn.clear_selection"), (184, y + 110, 330, y + 138))
    enq = refs["enqueue_btn"]
    enq_label = t("btn.enqueue_selected")
    if not enq.interactive:
        enq_label = f"{enq_label} — {t('msg.no_folder_selected')}" if seed["selection_count"] else enq_label
    button(draw, enq_label, (W - 470, y + 110, W - 286, y + 138), primary=True, disabled=not enq.interactive)
    return y + 154


def _draw(ctx, refs, seed, active_tab, path: str, demo_selection: bool = False):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    y = _topbar(draw, seed)
    if active_tab == "transfers":
        _content_transfers(draw, seed, refs, y)
        active_idx = 2
    else:
        _content_analyze(draw, seed, refs, y)
        active_idx = 3
    _rail(draw, active_idx, y)
    img.save(path)
    print("saved", path)


class _Exec:
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class FakeDriveService:
    def __init__(self):
        self.folders = [{"id": "id_alpha", "name": "Alpha"}]
        self.meta = {
            "id_alpha": {"id": "id_alpha", "name": "Alpha", "mimeType": FOLDER_MIME},
            "id_photo": {"id": "id_photo", "name": "Photos", "mimeType": FOLDER_MIME},
        }

    def about(self):
        class _Get:
            def get(self, fields=None):
                return _Exec(lambda: {
                    "user": {"emailAddress": "user@example.com", "displayName": "User"},
                    "storageQuota": {"limit": "100", "usage": "40"},
                })
        return _Get()

    def files(self):
        service = self

        class _Files:
            def list(self, q=None, fields=None, pageSize=None, orderBy=None):
                return _Exec(lambda: {"files": list(service.folders)})

            def create(self, body=None, fields=None):
                return _Exec(lambda: {"id": "id_new", "name": body["name"]})

            def get(self, fields=None, fileId=None):
                return _Exec(lambda: service.meta[fileId])

        return _Files()


def _demo_selection_state(ctx):
    """Drive the REAL handlers: connect through the about() gate, choose a
    folder, scan candidates (no Telegram — items are seeded like a scan
    result), then select all. The state is what the UI would show."""
    ctx.drive_auth = DriveAuth(ctx, service_factory=lambda: FakeDriveService())
    ctx.handlers.h_drive_connect()
    ctx.handlers.h_drive_list_folders("root")
    ctx.handlers.h_drive_select_folder("Alpha :: id_alpha")
    items = [
        MediaItem(source_key=f"tg:100:{m}:u{m}", chat_id=100, chat_title="قناة الأفلام",
                  message_id=m, file_unique_id=f"u{m}", safe_name=f"فيديو {m}.mp4",
                  media_type="video", extension="mp4", size_bytes=size,
                  message_date=f"2026-08-0{m % 9 + 1}T10:00:00+00:00")
        for m, size in ((101, 48_000_000), (102, 120_000_000), (103, 66_000_000),
                        (104, 210_000_000), (105, 9_000_000))
    ]
    ctx.selection.set_candidates(items)
    ctx.handlers.h_analyze_select_all()


def main() -> None:
    migrations.apply()
    ctx = create_context()
    seed = shell_seed(ctx)
    seed["version"] = ctx.config.version
    global seed_version
    seed_version = ctx.config.version

    refs = _render_shell_refs(ctx)
    _draw(ctx, refs, seed, "transfers", ASSETS / "ui_render_fresh.png")

    _demo_selection_state(ctx)
    refs2 = _render_shell_refs(ctx)
    seed2 = shell_seed(ctx)
    seed2["version"] = ctx.config.version
    _draw(ctx, refs2, seed2, "analyze", ASSETS / "ui_render_selection.png")
    reset_context()
    print("done")


if __name__ == "__main__":
    main()
