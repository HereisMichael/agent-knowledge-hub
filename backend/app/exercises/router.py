"""Authenticated LLM-101-CN practice endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.auth.router import require_identity
from app.auth.service import Identity
from app.db import store
from app.exercises import catalog
from app.exercises.service import grade_attempt
from app.progress.radar import build_exercise_progress


router = APIRouter(prefix="/api/exercises", tags=["exercises"])


class AttemptBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: dict[str, str | int]
    notes: str = Field(default="", max_length=4000)
    request_reveal: bool = False


@router.get("")
def exercises_list(
    level: int | None = Query(default=None, ge=1, le=4),
    topic: str | None = Query(default=None, max_length=100),
    kind: str | None = Query(default=None, max_length=50),
    _identity: Identity = Depends(require_identity),
):
    items = catalog.list_exercises(level=level, topic=topic, kind=kind)
    return {"items": items, "total": len(items)}


@router.get("/progress")
def exercises_progress(identity: Identity = Depends(require_identity)):
    return {
        **store.get_exercise_progress(identity.user_id),
        **build_exercise_progress(identity.user_id),
    }


@router.get("/{exercise_id}")
def exercises_detail(exercise_id: str, _identity: Identity = Depends(require_identity)):
    item = catalog.get_exercise(exercise_id)
    if item is None:
        raise HTTPException(404, detail="exercise_not_found")
    return item


@router.post("/{exercise_id}/attempts")
def exercises_submit(exercise_id: str, body: AttemptBody, identity: Identity = Depends(require_identity)):
    item = catalog.get_exercise(exercise_id)
    if item is None:
        raise HTTPException(404, detail="exercise_not_found")
    allowed = {"choice"} if item["kind"] == "single_choice" else (
        {blank["id"] for blank in item.get("blanks", [])} if item["kind"] == "blank_fill" else {"submission"}
    )
    if not body.answers or not set(body.answers).issubset(allowed):
        raise HTTPException(422, detail="exercise_answer_invalid")
    if any(len(str(value)) > 20_000 for value in body.answers.values()) or sum(len(str(value)) for value in body.answers.values()) > 40_000:
        raise HTTPException(413, detail="exercise_attempt_too_large")
    reference = catalog.load_answer(exercise_id)
    if body.request_reveal and (reference is None or not reference.get("reference_markdown")):
        raise HTTPException(409, detail="exercise_answer_not_available")
    result = grade_attempt(item, body.answers, reference)
    attempt = store.create_exercise_attempt(
        identity.user_id, exercise_id, body.answers, result.status, result.score,
        body.notes, feedback=result.feedback, revealed=body.request_reveal,
    )
    response = {
        "attempt_id": attempt["id"],
        **result.public_payload,
        "progress": store.get_exercise_progress(identity.user_id),
    }
    if body.request_reveal:
        response["reference_markdown"] = reference["reference_markdown"]
    return response
