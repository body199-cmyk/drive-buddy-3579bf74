"""Light-only design system for the Gradio shell (M20-T02).

Why this file exists
--------------------
Gradio decides between its light and dark palette from the browser's
``prefers-color-scheme`` and from the ``?__theme`` query flag. Inside a Colab
iframe neither is under our control, which is exactly how the previous build
ended up painting a black UI that no in-app toggle could fix.

So the light palette is not a preference here, it is the only palette:

1. Every Gradio CSS variable is redefined under ``:root``, ``.dark``,
   ``body.dark`` and ``.gradio-container.dark`` with ``!important`` and
   ``color-scheme: light``. Even if Gradio flips to dark, the tokens it reads
   are the light ones.
2. ``FORCE_LIGHT_JS`` strips the ``dark`` class on load and keeps stripping it
   through a MutationObserver, and pins ``dir="rtl"`` on the document.

No colour is defined anywhere else in this module's consumers: ``ui.py`` never
hardcodes a hex value, it only references the ``--td-*`` tokens declared here.
"""
from __future__ import annotations

from typing import Any


def build_theme() -> Any:
    """A neutral Gradio base theme. All colour work happens in TELEDRIVE_CSS.

    We deliberately do NOT pass colour tokens to ``Base.set()``: token names
    move between Gradio versions and a TypeError there would take the whole
    launch down. CSS variables are stable and win anyway.
    """
    import gradio as gr

    try:
        font = [gr.themes.GoogleFont("IBM Plex Sans Arabic"), "system-ui", "sans-serif"]
        font_mono = [gr.themes.GoogleFont("IBM Plex Mono"), "ui-monospace", "monospace"]
    except Exception:  # pragma: no cover - very old gradio
        font = ["system-ui", "sans-serif"]
        font_mono = ["ui-monospace", "monospace"]

    return gr.themes.Base(
        primary_hue=gr.themes.colors.purple,
        secondary_hue=gr.themes.colors.slate,
        neutral_hue=gr.themes.colors.gray,
        font=font,
        font_mono=font_mono,
    )


# --------------------------------------------------------------------------
# Guard 2: strip the dark class, keep it stripped, pin RTL.
# --------------------------------------------------------------------------
FORCE_LIGHT_JS = """
() => {
  const strip = () => {
    document.documentElement.classList.remove('dark');
    document.body && document.body.classList.remove('dark');
    document.documentElement.style.colorScheme = 'light';
    document.querySelectorAll('.dark').forEach((el) => el.classList.remove('dark'));
    document.documentElement.setAttribute('dir', 'rtl');
    document.documentElement.setAttribute('lang', 'ar');
  };
  strip();
  const observer = new MutationObserver(strip);
  observer.observe(document.documentElement, {
    attributes: true, subtree: true, attributeFilter: ['class']
  });
}
"""

# Fallback for Gradio builds whose Blocks() has no js= parameter.
FORCE_LIGHT_HTML = (
    "<script>(function(){var s=function(){"
    "document.documentElement.classList.remove('dark');"
    "document.body&&document.body.classList.remove('dark');"
    "document.documentElement.style.colorScheme='light';"
    "document.documentElement.setAttribute('dir','rtl');};"
    "s();new MutationObserver(s).observe(document.documentElement,"
    "{attributes:true,subtree:true,attributeFilter:['class']});})();</script>"
)

