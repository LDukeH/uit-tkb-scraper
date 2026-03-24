from app.services.school_service import get_all_announcements
from app.services.data_insert import insert_announcements
from app.services.analyze_service import label_announcements

from fastapi import APIRouter, HTTPException
import os

router = APIRouter(prefix="/internal_scraper", tags=["Internal"])

SECRET_KEY = os.getenv("SCRAPER_SECRET")


@router.get("/")
def run_scraper(key: str):
    if key != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = get_all_announcements()
    data = label_announcements(data)
    insert_announcements(data)

    return {"success": True, "count": len(data)}