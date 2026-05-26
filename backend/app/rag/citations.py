from __future__ import annotations

from typing import Any


def retrieved_source_ids(chunks: list) -> set[str]:
    return {c.source_id for c in chunks}


def validate_citation_list(
    citations: list[str] | None, allowed: set[str], *, strict: bool = False
) -> tuple[list[str], list[str]]:
    if not citations:
        return [], []
    valid = [c for c in citations if c in allowed]
    invalid = [c for c in citations if c not in allowed]
    if strict and invalid:
        return valid, invalid
    return valid, invalid


def apply_citation_guard(result: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    citations = result.get("citations")
    if isinstance(citations, list):
        valid, invalid = validate_citation_list(citations, allowed)
        result["citations"] = valid
        if invalid:
            result["citation_warnings"] = invalid
    return result
