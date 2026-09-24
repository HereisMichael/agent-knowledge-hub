"""Validation policy for user-controlled outbound model endpoints."""

from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import BoundedSemaphore
from collections.abc import Callable
from urllib.parse import SplitResult, urlsplit, urlunsplit


MAX_URL_LENGTH = 2048
DNS_TIMEOUT_SECONDS = 3.0
DNS_MAX_CONCURRENCY = 4
Resolver = Callable[..., list[tuple]]
_DNS_EXECUTOR = ThreadPoolExecutor(
    max_workers=DNS_MAX_CONCURRENCY,
    thread_name_prefix="safe-dns",
)
_DNS_SLOTS = BoundedSemaphore(DNS_MAX_CONCURRENCY)


class UnsafeOutboundUrl(ValueError):
    """Raised when an outbound URL could expose a protected network target."""


def _reject(message: str) -> None:
    raise UnsafeOutboundUrl(message)


def _normalize_host(hostname: str) -> str:
    host = hostname.rstrip(".").lower()
    if not host or "%" in host or "\\" in host:
        _reject("model endpoint host is invalid")
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise UnsafeOutboundUrl("model endpoint host is invalid") from exc


def _validate_resolved_addresses(
    hostname: str,
    port: int,
    resolver: Resolver,
) -> list[str]:
    try:
        answers = resolver(hostname, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError, UnicodeError) as exc:
        raise UnsafeOutboundUrl("model endpoint host could not resolve") from exc
    if not answers:
        _reject("model endpoint host could not resolve")

    addresses: list[str] = []
    for answer in answers:
        try:
            address = answer[4][0]
            parsed = ipaddress.ip_address(address)
        except (IndexError, TypeError, ValueError) as exc:
            raise UnsafeOutboundUrl(
                "model endpoint resolved to an invalid address"
            ) from exc
        normalized_address = str(parsed)
        if normalized_address not in addresses:
            addresses.append(normalized_address)
        if (
            not parsed.is_global
            or parsed.is_multicast
            or parsed.is_unspecified
            or parsed.is_reserved
            or parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_private
        ):
            _reject("model endpoint must resolve only to public addresses")
    if not addresses:
        _reject("model endpoint host could not resolve")
    return addresses


def bounded_getaddrinfo(hostname: str, port: int, *, type: int) -> list[tuple]:
    if not _DNS_SLOTS.acquire(blocking=False):
        raise OSError("DNS resolver capacity exhausted")
    future = _DNS_EXECUTOR.submit(
        socket.getaddrinfo,
        hostname,
        port,
        type=type,
    )

    def release_slot(_future) -> None:
        _DNS_SLOTS.release()

    future.add_done_callback(release_slot)
    try:
        return future.result(timeout=DNS_TIMEOUT_SECONDS)
    except FutureTimeout as exc:
        future.cancel()
        raise OSError("DNS resolution deadline exceeded") from exc


def validate_outbound_url(
    value: str,
    *,
    resolver: Resolver | None = None,
    _address_sink: list[str] | None = None,
) -> str:
    raw = (value or "").strip()
    if not raw or len(raw) > MAX_URL_LENGTH:
        _reject("model endpoint URL is empty or too long")
    if any(ord(character) < 32 for character in raw) or "\\" in raw:
        _reject("model endpoint URL contains invalid characters")

    try:
        parsed = urlsplit(raw)
        port = parsed.port or 443
        hostname = parsed.hostname
    except ValueError as exc:
        raise UnsafeOutboundUrl("model endpoint URL is invalid") from exc

    if parsed.scheme.lower() != "https":
        _reject("model endpoint must use HTTPS")
    if not hostname or parsed.username is not None or parsed.password is not None:
        _reject("model endpoint must have a host and no embedded credentials")
    if parsed.fragment or parsed.query:
        _reject("model endpoint must not contain a query or fragment")
    if port < 1 or port > 65535:
        _reject("model endpoint port is invalid")

    normalized_host = _normalize_host(hostname)
    addresses = _validate_resolved_addresses(
        normalized_host,
        port,
        resolver or bounded_getaddrinfo,
    )
    if _address_sink is not None:
        _address_sink.extend(addresses)

    try:
        literal = ipaddress.ip_address(normalized_host)
    except ValueError:
        display_host = normalized_host
    else:
        display_host = f"[{literal}]" if literal.version == 6 else str(literal)
    netloc = display_host if port == 443 else f"{display_host}:{port}"
    normalized = SplitResult(
        scheme="https",
        netloc=netloc,
        path=parsed.path,
        query="",
        fragment="",
    )
    return urlunsplit(normalized)


def validate_httpx_request(request) -> None:
    addresses: list[str] = []
    normalized = validate_outbound_url(
        str(request.url),
        _address_sink=addresses,
    )
    parsed = urlsplit(normalized)
    hostname = parsed.hostname
    if not hostname or not addresses:
        _reject("model endpoint could not be pinned")
    request.headers["host"] = parsed.netloc
    request.headers["accept-encoding"] = "identity"
    request.extensions["sni_hostname"] = hostname
    request.url = request.url.copy_with(host=addresses[0])


def outbound_origin(value: str) -> str:
    try:
        parsed = urlsplit((value or "").strip())
        hostname = parsed.hostname
        port = parsed.port or 443
    except ValueError as exc:
        raise UnsafeOutboundUrl("model endpoint URL is invalid") from exc
    if parsed.scheme.lower() != "https" or not hostname:
        _reject("model endpoint must use HTTPS and include a host")
    normalized_host = _normalize_host(hostname)
    try:
        literal = ipaddress.ip_address(normalized_host)
    except ValueError:
        display_host = normalized_host
    else:
        display_host = f"[{literal}]" if literal.version == 6 else str(literal)
    return (
        f"https://{display_host}"
        if port == 443
        else f"https://{display_host}:{port}"
    )
