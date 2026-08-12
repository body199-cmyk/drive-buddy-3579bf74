"""TeleDrive visual tokens + CSS (single source of truth for colors).

M19-T01: the palette is rebuilt around the oklch design tokens (day/night).
``ui.py`` never hardcodes a color — every hue flows from a ``--td-*`` CSS
variable defined here. Theme switching swaps the whole ``<style>`` block
returned by :func:`theme_style_block` (the existing, JS-free mechanism the
constitution endorses), so a toggle never reloads the page and never touches
runtime state.

Token map (oklch). Day is the light surface, night is NOT an inverted copy of
it — both palettes are authored independently so each contrast pair is honest:

* ``--td-primary``    — main actions only (teal).
* ``--td-primary-deep`` — pressed/brand emphasis.
* ``--td-accent``     — warm highlight (brand chip), never a CTA.
* ``--td-success``    — real success states (green).
* ``--td-danger``     — real failure states (red).
* ``--td-warn`` / ``--td-info`` — amber / cool-blue semantic accents.

A connection/success colour is ONLY ever shown from live state (Constitution
§4 / DOC-39): no chip is green before the service really reports connected.
"""
from __future__ import annotations

PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "bg": "oklch(97% 0.012 190)",
        "surface": "oklch(100% 0.008 190)",
        "surface-2": "oklch(94.5% 0.018 190)",
        "border": "oklch(87% 0.025 190)",
        "text": "oklch(24% 0.035 210)",
        "muted": "oklch(53% 0.035 210)",
        "primary": "oklch(55% 0.13 188)",
        "primary-deep": "oklch(37% 0.09 200)",
        "accent": "oklch(78% 0.13 82)",
        "accent-text": "oklch(20% 0.02 200)",
        "success": "oklch(63% 0.12 150)",
        "danger": "oklch(67% 0.13 18)",
        "warn": "oklch(72% 0.13 75)",
        "info": "oklch(60% 0.11 230)",
        "ok": "oklch(63% 0.12 150)",
        "err": "oklch(67% 0.13 18)",
        "logs-bg": "oklch(98% 0.01 190)",
        "logs-text": "oklch(30% 0.02 200)",
        "lime": "oklch(55% 0.13 188)",
    },
    "dark": {
        "bg": "oklch(17% 0.018 200)",
        "surface": "oklch(21% 0.022 200)",
        "surface-2": "oklch(25% 0.026 200)",
        "border": "oklch(35% 0.028 200)",
        "text": "oklch(93% 0.018 190)",
        "muted": "oklch(73% 0.025 190)",
        "primary": "oklch(68% 0.11 185)",
        "primary-deep": "oklch(78% 0.07 190)",
        "accent": "oklch(82% 0.10 82)",
        "accent-text": "oklch(15% 0.02 200)",
        "success": "oklch(72% 0.10 150)",
        "danger": "oklch(74% 0.10 18)",
        "warn": "oklch(80% 0.11 75)",
        "info": "oklch(72% 0.10 230)",
        "ok": "oklch(72% 0.10 150)",
        "err": "oklch(74% 0.10 18)",
        "logs-bg": "oklch(14% 0.02 200)",
        "logs-text": "oklch(88% 0.015 190)",
        "lime": "oklch(68% 0.11 185)",
    },
}


def _all_token_keys() -> tuple[str, ...]:
    return tuple(PALETTES["dark"].keys())


def theme_style_block(theme: str) -> str:
    """Return a ``<style>`` block that sets the CSS variables for a theme.

    Invalid theme names silently fall back to the persisted default (dark):
    preference-only input must never crash the UI. The block is swapped whole
    on toggle — no JS, no reload, runtime state untouched.
    """
    theme = theme if theme in PALETTES else "dark"
    p = dict(PALETTES[theme])
    # Legacy alias kept for backwards-compat tests / older handlers: lime now
    # equals the primary action colour (it was the old CTA accent).
    p.setdefault("lime", p.get("primary", PALETTES["dark"]["primary"]))
    vars_css = "\n".join(
        f"  --td-{k}: {v};" for k, v in p.items()
    )
    return (
        f'<style id="td-theme-vars" data-td-theme="{theme}">\n'
        f":root, .gradio-container {{\n{vars_css}\n}}\n"
        f"</style>"
    )


