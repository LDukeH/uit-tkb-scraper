from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import uuid

from app.services.school_service import login_and_get_session, get_schedule



app = FastAPI()

SESSION_STORE = {}  

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
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


@app.get("/schedule")
def schedule(authorization: str = Header(None)):
    """
    Header:
    Authorization: Bearer <token>
    """

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        token = authorization.replace("Bearer ", "")
    except:
        raise HTTPException(status_code=401, detail="Invalid token format")

    session = SESSION_STORE.get(token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        data = get_schedule(session)

        return {
            "success": True,
            "count": len(data),
            "data": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/auth/logout")
def logout(authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "")
    SESSION_STORE.pop(token, None)
    return {"success": True}