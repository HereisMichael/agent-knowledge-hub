from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl

from app.auth.router import require_admin
from app.auth.service import Identity
from app.db import store


router = APIRouter(prefix="/api/admin/content/sources", tags=["content-governance"])


class ContentSourceBody(BaseModel):
    source_path: str = Field(min_length=1, max_length=1024)
    source_url: HttpUrl
    source_title: str | None = Field(default=None, max_length=500)
    publisher: str | None = Field(default=None, max_length=300)
    retrieved_at: datetime
    rights_note: str | None = Field(default=None, max_length=4000)
    content_item_id: str | None = Field(default=None, max_length=100)


class TakedownBody(BaseModel):
    action: Literal["requested", "removed", "restored"]
    reason: str = Field(min_length=3, max_length=4000)


@router.post("", status_code=201)
def create_source(
    body: ContentSourceBody,
    _identity: Identity = Depends(require_admin),
):
    if body.content_item_id:
        try:
            store.get_content_item(body.content_item_id)
        except KeyError as exc:
            raise HTTPException(422, "content_item_not_found") from exc
    return store.create_content_source(
        source_path=body.source_path,
        source_url=str(body.source_url),
        source_title=body.source_title,
        publisher=body.publisher,
        retrieved_at=body.retrieved_at.isoformat(),
        rights_note=body.rights_note,
        content_item_id=body.content_item_id,
    )


@router.get("")
def list_sources(
    status: Literal["active", "takedown_requested", "removed"] | None = Query(
        default=None
    ),
    _identity: Identity = Depends(require_admin),
):
    return {"sources": store.list_content_sources(status)}


@router.get("/{source_id}")
def source_detail(
    source_id: str,
    _identity: Identity = Depends(require_admin),
):
    try:
        source = store.get_content_source(source_id)
    except KeyError as exc:
        raise HTTPException(404, "source_not_found") from exc
    return {
        "source": source,
        "events": store.list_content_takedown_events(source_id),
    }


@router.post("/{source_id}/takedown")
def record_takedown(
    source_id: str,
    body: TakedownBody,
    identity: Identity = Depends(require_admin),
):
    try:
        return store.record_content_takedown(
            source_id,
            identity.user_id,
            body.action,
            body.reason,
        )
    except KeyError as exc:
        raise HTTPException(404, "source_not_found") from exc
