from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.core.db import announcement_collection

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get("/")
def get_announcements(
    topic: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=15, ge=1, le=100),
):
    try:
        query = {}
        if topic is not None:
            query["topic"] = topic

        data = list(
            announcement_collection
            .find(query, {"_id": 0, "details": 0})
            .sort("date", -1)
            .skip(skip)
            .limit(limit)
        )

        return {
            "success": True,
            "count": len(data),
            "data": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{node_id}")
def get_announcement(node_id: str):
    try:
        doc = announcement_collection.find_one(
            {"_id": node_id},
            {"_id": 0}
        )

        if not doc:
            raise HTTPException(status_code=404, detail="Announcement not found")

        return {
            "success": True,
            "data": doc
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))