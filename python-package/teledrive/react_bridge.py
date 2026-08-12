"""Official Gradio-component bridge for the embedded React UI (M24).

The bridge is an adapter only. It accepts one validated action request from the
``ReactPanel`` value, dispatches the already-registered named handler on the one
ApplicationContext, and returns a redacted response plus a live snapshot. It
creates no HTTP server, client, event loop, Telegram client, Drive service, or
SQLite connection.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable, Mapping
from uuid import uuid4

from .i18n import set_language
from .logging_config import get_logger
from .redaction import PLACEHOLDER, redact

_log = get_logger("teledrive.react_bridge")


@dataclass(frozen=True)
class BridgeRequest:
    request_id: str
    action_id: str
    payload: Mapping[str, Any]
    language: str


@dataclass(frozen=True)
class BridgeResponse:
    request_id: str
    action_id: str
    status: str
    data: Mapping[str, Any] | None = None
    error_key: str | None = None
    message: str | None = None
    state: Mapping[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        response: dict[str, Any] = {
            "requestId": self.request_id,
            "actionId": self.action_id,
            "status": self.status,
        }
        if self.data is not None:
            response["data"] = dict(self.data)
        if self.error_key:
            response["errorKey"] = self.error_key
        if self.message:
            response["message"] = self.message
        if self.state is not None:
            response["state"] = dict(self.state)
        return response


_SECRET_KEYS = {
    "api_id", "api_hash", "phone", "phone_code_hash", "code", "password",
    "session", "session_string", "token", "access_token", "refresh_token",
    "credentials",
}

# Generic React transport must never carry authentication secrets. The secure
# Gradio fields remain wired to these existing actions outside the panel.
_SECURE_GRADIO_ONLY = {
    "telegram.set_credentials",
    "telegram.send_code",
    "telegram.verify_code",
    "telegram.verify_password",
}

_NO_ARGS = {
    "telegram.resend_code", "telegram.logout", "telegram.status",
    "drive.connect", "drive.reconnect", "drive.status", "drive.refresh_quota",
    "analyze.select_all", "analyze.clear_selection", "analyze.enqueue_selected",
    "queue.start_selected", "queue.pause", "queue.resume", "queue.stop",
    "queue.retry_failed", "queue.clear_completed", "queue.clear_incomplete",
    "queue.refresh",
    "dashboard.refresh", "settings.toggle_language", "export.build_zip",
    "export.colab_cells", "recovery.restore", "maintenance.checkpoint",
}

_ITEM_ACTIONS = {
    "queue.pause_item", "queue.resume_item", "queue.stop_item", "queue.retry_item",
}


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).strip().lower() in _SECRET_KEYS:
                return True
            if _contains_secret_key(child):
                return True
    elif isinstance(value, (list, tuple, set)):
        return any(_contains_secret_key(child) for child in value)
    return False


def _safe_text(value: Any) -> str:
    return redact(str(value or "")).strip()


def _update_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("value")
    return None


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [text for child in value.values() for text in _flatten_strings(child)]
    if isinstance(value, (list, tuple)):
        return [text for child in value for text in _flatten_strings(child)]
    return []


class ReactBridge:
    """React -> existing Action Registry / named handler adapter."""

    def __init__(
        self,
        ctx: Any,
        registry: Any,
        snapshotter: Callable[[], Mapping[str, Any]],
    ) -> None:
        self._ctx = ctx
        self._registry = registry
        self._snapshotter = snapshotter

    def initial_response(self) -> dict[str, Any]:
        return BridgeResponse(
            request_id="bridge-initial",
            action_id="bridge.snapshot",
            status="ok",
            state=self._redact_value(self._snapshotter()),
        ).as_dict()

    def handle(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        request_id = _safe_text(raw.get("requestId")) if isinstance(raw, Mapping) else ""
        action_id = _safe_text(raw.get("actionId")) if isinstance(raw, Mapping) else ""
        try:
            request = self._parse(raw)
        except (TypeError, ValueError):
            return BridgeResponse(
                request_id=request_id or "invalid-request",
                action_id=action_id or "unknown",
                status="error",
                error_key="bridge.invalid_request",
                message="Invalid bridge request",
            ).as_dict()

        spec = self._registry.get(request.action_id)
        if spec is None:
            return self._error(request, "bridge.unknown_action", "Unknown action")
        if request.action_id == "react.bridge.request":
            return self._error(request, "bridge.recursive_action", "Recursive bridge action")
        if not spec.ready:
            return self._error(
                request,
                spec.blocked_reason_key or "bridge.action_blocked",
                "Action is currently blocked",
                status="blocked",
            )
        if request.action_id in _SECURE_GRADIO_ONLY:
            return self._error(
                request,
                "bridge.secure_gradio_only",
                "Use the secure Gradio authentication controls",
                status="blocked",
            )
        if _contains_secret_key(request.payload):
            return self._error(
                request,
                "bridge.secret_payload_refused",
                "Secret-bearing payload refused",
                status="blocked",
            )

        handler = getattr(self._ctx.handlers, spec.handler_name, None)
        if not callable(handler):
            return self._error(request, "bridge.handler_missing", "Registered handler unavailable")

        try:
            set_language(request.language)
            args = self._handler_args(request)
            result = handler(*args)
            state = self._redact_value(self._snapshotter())
            failure = self._failure_message(result)
            if failure:
                return BridgeResponse(
                    request_id=request.request_id,
                    action_id=request.action_id,
                    status="error",
                    error_key="bridge.action_failed",
                    message=failure,
                    state=state,
                ).as_dict()
            return BridgeResponse(
                request_id=request.request_id,
                action_id=request.action_id,
                status="ok",
                data=self._response_data(request.action_id, result),
                message="Action completed",
                state=state,
            ).as_dict()
        except (TypeError, ValueError, KeyError):
            return self._error(request, "bridge.invalid_payload", "Invalid action payload")
        except Exception:  # noqa: BLE001 - payload/traceback are deliberately not logged
            correlation_id = uuid4().hex[:12]
            _log.error(
                "react_bridge_action_failed correlation_id=%s action_id=%s",
                correlation_id,
                request.action_id,
            )
            return self._error(
                request,
                "bridge.action_failed",
                f"Action failed [{correlation_id}]",
            )

    def _parse(self, raw: Mapping[str, Any]) -> BridgeRequest:
        if not isinstance(raw, Mapping):
            raise TypeError("request must be an object")
        request_id = str(raw.get("requestId") or "").strip()
        action_id = str(raw.get("actionId") or "").strip()
        language = str(raw.get("language") or "ar").strip().lower()
        payload = raw.get("payload")
        if not request_id or not action_id:
            raise ValueError("requestId and actionId are required")
        if language not in {"ar", "en"}:
            language = "ar"
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be an object")
        return BridgeRequest(request_id, action_id, payload, language)

    def _handler_args(self, request: BridgeRequest) -> tuple[Any, ...]:
        payload = request.payload
        action_id = request.action_id
        if action_id in _NO_ARGS:
            return ()
        if action_id in _ITEM_ACTIONS:
            return (str(payload.get("itemId") or "").strip(),)
        if action_id == "drive.list_folders":
            return (str(payload.get("parentId") or "root").strip() or "root",)
        if action_id == "drive.create_folder":
            return (
                str(payload.get("name") or "").strip(),
                str(payload.get("parentId") or "root").strip() or "root",
            )
        if action_id == "drive.select_folder":
            return (str(payload.get("folderId") or "").strip(),)
        if action_id == "analyze.run":
            return (
                str(payload.get("link") or "").strip(),
                str(payload.get("mode") or "message").strip(),
                payload.get("messageId"), payload.get("startId"), payload.get("endId"),
                payload.get("limit") or 1000,
                list(payload.get("mediaTypes") or ["all"]),
            )
        if action_id == "analyze.set_mode":
            return (str(payload.get("mode") or "message"),)
        if action_id == "analyze.apply_filters":
            return (
                list(payload.get("mediaTypes") or ["all"]),
                str(payload.get("extensions") or ""),
                payload.get("minSizeMb"), payload.get("maxSizeMb"),
                str(payload.get("dateFrom") or ""), str(payload.get("dateTo") or ""),
                str(payload.get("include") or ""), str(payload.get("exclude") or ""),
            )
        if action_id == "analyze.toggle_row":
            source_id = str(payload.get("sourceId") or "")
            visible = self._ctx.selection.visible()
            row = next(index for index, item in enumerate(visible) if item.id == source_id)
            return (SimpleNamespace(index=(row, 0), value=""),)
        if action_id == "analyze.select_range":
            return (payload.get("startId"), payload.get("endId"))
        if action_id == "analyze.select_group":
            return (str(payload.get("groupId") or ""),)
        if action_id == "logs.refresh" or action_id == "logs.download":
            return (str(payload.get("level") or "ALL"),)
        if action_id == "logs.search":
            return (
                str(payload.get("query") or ""),
                str(payload.get("level") or "ALL"),
            )
        if action_id == "settings.set_concurrency":
            return (payload.get("value"),)
        if action_id == "settings.set_theme":
            return (str(payload.get("theme") or "light"),)
        raise ValueError("unsupported action adapter")

    def _response_data(self, action_id: str, result: Any) -> Mapping[str, Any] | None:
        if action_id == "drive.list_folders":
            update = result[1] if isinstance(result, (list, tuple)) and len(result) > 1 else {}
            choices = update.get("choices", []) if isinstance(update, Mapping) else []
            folders = []
            for choice in choices:
                raw = choice[1] if isinstance(choice, (list, tuple)) and len(choice) > 1 else choice
                label, _, folder_id = str(raw).rpartition(" :: ")
                folders.append({"id": folder_id or str(raw), "name": label or str(raw)})
            return {"folders": folders}
        if action_id in {"logs.refresh", "logs.search"}:
            first = result[0] if isinstance(result, (list, tuple)) and result else result
            return {"logs": _safe_text(_update_value(first) or "")}
        return None

    @staticmethod
    def _failure_message(result: Any) -> str | None:
        for text in _flatten_strings(result):
            cleaned = _safe_text(text)
            if cleaned.startswith("⚠️"):
                return cleaned
        return None

    def _error(
        self,
        request: BridgeRequest,
        error_key: str,
        message: str,
        status: str = "error",
    ) -> dict[str, Any]:
        try:
            state = self._redact_value(self._snapshotter())
        except Exception:  # pragma: no cover - defensive, no traceback/payload log
            state = None
        return BridgeResponse(
            request_id=request.request_id,
            action_id=request.action_id,
            status=status,
            error_key=error_key,
            message=_safe_text(message),
            state=state,
        ).as_dict()

    def _redact_value(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            clean: dict[str, Any] = {}
            for key, child in value.items():
                name = str(key)
                clean[name] = (
                    PLACEHOLDER
                    if name.lower() in _SECRET_KEYS
                    else self._redact_value(child)
                )
            return clean
        if isinstance(value, (list, tuple, set)):
            return [self._redact_value(child) for child in value]
        if isinstance(value, str):
            return redact(value)
        if isinstance(value, (bool, int, float)) or value is None:
            return value
        return redact(str(value))
