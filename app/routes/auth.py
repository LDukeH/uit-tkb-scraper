import time
import uuid
from fastapi import APIRouter, HTTPException, Header, Request

from app.services.school_service import (
    login_and_get_session,
    save_session,
    SESSION_STORE,
)
from app.schemas.auth import LoginRequest, LoginResponse, LogoutResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate with UIT credentials and receive a session token",
    response_description="Login successful with session token",
)
def login(data: LoginRequest, request: Request = None):
    tc = getattr(request.state, "timing", None) if request else None

    # Measure UIT login
    t0 = time.perf_counter()
    session = login_and_get_session(data.username, data.password)
    login_ms = (time.perf_counter() - t0) * 1000.0

    if not session:
        raise HTTPException(status_code=401, detail="Đăng nhập UIT thất bại.")

    token = str(uuid.uuid4())
    save_session(token, session, data.username, data.password)

    timings = {"uit_login_ms": round(login_ms, 1)}

    return {
        "success": True,
        "token": token,
        "timings_ms": timings,
    }


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="User logout",
    description="Invalidate the current session token",
    response_description="Logout successful",
)
def logout(authorization: str = Header(None)):
    if not authorization:
        return {"success": True}

    token = authorization.replace("Bearer ", "")
    SESSION_STORE.pop(token, None)

    return {"success": True}
