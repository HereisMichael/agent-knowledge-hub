"""HTTP adapter for invite authentication."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

from app.auth import service
from app.auth.service import Identity
from app.config import settings


router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    invite_code: str = Field(max_length=256)


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)


def _public_identity(identity: Identity) -> dict:
    return {
        "id": identity.user_id,
        "email": identity.email,
        "role": identity.role,
    }


def _cookie_secure() -> bool:
    return settings.app_env.strip().lower() == "production"


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 60 * 60,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )


def _raise_auth_error(error: service.AuthError) -> None:
    status_by_code = {
        "invalid_credentials": 401,
        "invalid_session": 401,
        "invalid_invite": 403,
        "email_exists": 409,
        "invalid_email": 422,
        "weak_password": 422,
    }
    raise HTTPException(status_by_code.get(error.code, 401), detail=error.code)


def require_identity(request: Request) -> Identity:
    existing = getattr(request.state, "identity", None)
    if existing is not None:
        return existing
    token = request.cookies.get(settings.session_cookie_name, "")
    try:
        return service.authenticate(token)
    except service.AuthError as error:
        raise HTTPException(401, detail="authentication_required") from error


async def enforce_session(request: Request, call_next):
    path = request.url.path
    is_public = (
        request.method == "OPTIONS"
        or path == "/api/health"
        or path.startswith("/api/health/")
        or path.startswith("/api/auth/")
        or not path.startswith("/api/")
    )
    if is_public:
        return await call_next(request)
    try:
        request.state.identity = service.authenticate(
            request.cookies.get(settings.session_cookie_name, "")
        )
    except service.AuthError:
        return JSONResponse(
            status_code=401,
            content={"detail": "authentication_required"},
        )
    return await call_next(request)


def require_admin(identity: Identity = Depends(require_identity)) -> Identity:
    if identity.role != "admin":
        raise HTTPException(403, detail="admin_required")
    return identity


@router.post("/register", status_code=201)
def register(body: RegisterBody, response: Response):
    try:
        grant = service.register(body.email, body.password, body.invite_code)
    except service.AuthError as error:
        _raise_auth_error(error)
    _set_session_cookie(response, grant.token)
    return {"user": _public_identity(grant.identity)}


@router.post("/login")
def login(body: LoginBody, response: Response):
    try:
        grant = service.login(body.email, body.password)
    except service.AuthError as error:
        _raise_auth_error(error)
    _set_session_cookie(response, grant.token)
    return {"user": _public_identity(grant.identity)}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response) -> None:
    token = request.cookies.get(settings.session_cookie_name, "")
    service.logout(token)
    _clear_session_cookie(response)


@router.get("/me")
def me(identity: Identity = Depends(require_identity)):
    return {"user": _public_identity(identity)}
