from fastapi import APIRouter, Header, HTTPException

from app.services.school_service import get_schedule
from app.core.session_store import SESSION_STORE

router = APIRouter(prefix="/schedule", tags=["Schedule"])

from app.models.schema import ScheduleResponse

@router.get("/", response_model=ScheduleResponse)
def fetch_schedule(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    session = SESSION_STORE.get(token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        data = get_schedule(session)

        return {
            "success": True,
            "count": len(data),
            "data": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))