import time
from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
from app.core.db import get_announcement_collection
from app.schemas.announcement import AnnouncementListResponse, AnnouncementDetailResponse

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get(
    "/",
    response_model=AnnouncementListResponse,
    summary="List announcements",
    description="Get a paginated list of announcements, optionally filtered by topic",
    response_description="Paginated list of announcements",
)
def get_announcements(
    topic: Optional[str] = Query(
        default=None,
        description="Filter announcements by topic/category",
        examples=["Đăng ký học phần", "Thi"],
    ),
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination",
        examples=[0, 15, 30],
    ),
    limit: int = Query(
        default=15,
        ge=1,
        le=100,
        description="Maximum number of records to return",
        examples=[15, 30, 50],
    ),
    request: Request = None,
):
    t_request = time.perf_counter()
    timings = {}

    try:
        query = {}
        if topic is not None:
            query["topic"] = topic

        t0 = time.perf_counter()
        data = list(
            get_announcement_collection()
            .find(query, {"_id": 0, "details": 0})
            .sort("date", -1)
            .skip(skip)
            .limit(limit)
        )
        timings["db_query_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

        total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
        timings["total_ms"] = total_ms

        return {
            "success": True,
            "count": len(data),
            "data": data,
            "timings_ms": timings,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{node_id}",
    response_model=AnnouncementDetailResponse,
    summary="Get announcement details",
    description="Get full details of a specific announcement by its node ID",
    response_description="Full announcement details including content and related articles",
)
def get_announcement(node_id: str, request: Request = None):
    t_request = time.perf_counter()
    timings = {}

    try:
        t0 = time.perf_counter()
        doc = get_announcement_collection().find_one(
            {"_id": node_id},
            {"_id": 0}
        )
        timings["db_query_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

        if not doc:
            raise HTTPException(status_code=404, detail="Announcement not found")

        total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
        timings["total_ms"] = total_ms

        return {
            "success": True,
            "data": doc,
            "timings_ms": timings,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
