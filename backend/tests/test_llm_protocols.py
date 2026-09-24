from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import openai
import pytest

from app.llm import anthropic_messages, client, openai_chat
from app.llm.client import ModelEndpointError
from app.llm.protocols import (
    ANTHROPIC_MESSAGES,
    OPENAI_CHAT,
    SUPPORTED_PROTOCOLS,
    ModelResult,
    ModelUsage,
)
from app.llm.transport import ModelEndpointError as TransportModelEndpointError
from app.security.outbound_url import UnsafeOutboundUrl
from app.settings.service import LlmRuntime


class FakeOpenAI:
    def __init__(self, response):
        self.response = response
        self.request = None
        self.closed = False
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.request = kwargs
        return self.response

    def close(self):
        self.closed = True


def openai_runtime() -> LlmRuntime:
    return LlmRuntime(
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        model="test-model",
        demo=False,
        protocol=OPENAI_CHAT,
    )


def anthropic_runtime(base_url: str = "https://api.anthropic.com") -> LlmRuntime:
    return LlmRuntime(
        base_url=base_url,
        api_key="sk-ant-test",
        model="claude-test",
        demo=False,
        protocol=ANTHROPIC_MESSAGES,
    )


def openai_response(
    content: str | None = "answer",
    *,
    choices=None,
):
    return SimpleNamespace(
        choices=(
            [SimpleNamespace(message=SimpleNamespace(content=content))]
            if choices is None
            else choices
        ),
        usage=SimpleNamespace(
            prompt_tokens=11,
            completion_tokens=7,
            total_tokens=18,
        ),
    )


def test_protocol_values_are_canonical_and_errors_keep_the_public_identity():
    assert OPENAI_CHAT == "openai_chat"
    assert ANTHROPIC_MESSAGES == "anthropic_messages"
    assert SUPPORTED_PROTOCOLS == frozenset({OPENAI_CHAT, ANTHROPIC_MESSAGES})
    assert ModelUsage() == ModelUsage(0, 0, 0)
    assert ModelEndpointError is TransportModelEndpointError
    assert ModelEndpointError("model_endpoint_blocked").code == "model_endpoint_blocked"


def test_openai_adapter_returns_canonical_result(monkeypatch):
    fake = FakeOpenAI(openai_response())
    monkeypatch.setattr(openai_chat, "build_openai_client", lambda runtime: fake)

    result = openai_chat.complete_openai(
        openai_runtime(), "system", "user", json_mode=False
    )

    assert result == ModelResult("answer", ModelUsage(11, 7, 18))
    assert fake.request["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]
    assert fake.request["model"] == "test-model"
    assert fake.request["temperature"] == 0.2
    assert "response_format" not in fake.request
    assert fake.closed is True


def test_openai_adapter_sends_json_object_response_format(monkeypatch):
    fake = FakeOpenAI(openai_response('{"ok": true}'))
    monkeypatch.setattr(openai_chat, "build_openai_client", lambda runtime: fake)

    result = openai_chat.complete_openai(
        openai_runtime(), "system", "user", json_mode=True
    )

    assert result.text == '{"ok": true}'
    assert fake.request["response_format"] == {"type": "json_object"}
    assert fake.request["temperature"] == 0.2


@pytest.mark.parametrize(
    "response",
    [
        openai_response(choices=[]),
        openai_response(None),
        openai_response(""),
        openai_response("   \r\n\t"),
    ],
    ids=["empty-choices", "none-content", "empty-content", "blank-content"],
)
def test_openai_adapter_rejects_empty_responses(monkeypatch, response):
    fake = FakeOpenAI(response)
    monkeypatch.setattr(openai_chat, "build_openai_client", lambda runtime: fake)

    with pytest.raises(ModelEndpointError) as error:
        openai_chat.complete_openai(
            openai_runtime(), "system", "user", json_mode=False
        )

    assert error.value.code == "model_response_invalid"


def test_openai_adapter_translates_blocked_endpoint_errors(monkeypatch):
    def blocked(_runtime):
        raise UnsafeOutboundUrl("private address")

    monkeypatch.setattr(openai_chat, "build_openai_client", blocked)

    with pytest.raises(ModelEndpointError) as error:
        openai_chat.complete_openai(
            openai_runtime(), "system", "user", json_mode=False
        )

    assert error.value.code == "model_endpoint_blocked"


def test_chat_text_dispatches_through_openai_adapter(monkeypatch):
    fake = FakeOpenAI(openai_response("facade answer"))
    monkeypatch.setattr(openai_chat, "build_openai_client", lambda runtime: fake)

    result = client.chat_text(
        "system",
        "user",
        runtime=openai_runtime(),
    )

    assert result == "facade answer"
    assert fake.request["messages"][1] == {"role": "user", "content": "user"}


def test_chat_json_dispatches_through_openai_adapter(monkeypatch):
    fake = FakeOpenAI(openai_response('{"score": 9}'))
    monkeypatch.setattr(openai_chat, "build_openai_client", lambda runtime: fake)

    result = client.chat_json(
        "system",
        "evaluate",
        schema_hint='{"score": 0}',
        runtime=openai_runtime(),
    )

    assert result == {"score": 9}
    assert fake.request["messages"][1] == {
        "role": "user",
        "content": 'evaluate\n\n请严格输出 JSON：\n{"score": 0}',
    }
    assert fake.request["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("https://api.anthropic.com", "https://api.anthropic.com/v1/messages"),
        ("https://api.anthropic.com/v1", "https://api.anthropic.com/v1/messages"),
        (
            "https://gateway.example/anthropic",
            "https://gateway.example/anthropic/v1/messages",
        ),
        (
            "https://gateway.example/anthropic/v1/",
            "https://gateway.example/anthropic/v1/messages",
        ),
    ],
)
def test_anthropic_messages_url_rules(monkeypatch, base_url, expected):
    monkeypatch.setattr(anthropic_messages, "validate_outbound_url", lambda value: value)
    assert anthropic_messages.anthropic_messages_url(base_url) == expected


