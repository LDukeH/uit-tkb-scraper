from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import uuid
from typing import List, Optional

from app.services.school_service import (
    login_and_get_session, 
    get_schedule, 
    get_valid_session, 
    save_session,
    get_announcements,
    SESSION_STORE
)

app = FastAPI(title="UIT Student API")

class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/")
def root():
    return {"message": "UIT School API is running!", "status": "healthy"}

@app.post("/auth/login")
def login(data: LoginRequest):
    session = login_and_get_session(data.username, data.password)

    if not session:
        raise HTTPException(status_code=401, detail="Đăng nhập UIT thất bại. Kiểm tra lại MSSV/Mật khẩu.")

    token = str(uuid.uuid4())

    # luu tam lai username va password de tu dong dang nhap
    save_session(token, session, data.username, data.password)

    return {
        "success": True,
        "token": token
    }

@app.get("/schedule")
def schedule(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    
    # check session
    session = get_valid_session(token)

    if not session:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")

    try:
        data = get_schedule(session)
        return {
            "success": True,
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lấy TKB thất bại: {str(e)}")

@app.get("/announcements")
def announcements():
    data = get_announcements()
    if not data:
        raise HTTPException(status_code=500, detail="Không thể lấy thông báo từ UIT")
    
    return {
        "success": True,
        "count": len(data),
        "data": data
    }

@app.post("/auth/logout")
def logout(authorization: str = Header(None)):
    if not authorization:
        return {"success": True}
    
    token = authorization.replace("Bearer ", "")
    SESSION_STORE.pop(token, None)
    return {"success": True}