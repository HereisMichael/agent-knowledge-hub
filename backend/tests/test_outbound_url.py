from __future__ import annotations

import socket
import time

import httpx
import pytest

from app.llm import anthropic_messages
from app.llm.client import ModelEndpointError
from app.llm.openai_chat import build_openai_client
from app.llm.transport import (
    BoundedResponseStream,
    bound_model_response,
    build_http_client,
    run_model_call,
)
from app.security.outbound_url import UnsafeOutboundUrl, validate_outbound_url
from app.settings.service import LlmRuntime


PUBLIC_V4 = "93.184.216.34"


def _answers(*addresses: str):
    def resolve(host, port, *, type):
        assert type == socket.SOCK_STREAM
        rows = []
        for address in addresses:
            family = socket.AF_INET6 if ":" in address else socket.AF_INET
            sockaddr = (
                (address, port, 0, 0)
                if family == socket.AF_INET6
                else (address, port)
            )
            rows.append((family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr))
        return rows

    return resolve


def test_https_endpoint_is_normalized_after_all_addresses_are_public():
    normalized = validate_outbound_url(
        " HTTPS://API.Example.COM:443/v1/ ",
        resolver=_answers(PUBLIC_V4, "2606:2800:220:1:248:1893:25c8:1946"),
    )

    assert normalized == "https://api.example.com/v1/"


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.com/v1",
        "file:///etc/passwd",
        "https://user:password@api.example.com/v1",
        "https://api.example.com/v1#internal",
        "https://api.example.com/v1?redirect=http://127.0.0.1",
    ],
)
def test_unsafe_url_shapes_are_rejected(url):
    with pytest.raises(UnsafeOutboundUrl):
        validate_outbound_url(url, resolver=_answers(PUBLIC_V4))


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.8",
        "169.254.169.254",
        "100.64.0.1",
        "224.0.0.1",
        "0.0.0.0",
        "::1",
        "fc00::1",
        "fe80::1",
        "ff02::1",
    ],
)
def test_non_global_ipv4_and_ipv6_destinations_are_rejected(address):
    with pytest.raises(UnsafeOutboundUrl, match="public"):
        validate_outbound_url(
            "https://model.example.com/v1",
            resolver=_answers(address),
        )


def test_one_private_dns_answer_rejects_the_whole_host():
    with pytest.raises(UnsafeOutboundUrl, match="public"):
        validate_outbound_url(
            "https://model.example.com/v1",
            resolver=_answers(PUBLIC_V4, "127.0.0.1"),
        )


def test_unresolved_host_is_rejected():
    def unavailable(*args, **kwargs):
        raise socket.gaierror("not found")

    with pytest.raises(UnsafeOutboundUrl, match="resolve"):
        validate_outbound_url("https://missing.example/v1", resolver=unavailable)


def test_default_dns_resolution_has_a_deadline(monkeypatch):
    from app.security import outbound_url

    monkeypatch.setattr(outbound_url, "DNS_TIMEOUT_SECONDS", 0.01)

    def slow_resolution(*args, **kwargs):
        time.sleep(0.05)
        return _answers(PUBLIC_V4)(*args, **kwargs)

    monkeypatch.setattr(outbound_url.socket, "getaddrinfo", slow_resolution)

    with pytest.raises(UnsafeOutboundUrl, match="resolve"):
        validate_outbound_url("https://slow.example/v1")


def test_openai_client_disables_proxies_redirects_and_revalidates_each_request(monkeypatch):
    from app.security import outbound_url

    monkeypatch.setattr(outbound_url.socket, "getaddrinfo", _answers(PUBLIC_V4))
    client = build_openai_client(
        LlmRuntime(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            model="test-model",
            demo=False,
        )
    )
    transport = client._client

    assert transport.follow_redirects is False
    assert client.max_retries == 0
    assert transport.timeout.connect == 5.0
    assert transport.timeout.read == 60.0
    assert transport._trust_env is False

    request_hook = transport._event_hooks["request"][0]
    public_request = httpx.Request(
        "POST",
        "https://api.example.com/v1/chat/completions",
    )
    request_hook(public_request)
    assert public_request.url.host == PUBLIC_V4
    assert public_request.headers["host"] == "api.example.com"
    assert public_request.headers["accept-encoding"] == "identity"
    assert public_request.extensions["sni_hostname"] == "api.example.com"

    monkeypatch.setattr(outbound_url.socket, "getaddrinfo", _answers("127.0.0.1"))
    with pytest.raises(UnsafeOutboundUrl):
        request_hook(httpx.Request("POST", "https://api.example.com/v1/chat/completions"))
    client.close()


def test_anthropic_uses_shared_secured_http_client(monkeypatch):
    from app.security import outbound_url

    assert anthropic_messages.build_http_client is build_http_client
    monkeypatch.setattr(outbound_url.socket, "getaddrinfo", _answers(PUBLIC_V4))
    client = anthropic_messages.build_http_client()

    assert client.follow_redirects is False
    assert client.timeout.connect == 5.0
    assert client.timeout.read == 60.0
    assert client._trust_env is False

    request_hook = client._event_hooks["request"][0]
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    request_hook(request)
    assert request.url.host == PUBLIC_V4
    assert request.headers["host"] == "api.anthropic.com"
    assert request.headers["accept-encoding"] == "identity"
    assert request.extensions["sni_hostname"] == "api.anthropic.com"

    monkeypatch.setattr(outbound_url.socket, "getaddrinfo", _answers("127.0.0.1"))
    with pytest.raises(UnsafeOutboundUrl):
        request_hook(
            httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        )
    client.close()


class _Chunks(httpx.SyncByteStream):
    def __init__(self, *chunks: bytes):
        self.chunks = chunks

    def __iter__(self):
        yield from self.chunks


def test_model_response_stream_has_a_hard_size_limit():
    stream = BoundedResponseStream(
        _Chunks(b"1234", b"5678"),
        max_bytes=6,
        deadline=time.monotonic() + 10,
    )

    with pytest.raises(ModelEndpointError) as error:
        b"".join(stream)

    assert error.value.code == "model_response_too_large"


def test_model_response_stream_has_an_overall_deadline():
    stream = BoundedResponseStream(
        _Chunks(b"ok"),
        max_bytes=100,
        deadline=time.monotonic() - 1,
    )

    with pytest.raises(ModelEndpointError) as error:
        b"".join(stream)

    assert error.value.code == "model_request_deadline_exceeded"


def test_compressed_model_response_is_rejected_before_decoding():
    response = httpx.Response(
        200,
        headers={"content-encoding": "gzip"},
        stream=_Chunks(b"small-compressed-payload"),
    )

    with pytest.raises(ModelEndpointError) as error:
        bound_model_response(
            response,
            deadline=time.monotonic() + 10,
        )

    assert error.value.code == "model_response_encoding_unsupported"


def test_model_call_deadline_returns_and_closes_the_active_client(monkeypatch):
    from app.llm import transport

    monkeypatch.setattr(transport, "MODEL_REQUEST_DEADLINE_SECONDS", 0.01)

    class ActiveClient:
        closed = False

        def close(self):
            self.closed = True

    active_client = ActiveClient()
    started = time.monotonic()

    with pytest.raises(ModelEndpointError) as error:
        run_model_call(
            active_client,
            lambda: time.sleep(0.2),
        )

    assert error.value.code == "model_request_deadline_exceeded"
    assert active_client.closed is True
    assert time.monotonic() - started < 0.1