def test_anthropic_adapter_builds_request_and_returns_canonical_result(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "text", "text": "first"},
                    {
                        "type": "tool_use",
                        "id": "ignored",
                        "name": "x",
                        "input": {},
                    },
                    {"type": "text", "text": " second"},
                ],
                "usage": {"input_tokens": 9, "output_tokens": 4},
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(anthropic_messages, "validate_outbound_url", lambda value: value)
    monkeypatch.setattr(anthropic_messages, "build_http_client", lambda: http_client)

    result = anthropic_messages.complete_anthropic(
        anthropic_runtime(), "system", "user", json_mode=False
    )

    request = captured["request"]
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    assert request.headers["x-api-key"] == "sk-ant-test"
    assert request.headers["anthropic-version"] == "2023-06-01"
    assert request.headers["content-type"] == "application/json"
    assert captured["payload"] == {
        "model": "claude-test",
        "max_tokens": 2048,
        "temperature": 0.2,
        "system": "system",
        "messages": [{"role": "user", "content": "user"}],
    }
    assert result == ModelResult("first second", ModelUsage(9, 4, 13))
    assert http_client.is_closed is True


def test_anthropic_json_mode_adds_json_only_instruction(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": '{"score": 8}'}],
                "usage": {"input_tokens": 3, "output_tokens": 2},
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(anthropic_messages, "validate_outbound_url", lambda value: value)
    monkeypatch.setattr(anthropic_messages, "build_http_client", lambda: http_client)
    anthropic_messages.complete_anthropic(
        anthropic_runtime(), "system", "evaluate", json_mode=True
    )

    prompt = captured["payload"]["messages"][0]["content"]
    assert prompt.startswith("evaluate\n\n")
    assert "JSON" in prompt
    assert "不要添加解释" in prompt


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"score": 8}', {"score": 8}),
        (
            (chr(96) * 3) + 'json\n{"score": 8}\n' + (chr(96) * 3),
            {"score": 8},
        ),
        (
            "  " + (chr(96) * 3) + '\n{"nested": {"ok": true}}\n'
            + (chr(96) * 3) + "  ",
            {"nested": {"ok": True}},
        ),
    ],
)
def test_parse_json_object_accepts_one_complete_object(text, expected):
    assert client.parse_json_object(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "[]",
        'leading prose {"score": 8}',
        '{"score": 8} trailing prose',
        '{"first": 1} {"second": 2}',
        (chr(96) * 3) + 'json\n{"score": 8}\n' + (chr(96) * 3) + "\nextra",
        (chr(96) * 3) + "json\n{not-json}\n" + (chr(96) * 3),
        "null",
        "8",
    ],
)
def test_parse_json_object_rejects_non_object_or_non_exact_output(text):
    with pytest.raises(ModelEndpointError) as error:
        client.parse_json_object(text)

    assert error.value.code == "model_json_invalid"


