from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import BoundedSemaphore
from typing import Any

import httpx
from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APITimeoutError,
)

from app.security.outbound_url import (
    UnsafeOutboundUrl,
    validate_httpx_request,
)


MODEL_HTTP_TIMEOUT = httpx.Timeout(60.0, connect=5.0, write=30.0, pool=5.0)
MODEL_REQUEST_DEADLINE_SECONDS = 75.0
MAX_MODEL_RESPONSE_BYTES = 2 * 1024 * 1024
MODEL_MAX_CONCURRENCY = 8
_MODEL_EXECUTOR = ThreadPoolExecutor(
    max_workers=MODEL_MAX_CONCURRENCY,
    thread_name_prefix="model-call",
)
_MODEL_SLOTS = BoundedSemaphore(MODEL_MAX_CONCURRENCY)


class ModelEndpointError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class BoundedResponseStream(httpx.SyncByteStream):
    def __init__(
        self,
        stream: httpx.SyncByteStream,
        *,
        max_bytes: int,
        deadline: float,
    ):
        self._stream = stream
        self._max_bytes = max_bytes
        self._deadline = deadline

    def __iter__(self):
        total = 0
        for chunk in self._stream:
            if time.monotonic() > self._deadline:
                raise ModelEndpointError("model_request_deadline_exceeded")
            total += len(chunk)
            if total > self._max_bytes:
                raise ModelEndpointError("model_response_too_large")
            yield chunk

    def close(self) -> None:
        self._stream.close()


class BoundedHTTPTransport(httpx.BaseTransport):
    def __init__(self):
        self._transport = httpx.HTTPTransport(retries=0)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        deadline = time.monotonic() + MODEL_REQUEST_DEADLINE_SECONDS
        response = self._transport.handle_request(request)
        if time.monotonic() > deadline:
            response.close()
            raise ModelEndpointError("model_request_deadline_exceeded")
        return bound_model_response(response, deadline=deadline)

    def close(self) -> None:
        self._transport.close()


def bound_model_response(
    response: httpx.Response,
    *,
    deadline: float,
) -> httpx.Response:
    content_encoding = response.headers.get("content-encoding", "").strip().lower()
    if content_encoding not in {"", "identity"}:
        response.close()
        raise ModelEndpointError("model_response_encoding_unsupported")
    try:
        content_length = int(response.headers.get("content-length", "0"))
    except ValueError:
        content_length = 0
    if content_length > MAX_MODEL_RESPONSE_BYTES:
        response.close()
        raise ModelEndpointError("model_response_too_large")
    response.stream = BoundedResponseStream(
        response.stream,
        max_bytes=MAX_MODEL_RESPONSE_BYTES,
        deadline=deadline,
    )
    return response


def build_http_client() -> httpx.Client:
    return httpx.Client(
        timeout=MODEL_HTTP_TIMEOUT,
        transport=BoundedHTTPTransport(),
        follow_redirects=False,
        trust_env=False,
        event_hooks={"request": [validate_httpx_request]},
    )


def run_model_call(client: Any, operation: Callable[[], Any]) -> Any:
    if not _MODEL_SLOTS.acquire(blocking=False):
        client.close()
        raise ModelEndpointError("model_capacity_exhausted")
    future = _MODEL_EXECUTOR.submit(operation)

    def release_slot(_future) -> None:
        _MODEL_SLOTS.release()

    future.add_done_callback(release_slot)
    try:
        return future.result(timeout=MODEL_REQUEST_DEADLINE_SECONDS)
    except FutureTimeout as exc:
        client.close()
        future.cancel()
        raise ModelEndpointError("model_request_deadline_exceeded") from exc
    finally:
        if future.done():
            client.close()


def model_error_code_for_status(status_code: int) -> str:
    if status_code in {401, 403}:
        return "model_auth_failed"
    if status_code == 429:
        return "model_rate_limited"
    if 400 <= status_code < 500:
        return "model_request_invalid"
    if 500 <= status_code < 600:
        return "model_endpoint_unreachable"
    return "model_response_invalid"


def _status_code(exc: BaseException) -> int | None:
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and not isinstance(status, bool):
        return status
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int) and not isinstance(status, bool):
        return status
    return None


def raise_boundary_error(exc: Exception) -> None:
    current: BaseException | None = exc
    while current is not None:
        code: str | None = None
        if isinstance(current, ModelEndpointError):
            code = current.code
        elif isinstance(current, UnsafeOutboundUrl):
            code = "model_endpoint_blocked"
        elif isinstance(current, APIResponseValidationError):
            code = "model_response_invalid"
        elif isinstance(current, (APITimeoutError, httpx.TimeoutException)):
            code = "model_request_deadline_exceeded"
        else:
            status_code = _status_code(current)
            if status_code is not None:
                code = model_error_code_for_status(status_code)
            elif isinstance(current, (APIConnectionError, httpx.RequestError)):
                code = "model_endpoint_unreachable"
            elif isinstance(current, (TypeError, ValueError)):
                code = "model_response_invalid"
        if code is not None:
            raise ModelEndpointError(code) from None
        current = current.__cause__ or current.__context__
    raise ModelEndpointError("model_endpoint_unreachable") from None
