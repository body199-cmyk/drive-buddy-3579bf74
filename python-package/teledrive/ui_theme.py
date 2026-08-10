"""TeleDrive visual tokens + CSS (single source of truth for colors).

M17-T03: graphite dark / light palettes exposed as CSS variables; ui.py never
hardcodes a color. Theme switching is driven by replacing the <style> block
returned by ``theme_style_block`` — no JS, no page reload needed.
"""
from __future__ import annotations

PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0d0f10",
        "surface": "#15181a",
        "surface-2": "#1c2023",
        "border": "#262b2f",
        "text": "#e8edf0",
        "muted": "#8b969c",
        "accent": "#b6f24a",
        "accent-text": "#0d0f10",
        "ok": "#b6f24a",
        "warn": "#f2b34a",
        "err": "#f2565a",
        "info": "#6fc3ff",
        "logs-bg": "#080a0b",
        "logs-text": "#c9d1d9",
    },
    "light": {
        "bg": "#f6f8f7",
        "surface": "#ffffff",
        "surface-2": "#eef1ef",
        "border": "#d9e0dc",
        "text": "#121614",
        "muted": "#5c6764",
        "accent": "#7fbf1f",
        "accent-text": "#0d0f10",
        "ok": "#5aa314",
        "warn": "#b8811a",
        "err": "#c23c40",
        "info": "#2b7bbf",
        "logs-bg": "#f2f5f3",
        "logs-text": "#1e2220",
    },
}


def _all_token_keys() -> tuple[str, ...]:
    return tuple(PALETTES["dark"].keys())


def theme_style_block(theme: str) -> str:
    """Return a <style> block that sets CSS variables for the given theme.

    Invalid theme names silently fall back to dark (preference-only input
    should never crash the UI).
    """
    theme = theme if theme in PALETTES else "dark"
    p = dict(PALETTES[theme])
    # Legacy alias — older code/tests refer to --td-lime.
    p.setdefault("lime", p.get("accent", PALETTES["dark"]["accent"]))
    vars_css = "\n".join(
        f"  --td-{k}: {v};" for k, v in p.items()
    )
    return (
        f'<style id="td-theme-vars" data-td-theme="{theme}">\n'
        f":root, .gradio-container {{\n{vars_css}\n}}\n"
        f"</style>"
    )


BASE_CSS = """
:root, .gradio-container {
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
  --color-accent: var(--td-accent);
  --button-primary-background-fill: var(--td-accent);
  --button-primary-text-color: var(--td-accent-text);
  --button-secondary-background-fill: var(--td-surface-2);
  --button-secondary-text-color: var(--td-text);
  --button-secondary-border-color: var(--td-border);
  /* Legacy lime token kept for backwards-compat tests; equals accent. */
  --td-lime: var(--td-accent);
  --td-lime-dim: rgba(182, 242, 74, 0.14);
  --td-radius: 14px;
}
.td-root.td-rtl { direction: rtl; text-align: right; }
.td-root.td-ltr { direction: ltr; text-align: left; }

/* ---- shell grid: main + right navigation rail ---- */
#td-shell { display: grid; grid-template-columns: 1fr 232px; gap: 16px; align-items: start; }
#td-content { min-width: 0; }
#td-rail {
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-radius: 14px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  position: sticky;
  top: 8px;
}
#td-rail .td-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--td-muted);
  cursor: pointer;
  font-weight: 600;
  background: transparent;
  border: 0;
  width: 100%;
  text-align: start;
  font-size: 14px;
}
#td-rail .td-item:hover { color: var(--td-text); background: var(--td-surface-2); }
#td-rail .td-item[data-active="true"] {
  background: var(--td-surface-2);
  color: var(--td-text);
  box-shadow: inset -3px 0 0 0 var(--td-accent);
}
#td-rail .td-item .td-item-idx {
  font-size: 11px;
  color: var(--td-muted);
  opacity: 0.7;
  font-variant-numeric: tabular-nums;
}
#td-rail .td-rail-foot { margin-top: 8px; padding: 8px 10px; border-top: 1px solid var(--td-border); }

@media (max-width: 900px) {
  #td-shell { grid-template-columns: 1fr; }
  #td-rail { position: static; flex-direction: row; flex-wrap: wrap; }
  #td-rail .td-item { flex: 1 1 40%; width: auto; }
  #td-rail .td-item[data-active="true"] { box-shadow: inset 0 -3px 0 0 var(--td-accent); }
}

/* ---- top status bar ---- */
.td-topbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 10px 14px;
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-radius: 14px;
  margin-bottom: 14px;
}
.td-brand { font-size: 17px; letter-spacing: 0.3px; color: var(--td-text); margin-inline-end: auto; }
.td-brand strong { color: var(--td-text); }
.td-brand code {
  color: var(--td-accent);
  background: color-mix(in srgb, var(--td-accent) 16%, transparent);
  border-radius: 6px;
  padding: 1px 6px;
  font-size: 12px;
}
.td-chip {
  border: 1px solid var(--td-border);
  border-radius: 999px;
  padding: 4px 12px;
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
.td-chip[data-state="ok"]   { color: var(--td-ok); }
.td-chip[data-state="warn"] { color: var(--td-warn); }
.td-chip[data-state="err"]  { color: var(--td-err); }

/* ---- cards / sections ---- */
.td-card {
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-radius: 14px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.td-section-title { color: var(--td-muted); font-size: 14px; font-weight: 700; margin: 0; }

/* ---- buttons: primary uses accent, stop uses err wash ---- */
.gradio-container button { border-radius: 10px !important; }
.td-primary, .td-primary button, button.td-primary {
  background: var(--td-accent) !important;
  border-color: var(--td-accent) !important;
  color: var(--td-accent-text) !important;
  font-weight: 700;
}
.td-stop, .td-stop button, button.td-stop {
  background: color-mix(in srgb, var(--td-err) 14%, transparent) !important;
  border-color: var(--td-err) !important;
  color: var(--td-err) !important;
  font-weight: 700;
}

/* ---- semantic panels ---- */
.td-panel-otp {
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-inline-start: 4px solid var(--td-info);
  border-radius: 14px;
  padding: 10px 14px;
}
.td-panel-2fa {
  background: var(--td-surface);
  border: 1px solid var(--td-border);
  border-inline-start: 4px solid var(--td-warn);
  border-radius: 14px;
  padding: 10px 14px;
}

/* ---- tables ---- */
.td-table { border: 1px solid var(--td-border); border-radius: 14px; overflow: hidden; }
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
  border-radius: 14px;
  direction: ltr !important;
  text-align: left !important;
  unicode-bidi: plaintext;
}

/* ---- dir=ltr helper for mixed-script tokens (SHA, ids, paths) ---- */
.td-ltr { direction: ltr; unicode-bidi: plaintext; display: inline-block; }

/* ---- empty state ---- */
.td-empty { color: var(--td-muted); font-size: 13px; padding: 12px 8px; }

/* ---- Gradio-specific resets that fight our palette ---- */
.gradio-container .gr-button-primary { background: var(--td-accent) !important; color: var(--td-accent-text) !important; }
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
