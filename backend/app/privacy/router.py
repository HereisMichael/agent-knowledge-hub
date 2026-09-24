"""Authenticated HTTP routes for privacy controls."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.auth.router import require_identity
from app.auth.service import Identity
from app.config import settings
from app.privacy import service


router = APIRouter(prefix="/api/account", tags=["account"])


class DeleteAccountBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=128)


@router.get("/export")
def export_account(identity: Identity = Depends(require_identity)):
    payload = service.export_account(identity)
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": (
                'attachment; filename="agent-knowledge-hub-account-export.json"'
            ),
            "Cache-Control": "no-store",
        },
    )


@router.delete("", status_code=204)
def delete_account(
    body: DeleteAccountBody,
    identity: Identity = Depends(require_identity),
):
    try:
        service.delete_account(identity, body.password)
    except service.PrivacyError as exc:
        status = 403 if exc.code == "invalid_password" else 409
        raise HTTPException(status, detail=exc.code) from exc
    response = Response(status_code=204)
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
    )
    return response
