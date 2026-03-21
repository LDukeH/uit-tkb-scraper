from fastapi import APIRouter, HTTPException
import uuid

from app.models.schema import LoginRequest, LoginResponse
from app.services.school_service import login_and_get_session
from app.core.session_store import SESSION_STORE

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    session = login_and_get_session(data.username, data.password)

    if not session:
        raise HTTPException(status_code=401, detail="Login failed")

    token = str(uuid.uuid4())
    SESSION_STORE[token] = session

    return {
        "success": True,
        "token": token
    }