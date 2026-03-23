from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
import uuid

from app.services.school_service import (
    login_and_get_session,
    save_session,
    SESSION_STORE
)

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(data: LoginRequest):
    session = login_and_get_session(data.username, data.password)

    if not session:
        raise HTTPException(status_code=401, detail="Đăng nhập UIT thất bại.")

    token = str(uuid.uuid4())
    save_session(token, session, data.username, data.password)

    return {
        "success": True,
        "token": token
    }


@router.post("/logout")
def logout(authorization: str = Header(None)):
    if not authorization:
        return {"success": True}

    token = authorization.replace("Bearer ", "")
    SESSION_STORE.pop(token, None)

    return {"success": True}