TELEDRIVE_CSS = """
/* ==========================================================================
   TeleDrive M20 — light-only tokens. Declared for the dark selectors too, so
   Gradio's dark mode resolves to the same values instead of inverting.
   The --td-* tokens carry !important because the legacy ui_theme style block
   is injected into the BODY, i.e. later in the document than this sheet: with
   equal specificity the later declaration would win and could still repaint
   the shell dark. !important on a custom property removes that last path.
   ========================================================================== */
:root, body, body.dark, gradio-app, .dark,
.gradio-container, .gradio-container.dark {
  --td-bg:#F4F0F5 !important;
  --td-surface:#FDFBFD !important;
  --td-surface-2:#EEE8EF !important;
  --td-surface-3:#E5DDE7 !important;
  --td-text:#2A2430 !important;
  --td-muted:#6E6472 !important;
  --td-faint:#948B98 !important;
  --td-line:#E0D8E2 !important;
  --td-line-strong:#C9BDCC !important;
  --td-primary:#7B3E86 !important;
  --td-primary-hover:#663270 !important;
  --td-primary-soft:#F1E4F3 !important;
  --td-success:#2E7D5B !important;
  --td-success-soft:#E4F3EC !important;
  --td-warn:#B4761F !important;
  --td-warn-soft:#FBF0DD !important;
  --td-danger:#C0392B !important;
  --td-danger-soft:#FBE7E4 !important;

  color-scheme: light !important;

  --body-background-fill: var(--td-bg) !important;
  --body-text-color: var(--td-text) !important;
  --body-text-color-subdued: var(--td-muted) !important;
  --background-fill-primary: var(--td-surface) !important;
  --background-fill-secondary: var(--td-surface-2) !important;
  --block-background-fill: var(--td-surface) !important;
  --block-border-color: var(--td-line) !important;
  --block-label-background-fill: var(--td-surface-2) !important;
  --block-label-text-color: var(--td-muted) !important;
  --block-title-text-color: var(--td-text) !important;
  --border-color-primary: var(--td-line) !important;
  --border-color-accent: var(--td-primary) !important;
  --panel-background-fill: var(--td-surface) !important;
  --panel-border-color: var(--td-line) !important;
  --input-background-fill: var(--td-surface) !important;
  --input-border-color: var(--td-line-strong) !important;
  --input-placeholder-color: var(--td-faint) !important;
  --checkbox-background-color: var(--td-surface) !important;
  --checkbox-border-color: var(--td-line-strong) !important;
  --button-primary-background-fill: var(--td-primary) !important;
  --button-primary-background-fill-hover: var(--td-primary-hover) !important;
  --button-primary-text-color: #FFFFFF !important;
  --button-primary-border-color: var(--td-primary) !important;
  --button-secondary-background-fill: var(--td-surface) !important;
  --button-secondary-background-fill-hover: var(--td-surface-2) !important;
  --button-secondary-text-color: var(--td-text) !important;
  --button-secondary-border-color: var(--td-line-strong) !important;
  --table-even-background-fill: var(--td-surface) !important;
  --table-odd-background-fill: var(--td-surface-2) !important;
  --table-border-color: var(--td-line) !important;
  --color-accent-soft: var(--td-primary-soft) !important;
  --slider-color: var(--td-primary) !important;
  --link-text-color: var(--td-primary) !important;
  --link-text-color-hover: var(--td-primary-hover) !important;
}

body, gradio-app, .gradio-container {
  background: var(--td-bg) !important;
  color: var(--td-text) !important;
  direction: rtl;
  font-family: "IBM Plex Sans Arabic", system-ui, -apple-system, "Segoe UI", sans-serif;
}
.gradio-container { max-width: 1180px !important; margin: 0 auto !important; }

/* ---- header ---- */
.td-topbar {
  align-items: center; gap: 16px;
  border-bottom: 1px solid var(--td-line);
  padding-bottom: 10px; margin-bottom: 4px;
}
.td-brand h3, .td-brand h2 { margin: 0; letter-spacing: -0.01em; }
.td-chips p { margin: 0; font-size: 0.85rem; color: var(--td-muted); }
.td-toolbar { align-items: end; gap: 8px; }

/* ---- stepper ---- */
.td-flow {
  background: var(--td-surface); border: 1px solid var(--td-line);
  border-radius: 12px; padding: 10px 14px; margin: 10px 0 18px;
  font-size: 0.9rem;
}
.td-stepper { display: flex; flex-wrap: wrap; gap: 6px 14px; }

/* ---- step cards ---- */
.td-card {
  background: var(--td-surface) !important;
  border: 1px solid var(--td-line) !important;
  border-radius: 14px !important;
  padding: 18px !important;
  margin-bottom: 18px !important;
  box-shadow: 0 1px 2px rgba(42,36,48,0.04);
}
.td-step-head { display: flex; align-items: center; gap: 10px; }
.td-step-no {
  width: 26px; height: 26px; border-radius: 50%;
  background: var(--td-primary); color: #fff;
  display: inline-grid; place-items: center;
  font-size: 0.8rem; font-weight: 700; flex: 0 0 auto;
}
.td-step-title { font-size: 1.05rem; font-weight: 700; color: var(--td-text); }
.td-step-hint {
  margin: 6px 0 14px 0; font-size: 0.85rem; color: var(--td-muted);
  padding-inline-start: 36px;
}

/* ---- selection summary ---- */
.td-summary, .td-hint {
  background: var(--td-primary-soft); border: 1px solid var(--td-line);
  border-radius: 10px; padding: 10px 14px; font-size: 0.88rem;
}
.td-hint { background: var(--td-warn-soft); }

/* ---- logs stay LTR ---- */
.td-log textarea {
  direction: ltr !important; text-align: left !important;
  font-family: "IBM Plex Mono", ui-monospace, monospace !important;
  font-size: 0.8rem !important;
}

/* ---- tables ---- */
.gradio-container table { font-size: 0.85rem; }
.gradio-container thead th {
  background: var(--td-surface-2) !important;
  color: var(--td-muted) !important;
  font-weight: 600 !important;
}

/* ---- footer noise ---- */
footer { display: none !important; }
"""
