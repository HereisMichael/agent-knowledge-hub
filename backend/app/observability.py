"""Sanitized structured telemetry for public operations."""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings


REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_SAFE_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "user_id",
    "model",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
)


def current_request_id() -> str:
    return _request_id.get()


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for field in _SAFE_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_structured_logging() -> None:
    if settings.app_env != "production":
        return
    logger = logging.getLogger("akh")
    if any(getattr(handler, "_akh_json", False) for handler in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    handler._akh_json = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def _safe_request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    if _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return uuid.uuid4().hex


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path.startswith("/") and len(path) <= 300:
        return path
    return "<unmatched>"


async def request_telemetry(request: Request, call_next):
    request_id = _safe_request_id(request.headers.get(REQUEST_ID_HEADER))
    token = _request_id.set(request_id)
    request.state.request_id = request_id
    started = time.perf_counter()
    logger = logging.getLogger("akh.request")
    try:
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": _route_template(request),
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "user_id": getattr(
                        getattr(request.state, "identity", None),
                        "user_id",
                        None,
                    ),
                },
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "internal_server_error"},
                headers={REQUEST_ID_HEADER: request_id},
            )
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        status_code = response.status_code
        if status_code >= 500:
            event = "request_failed"
            level = logging.ERROR
        elif duration_ms >= settings.slow_request_ms:
            event = "slow_request"
            level = logging.WARNING
        else:
            event = "request_completed"
            level = logging.INFO
        logger.log(
            level,
            event,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": _route_template(request),
                "status_code": status_code,
                "duration_ms": duration_ms,
                "user_id": getattr(
                    getattr(request.state, "identity", None),
                    "user_id",
                    None,
                ),
            },
        )
        return response
    finally:
        _request_id.reset(token)