@pytest.mark.parametrize(
    "text",
    [
        '{"value": NaN}',
        '{"value": Infinity}',
        '{"value": -Infinity}',
        '{"score": 1, "score": 2}',
        '{"result": {"score": 1, "score": 2}}',
    ],
    ids=[
        "nan",
        "positive-infinity",
        "negative-infinity",
        "duplicate-top-level-key",
        "duplicate-nested-key",
    ],
)
def test_parse_json_object_rejects_non_finite_values_and_duplicate_keys(text):
    with pytest.raises(ModelEndpointError) as error:
        client.parse_json_object(text)

    assert error.value.code == "model_json_invalid"


def test_chat_text_and_json_dispatch_through_anthropic_adapter(monkeypatch):
    calls = []

    def complete(runtime, system, user, json_mode=False):
        calls.append((runtime, system, user, json_mode))
        return ModelResult(
            '{"score": 9}' if json_mode else "facade answer",
            ModelUsage(1, 2, 3),
        )

    monkeypatch.setattr(anthropic_messages, "complete_anthropic", complete)
    assert client.chat_text(
        "system", "user", runtime=anthropic_runtime()
    ) == "facade answer"
    assert client.chat_json(
        "system",
        "evaluate",
        schema_hint='{"score": 0}',
        runtime=anthropic_runtime(),
    ) == {"score": 9}
    assert calls[0][1:] == ("system", "user", False)
    assert calls[1][1:] == (
        "system",
        'evaluate\n\n请严格输出 JSON：\n{"score": 0}',
        True,
    )


@pytest.mark.parametrize(
    ("status", "expected_code"),
    [
        (401, "model_auth_failed"),
        (403, "model_auth_failed"),
        (429, "model_rate_limited"),
        (400, "model_request_invalid"),
        (404, "model_request_invalid"),
        (500, "model_endpoint_unreachable"),
        (503, "model_endpoint_unreachable"),
    ],
)
def test_anthropic_http_statuses_use_safe_error_codes(
    monkeypatch, status, expected_code
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            json={"error": {"message": "secret sk-ant-leak"}},
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(anthropic_messages, "validate_outbound_url", lambda value: value)
    monkeypatch.setattr(anthropic_messages, "build_http_client", lambda: http_client)

    with pytest.raises(ModelEndpointError) as error:
        anthropic_messages.complete_anthropic(
            anthropic_runtime(), "system", "user"
        )

    assert error.value.code == expected_code
    assert str(error.value) == expected_code
    assert error.value.__cause__ is None
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    ("status", "exception_type", "expected_code"),
    [
        (401, openai.AuthenticationError, "model_auth_failed"),
        (403, openai.PermissionDeniedError, "model_auth_failed"),
        (429, openai.RateLimitError, "model_rate_limited"),
        (400, openai.BadRequestError, "model_request_invalid"),
        (404, openai.NotFoundError, "model_request_invalid"),
        (500, openai.InternalServerError, "model_endpoint_unreachable"),
    ],
)
def test_openai_sdk_statuses_use_same_safe_error_codes(
    monkeypatch, status, exception_type, expected_code
):
    request = httpx.Request("POST", "https://api.example.com/v1/chat/completions")
    response = httpx.Response(status, request=request)
    provider_error = exception_type(
        "upstream included sk-test",
        response=response,
        body={"secret": "sk-test"},
    )

    def fail(_runtime):
        raise provider_error

    monkeypatch.setattr(openai_chat, "build_openai_client", fail)

    with pytest.raises(ModelEndpointError) as error:
        openai_chat.complete_openai(openai_runtime(), "system", "user")

    assert error.value.code == expected_code
    assert str(error.value) == expected_code
    assert error.value.__cause__ is None
    assert "sk-test" not in str(error.value)


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        b"\xff",
        b"[]",
        b'{"content": [], "usage": {"input_tokens": 1, "output_tokens": 1}}',
        b'{"content": [{"type": "text", "text": ""}], "usage": {"input_tokens": 1, "output_tokens": 1}}',
        b'{"content": [{"type": "text", "text": 3}], "usage": {"input_tokens": 1, "output_tokens": 1}}',
        b'{"content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": "x", "output_tokens": 1}}',
    ],
)
def test_anthropic_rejects_malformed_or_empty_response(monkeypatch, body):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(anthropic_messages, "validate_outbound_url", lambda value: value)
    monkeypatch.setattr(anthropic_messages, "build_http_client", lambda: http_client)

    with pytest.raises(ModelEndpointError) as error:
        anthropic_messages.complete_anthropic(
            anthropic_runtime(), "system", "user"
        )

    assert error.value.code == "model_response_invalid"