# Spacing scale (4 / 8 / 12 / 16 / 24 / 32 px) and the 44 px touch target live
# as tokens so the layout is consistent without per-component magic numbers.
BASE_CSS = """
:root, .gradio-container {
  --td-bg: oklch(17% 0.018 200);
  --td-space-1: 4px;
  --td-space-2: 8px;
  --td-space-3: 12px;
  --td-space-4: 16px;
  --td-space-5: 24px;
  --td-space-6: 32px;
  --td-touch: 44px;
  --td-radius: 14px;
  --td-radius-sm: 10px;
}
.td-root.td-rtl { direction: rtl; text-align: right; }
.td-root.td-ltr { direction: ltr; text-align: left; }

/* ---- page frame: single centered column, max ~1280px, no stray strips ---- */
.gradio-container {
  max-width: 1280px !important;
  margin: 0 auto !important;
  background: var(--td-bg) !important;
  color: var(--td-text);
  font-family: "Segoe UI", "Noto Naskh Arabic", "Noto Sans Arabic", Tahoma, Arial, sans-serif;
  --body-background-fill: var(--td-bg);
  --block-background-fill: var(--td-surface);
  --block-border-color: var(--td-border);
  --body-text-color: var(--td-text);
  --block-label-text-color: var(--td-muted);
  --block-title-text-color: var(--td-muted);
  --input-border-color: var(--td-border);
  --border-color-primary: var(--td-border);
  --color-accent: var(--td-primary);
  /* Main actions use the primary token; warm accent is for brand only. */
  --button-primary-background-fill: var(--td-primary);
  --button-primary-text-color: var(--td-accent-text);
  --button-primary-background-fill-hover: var(--td-primary-deep);
  --button-secondary-background-fill: var(--td-surface-2);
  --button-secondary-text-color: var(--td-text);
  --button-secondary-border-color: var(--td-border);
  /* Legacy lime token kept for backwards-compat tests; equals primary. */
  --td-lime: var(--td-primary);
  --td-lime-dim: color-mix(in srgb, var(--td-primary) 16%, transparent);
}
#td-root { width: 100%; }
#td-content, #td-shell, #td-shell > * { min-width: 0; }

/* ---- top status bar (NOT navigation — live state only) ---- */
.td-topbar {
  display: flex;
  align-items: center;
  gap: var(--td-space-2);
  flex-wrap: wrap;
  padding: var(--td-space-3) var(--td-space-4);
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-radius: var(--td-radius);
  margin-bottom: var(--td-space-4);
}
.td-topbar .td-brand { margin-inline-end: auto; }
.td-brand { font-size: 17px; letter-spacing: 0.3px; color: var(--td-text); margin-inline-end: auto; }
.td-brand strong { color: var(--td-text); }
.td-brand code {
  color: var(--td-primary-deep);
  background: color-mix(in srgb, var(--td-primary) 14%, transparent);
  border-radius: var(--td-space-1);
  padding: 1px 6px;
  font-size: 12px;
}
/* Chips are real styled spans, never raw textboxes. */
.td-chip-host { display: inline-flex; align-items: center; padding: 0; border: 0; background: transparent !important; }
.td-chip-host > * { margin: 0; }
.td-chip {
  border: 1px solid var(--td-border);
  border-radius: 999px;
  padding: var(--td-space-1) var(--td-space-3);
  font-size: 12px;
  font-weight: 600;
  background: var(--td-surface-2);
  color: var(--td-muted);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.td-chip::before {
  content: "";
  width: 8px; height: 8px;
  border-radius: 50%;
  background: currentColor;
}
.td-chip[data-state="ok"]   { color: var(--td-success); }
.td-chip[data-state="warn"] { color: var(--td-warn); }
.td-chip[data-state="err"]  { color: var(--td-danger); }

/* ---- single navigation bar: native Gradio tabs, restyled ---- */
#td-content .gr-tabs, #td-content .gr-tabs > div { width: 100%; }
.td-tabs .tab-nav {
  display: flex;
  flex-wrap: wrap;
  gap: var(--td-space-1);
  border-bottom: 1px solid var(--td-border) !important;
  background: var(--td-surface);
  border-radius: var(--td-radius) var(--td-radius) 0 0;
  padding: var(--td-space-2);
}
.td-tabs .tab-nav button {
  min-height: var(--td-touch);
  padding: var(--td-space-2) var(--td-space-4) !important;
  border-radius: var(--td-radius-sm) !important;
  border: 1px solid transparent !important;
  background: transparent !important;
  color: var(--td-muted) !important;
  font-weight: 600;
  font-size: 14px;
}
.td-tabs .tab-nav button:hover { background: var(--td-surface-2) !important; color: var(--td-text) !important; }
.td-tabs .tab-nav button[aria-selected="true"],
.td-tabs .tab-nav button.selected {
  color: var(--td-primary) !important;
  background: color-mix(in srgb, var(--td-primary) 12%, transparent) !important;
  box-shadow: inset 0 -3px 0 0 var(--td-primary);
}

/* ---- cards / sections (flat — no nested cards, no colored side rules) ---- */
.td-card {
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-radius: var(--td-radius);
  padding: var(--td-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--td-space-3);
  width: 100%;
  box-sizing: border-box;
}
.td-section-title { color: var(--td-muted); font-size: 14px; font-weight: 700; margin: 0; }
.td-zone-title { color: var(--td-text); font-size: 16px; font-weight: 800; margin: 0 0 var(--td-space-1) 0; }
.td-zone-hint  { color: var(--td-muted); font-size: 12px; font-weight: 500; margin: 0 0 var(--td-space-2) 0; }

/* ---- consistent widths: tables and panels never stretch arbitrarily ---- */
.td-table, .td-table table, .td-table .table-wrap { width: 100% !important; }
.td-tabs { width: 100%; }
#td-content .gr-form, #td-content .gr-box, #td-content .gr-group { max-width: none; }
.td-preview { font-variant-numeric: tabular-nums; }

/* ---- focus ring uses the primary token, never a default blue ---- */
button:focus-visible, input:focus-visible, textarea:focus-visible, select:focus-visible,
.gradio-container .gr-text-input:focus, .gradio-container .gr-number-input:focus {
  outline: 2px solid var(--td-primary) !important;
  outline-offset: 1px;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--td-primary) 22%, transparent) !important;
}

/* ---- candidates table: row clicks are selection toggles ---- */
#td-candidates table td { cursor: pointer; }
#td-candidates table td:hover { background: color-mix(in srgb, var(--td-primary) 10%, var(--td-surface-2)); }
#td-candidates [aria-label="Add row"], #td-candidates [aria-label="Delete row"] { display: none !important; }

/* ---- buttons: primary = main actions, stop = danger wash ---- */
.gradio-container button { border-radius: var(--td-radius-sm) !important; min-height: var(--td-touch); }
.gradio-container .gr-button-primary {
  background: var(--td-primary) !important;
  border-color: var(--td-primary) !important;
  color: var(--td-accent-text) !important;
  font-weight: 700;
}
.gradio-container .gr-button-primary:hover { background: var(--td-primary-deep) !important; }
.td-stop, .td-stop button, button.td-stop {
  background: color-mix(in srgb, var(--td-danger) 14%, transparent) !important;
  border-color: var(--td-danger) !important;
  color: var(--td-danger) !important;
  font-weight: 700;
}

/* ---- semantic panels (OTP / 2FA): flat surfaces, no side bars ---- */
.td-panel-otp, .td-panel-2fa {
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-radius: var(--td-radius);
  padding: var(--td-space-3) var(--td-space-4);
}
.td-panel-otp { box-shadow: inset 0 2px 0 0 var(--td-info); }
.td-panel-2fa { box-shadow: inset 0 2px 0 0 var(--td-warn); }

/* ---- tables ---- */
.td-table { border: 1px solid var(--td-border); border-radius: var(--td-radius); overflow: hidden; }
.td-table table { background: var(--td-surface); }
.td-table th { background: var(--td-surface-2) !important; color: var(--td-muted) !important; font-weight: 700; }
.td-table td { color: var(--td-text); border-color: var(--td-border) !important; }
.td-table tr:hover td { background: var(--td-surface-2); }

/* ---- logs pane: monospace, LTR even inside RTL shells ---- */
.td-logs textarea, .td-logs .gradio-textbox {
  font-family: "Cascadia Mono", "Fira Code", Consolas, monospace !important;
  font-size: 12px !important;
  background: var(--td-logs-bg) !important;
  color: var(--td-logs-text) !important;
  border: 1px solid var(--td-border) !important;
  border-radius: var(--td-radius);
  direction: ltr !important;
  text-align: left !important;
  unicode-bidi: plaintext;
}

/* ---- dir=ltr helper for mixed-script tokens (SHA, ids, paths) ---- */
.td-ltr { direction: ltr; unicode-bidi: plaintext; display: inline-block; }

/* ---- empty state ---- */
.td-empty { color: var(--td-muted); font-size: 13px; padding: var(--td-space-3) var(--td-space-2); }

/* ---- responsive: nav becomes a clear bottom bar on small screens, tables
   scroll instead of being crushed (DOC-39 §3 / M19-T01 §5.3) ---- */
@media (max-width: 900px) {
  .gradio-container { padding: var(--td-space-2) !important; }
  .td-topbar { padding: var(--td-space-2) var(--td-space-3); }
  /* Pin the single nav bar to the bottom as a scrollable bar of 44px tabs. */
  .td-tabs .tab-nav {
    position: fixed;
    left: 0; right: 0; bottom: 0;
    top: auto;
    z-index: 50;
    flex-wrap: nowrap;
    overflow-x: auto;
    justify-content: flex-start;
    border-radius: 0;
    border-top: 1px solid var(--td-border) !important;
    border-bottom: 0 !important;
    padding-bottom: env(safe-area-inset-bottom, var(--td-space-2));
    background: var(--td-surface);
  }
  .td-tabs .tab-nav button { flex: 0 0 auto; white-space: nowrap; }
  /* Keep tables legible: scroll horizontally instead of shrinking columns. */
  .td-table .table-wrap, .td-candidates, #td-candidates { overflow-x: auto; }
  /* Leave room at the bottom so the fixed nav never covers content. */
  #td-shell { padding-bottom: calc(var(--td-touch) + var(--td-space-4)); }
}

/* ---- Gradio-specific resets that fight our palette ---- */
.gradio-container input, .gradio-container textarea, .gradio-container select {
  background: var(--td-surface-2) !important;
  color: var(--td-text) !important;
  border-color: var(--td-border) !important;
}
.gradio-container label, .gradio-container .gr-form, .gradio-container .gr-box,
.gradio-container .gr-accordion, .gradio-container .gr-group {
  border-color: var(--td-border) !important;
  background: var(--td-surface) !important;
  color: var(--td-text);
}
"""
