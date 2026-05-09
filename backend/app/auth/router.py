"""HTTP routes for auth flows."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth import otp as otp_mod
from app.auth import rate_limit, security, service
from app.auth.deps import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    REFRESH_COOKIE,
    get_current_user,
    require_landlord,
)
from app.auth.schemas import (
    CsrfTokenResponse,
    ForgotPasswordRequest,
    LandlordRegisterRequest,
    LoginRequest,
    LoginSuccessResponse,
    OtpRequestRequest,
    OtpVerifyRequest,
    TenantAcceptResolveResponse,
    TenantInviteRequest,
    TenantInviteResponse,
    TenantSetPasswordRequest,
    UserOut,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.notifications import service as notifications
from app.notifications.models import NotificationChannel
from app.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
_session_log = get_logger("auth.session")


def _set_session_cookies(response: Response, *, access: str, refresh: str, csrf: str) -> None:
    settings = get_settings()
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        httponly=True,
        max_age=settings.jwt_access_ttl_minutes * 60,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        httponly=True,
        max_age=settings.jwt_refresh_ttl_days * 86400,
        path="/auth",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
    )
    # CSRF cookie is intentionally NOT httpOnly — JS reads it and echoes it
    # via the X-CSRF-Token header on state-changing requests.
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        httponly=False,
        max_age=settings.jwt_access_ttl_minutes * 60,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
    )


def _clear_session_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name)
    response.delete_cookie(REFRESH_COOKIE, path="/auth")


async def _ensure_under_rate_limit(
    redis: Redis,
    bucket: str,
    *,
    limit: int,
    window_seconds: int,
) -> None:
    if not await rate_limit.hit(redis, bucket=bucket, limit=limit, window_seconds=window_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="too many requests"
        )


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


# ─── Landlord self-signup ──────────────────────────────────────────────
@router.post("/landlord/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def landlord_register(
    body: LandlordRegisterRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(db_session)],
) -> UserOut:
    if not service.is_strong_password(body.password):
        raise HTTPException(status_code=400, detail="password must be 8+ chars with letters & digits")
    try:
        user = await service.register_landlord(
            db,
            name=body.name,
            phone=body.phone,
            email=body.email,
            password=body.password,
        )
    except service.DuplicateUser:
        raise HTTPException(status_code=409, detail="phone or email already registered")
    await db.commit()
    access = security.create_token(subject=str(user.id), type_="access")
    refresh = security.create_token(subject=str(user.id), type_="refresh")
    csrf = service.generate_csrf_token()
    _set_session_cookies(response, access=access, refresh=refresh, csrf=csrf)
    user_out = UserOut.model_validate(user)
    _session_log.info(
        "session_minted",
        reason="landlord_register",
        user_id=str(user.id),
        role=user.role.value,
    )
    return user_out


# ─── Login ────────────────────────────────────────────────────────────
@router.post("/login", response_model=LoginSuccessResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(db_session)],
) -> LoginSuccessResponse:
    redis = await otp_mod.open_redis()
    try:
        await _ensure_under_rate_limit(
            redis,
            f"rl:login:{_client_ip(request)}",
            limit=10,
            window_seconds=60,
        )
        try:
            user = await service.authenticate(
                db, identifier=body.identifier, password=body.password
            )
        except service.InvalidCredentials:
            raise HTTPException(status_code=401, detail="invalid credentials")

        if not user.is_verified:
            raise HTTPException(status_code=403, detail="account not verified")

        access = security.create_token(subject=str(user.id), type_="access")
        refresh = security.create_token(subject=str(user.id), type_="refresh")
        csrf = service.generate_csrf_token()
        _set_session_cookies(response, access=access, refresh=refresh, csrf=csrf)
        out = LoginSuccessResponse(csrf_token=csrf, user=UserOut.model_validate(user))
        _session_log.info(
            "session_minted",
            reason="login",
            user_id=str(user.id),
            role=user.role.value,
        )
        return out
    finally:
        await redis.aclose()


# ─── Logout ───────────────────────────────────────────────────────────
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    _clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


# ─── Refresh ──────────────────────────────────────────────────────────
@router.post("/refresh", response_model=CsrfTokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(db_session)],
) -> CsrfTokenResponse:
    import jwt as _jwt
    refresh_cookie = request.cookies.get(REFRESH_COOKIE)
    if not refresh_cookie:
        raise HTTPException(status_code=401, detail="no refresh token")
    try:
        payload = security.decode_token(refresh_cookie, expected_type="refresh")
    except _jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid refresh token")

    user = await service.get_user_by_id(db, payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="user gone")
    access = security.create_token(subject=str(user.id), type_="access")
    new_refresh = security.create_token(subject=str(user.id), type_="refresh")
    csrf = service.generate_csrf_token()
    _set_session_cookies(response, access=access, refresh=new_refresh, csrf=csrf)
    return CsrfTokenResponse(csrf_token=csrf)


# ─── Whoami ───────────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
async def whoami(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut.model_validate(user)


# ─── Tenant invite (landlord) ─────────────────────────────────────────
@router.post(
    "/landlord/tenants/invite",
    response_model=TenantInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_tenant(
    body: TenantInviteRequest,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> TenantInviteResponse:
    try:
        user, token = await service.create_tenant_invite(
            db,
            landlord=landlord,
            name=body.name,
            phone=body.phone,
            email=body.email,
        )
    except service.DuplicateUser:
        raise HTTPException(status_code=409, detail="phone already registered")

    accept_url = f"/auth/tenant/accept/{token}"
    await notifications.send(
        db,
        recipient=user,
        channel=NotificationChannel.SMS,
        template="tenant_invite",
        context={"name": user.name, "accept_url": accept_url},
    )
    await db.commit()
    return TenantInviteResponse(user_id=user.id, accept_url=accept_url)


# ─── Tenant accept (token resolution) ─────────────────────────────────
@router.get("/tenant/accept/{token}", response_model=TenantAcceptResolveResponse)
async def tenant_accept_resolve(
    token: str,
    db: Annotated[AsyncSession, Depends(db_session)],
) -> TenantAcceptResolveResponse:
    try:
        user = await service.resolve_invite(db, token)
    except service.InvalidInviteToken:
        raise HTTPException(status_code=404, detail="invalid or expired invite")
    return TenantAcceptResolveResponse(user_id=user.id, name=user.name, phone=user.phone)


# ─── OTP request ──────────────────────────────────────────────────────
@router.post("/tenant/otp/request", status_code=status.HTTP_204_NO_CONTENT)
async def otp_request(
    body: OtpRequestRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(db_session)],
) -> Response:
    user = await service.get_user_by_id(db, body.user_id)
    if user is None or user.is_verified:
        raise HTTPException(status_code=404, detail="user not found or already verified")

    redis = await otp_mod.open_redis()
    try:
        await _ensure_under_rate_limit(
            redis,
            f"rl:otp_request:{user.id}",
            limit=3,
            window_seconds=3600,
        )
        code = await otp_mod.issue(redis, str(user.id))
    finally:
        await redis.aclose()

    from app.core.config import get_settings

    await notifications.send(
        db,
        recipient=user,
        channel=NotificationChannel.SMS,
        template="otp",
        context={"code": code, "ttl_min": get_settings().otp_ttl_minutes},
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── OTP verify (no password set yet) ─────────────────────────────────
@router.post("/tenant/otp/verify", status_code=status.HTTP_204_NO_CONTENT)
async def otp_verify(
    body: OtpVerifyRequest,
    db: Annotated[AsyncSession, Depends(db_session)],
) -> Response:
    user = await service.get_user_by_id(db, body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    redis = await otp_mod.open_redis()
    try:
        ok = await otp_mod.verify(redis, str(user.id), body.code)
    finally:
        await redis.aclose()
    if not ok:
        raise HTTPException(status_code=401, detail="invalid or expired code")
    # Re-store a one-time "password reset" marker so set_password requires
    # the same code one more time. For MVP simplicity we re-issue an OTP-
    # less marker by accepting the next call without a code re-check.
    # To keep the flow simple in tests, we expose a separate
    # `tenant/set-password` route that accepts code+password atomically.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── Set password (single atomic call: code + new password) ──────────
@router.post("/tenant/set-password", response_model=UserOut)
async def tenant_set_password(
    body: TenantSetPasswordRequest,
    db: Annotated[AsyncSession, Depends(db_session)],
) -> UserOut:
    if not service.is_strong_password(body.password):
        raise HTTPException(status_code=400, detail="weak password")
    user = await service.get_user_by_id(db, body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    redis = await otp_mod.open_redis()
    try:
        ok = await otp_mod.verify(redis, str(user.id), body.code)
    finally:
        await redis.aclose()
    if not ok:
        raise HTTPException(status_code=401, detail="invalid or expired code")

    user = await service.set_tenant_password(db, user_id=user.id, new_password=body.password)
    await db.commit()
    return UserOut.model_validate(user)


# ─── Forgot password ──────────────────────────────────────────────────
@router.post("/forgot", status_code=status.HTTP_204_NO_CONTENT)
async def forgot(
    body: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(db_session)],
) -> Response:
    """Soft-handle: always 204 to avoid account enumeration."""
    user = await service.get_user_by_identifier(db, body.identifier)
    if user is not None:
        # Phase 7 will send a real email/SMS via Notifications module.
        from app.core.logging import get_logger

        get_logger("auth.forgot").info(
            "forgot_password_link_issued",
            user_id=str(user.id),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
