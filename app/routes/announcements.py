from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.core.db import announcement_collection

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get("/")
def get_announcements(topic: Optional[str] = Query(default=None)):
    try:
        # Build query condition
        query = {}
        if topic is not None:
            query["topic"] = topic

        data = list(
            announcement_collection
            .find(query, {"_id": 0})
            .sort("date", -1)
            .limit(15)
        )

        return {
            "success": True,
            "count": len(data),
            "data": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))