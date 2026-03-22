from fastapi import APIRouter, Header, HTTPException

from app.services.school_service import get_schedule,get_valid_session
from app.core.session_store import SESSION_STORE

router = APIRouter(prefix="/schedule", tags=["Schedule"])

from app.models.schema import ScheduleResponse

@router.get("/")
def fetch_schedule(authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "")
    
    session = get_valid_session(token)
    
    if not session:
        raise HTTPException(status_code=401, detail="Session expired and re-login failed")

    try:
        data = get_schedule(session)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Lỗi lấy dữ liệu")