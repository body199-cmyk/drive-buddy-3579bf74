"""Reusable Gradio 6.20 HTML custom component hosting the React shell.

Communication uses only the official component value + ``submit`` event. The
browser bundle never opens an endpoint or transport of its own.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Mapping

_ASSET_DIR = Path(__file__).with_name("react_panel_assets")
_PANEL_JS = gzip.decompress(
    (_ASSET_DIR / "panel.bundle.gz").read_bytes()
).decode("utf-8")
_PANEL_CSS = gzip.decompress(
    (_ASSET_DIR / "panel.css.gz").read_bytes()
).decode("utf-8")
_PANEL_HTML = '<div data-teledrive-react-root="true"></div>'
_PANEL_ON_LOAD = _PANEL_JS + r"""
const tdPanel = TeleDriveGradioPanel.mount({
  element,
  readValue: () => props.value,
  writeValue: (value) => { props.value = value; },
  submit: () => trigger('submit'),
});
watch('value', () => tdPanel.receive(props.value));
"""

try:  # Gradio remains optional for non-UI import checks.
    import gradio as gr
except Exception:  # pragma: no cover - real runtime has pinned Gradio
    gr = None  # type: ignore


if gr is not None:
    class ReactPanel(gr.HTML):
        """JSON-valued custom HTML component with a bundled React frontend."""

        def __init__(self, value: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
            kwargs.setdefault("elem_id", "td-react-panel")
            kwargs.setdefault("container", False)
            kwargs.setdefault("apply_default_css", False)
            kwargs.setdefault("html_template", _PANEL_HTML)
            kwargs.setdefault("css_template", _PANEL_CSS)
            kwargs.setdefault("js_on_load", _PANEL_ON_LOAD)
            kwargs.setdefault("preserved_by_key", "value")
            super().__init__(value=value, **kwargs)

        def preprocess(self, payload: str | Mapping[str, Any] | None) -> dict[str, Any]:
            if isinstance(payload, Mapping):
                return dict(payload)
            if not payload:
                return {}
            parsed = json.loads(payload)
            return dict(parsed) if isinstance(parsed, Mapping) else {}

        def postprocess(self, value: str | Mapping[str, Any] | None) -> str:
            if isinstance(value, str):
                # Validate that component values remain JSON objects.
                parsed = json.loads(value)
                if not isinstance(parsed, Mapping):
                    raise ValueError("ReactPanel value must be a JSON object")
                return value
            return json.dumps(dict(value or {}), ensure_ascii=False, separators=(",", ":"))
else:
    class ReactPanel:  # pragma: no cover - only instantiated by ui.build
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("gradio is not installed")
