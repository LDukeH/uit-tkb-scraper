from fastapi import APIRouter, HTTPException
from app.services.school_service import get_announcements
from app.models.schema import AnnouncementResponse

router = APIRouter(prefix="/announcements", tags=["Announcements"])

@router.get("/", response_model=AnnouncementResponse)
def fetch_announcements():
    data = get_announcements()
    if not data:
        raise HTTPException(status_code=500, detail="Could not fetch announcements")
    return {"success": True, "data": data}

