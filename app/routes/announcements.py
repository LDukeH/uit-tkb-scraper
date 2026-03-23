from fastapi import APIRouter, HTTPException
from app.core.db import announcement_collection

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get("/")
def get_announcements():
    try:
        data = list(
            announcement_collection
            .find({}, {"_id": 0})
            .sort("date", -1)
            .limit(50)
        )

        return {
            "success": True,
            "count": len(data),
            "data": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))