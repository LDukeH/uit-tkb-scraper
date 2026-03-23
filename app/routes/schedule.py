from fastapi import APIRouter, HTTPException, Header

from app.services.school_service import (
    get_schedule,
    get_valid_session
)

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.get("/")
def schedule(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    session = get_valid_session(token)

    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    try:
        data = get_schedule(session)
        return {
            "success": True,
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))