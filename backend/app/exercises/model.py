"""Public exercise scoring result, intentionally excluding private answers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GradeResult:
    status: str
    score: int | None
    feedback: dict[str, object]
    public_payload: dict[str, object]
