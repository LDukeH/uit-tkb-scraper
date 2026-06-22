import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query

from app.services.moodle_service import MoodleClient
from app.services.school_service import get_valid_session, SESSION_STORE
from app.core.db import deadlines_collection
from app.schemas.deadline import DeadlineResponse

router = APIRouter(prefix="/deadlines", tags=["Deadlines"])


@router.get(
    "/",
    response_model=DeadlineResponse,
    summary="Get deadlines and events",
    description="Retrieve deadlines and events from Moodle for a specific month/year",
    response_description="List of deadlines and events with caching support",
)
def deadlines(
    year: Optional[int] = Query(
        default=None,
        ge=2000,
        le=2100,
        description="Year to fetch deadlines for (defaults to current year)",
        examples=[2024, 2025],
    ),
    month: Optional[int] = Query(
        default=None,
        ge=1,
        le=12,
        description="Month to fetch deadlines for (defaults to current month)",
        examples=[1, 12],
    ),
    refresh: bool = Query(
        default=False,
        description="Force refresh data from Moodle, bypassing cache",
        examples=[True, False],
    ),
    authorization: str = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    session = get_valid_session(token)

    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    try:
        username = SESSION_STORE.get(token, {}).get("auth_data", {}).get("username")
        password = SESSION_STORE.get(token, {}).get("auth_data", {}).get("password")

        now = datetime.now()
        yr = year or now.year
        mo = month or now.month

        db_time_ms = None
        if username and not refresh:
            t0 = time.perf_counter()
            cached = deadlines_collection.find_one(
                {"user_id": username, "year": yr, "month": mo},
                {"_id": 0},
            )
            if cached and cached.get("events"):
                return {
                    "success": True,
                    "count": len(cached["events"]),
                    "data": cached["events"],
                    "cached": True,
                }

        t1 = time.perf_counter()
        client = MoodleClient(username, password)
        if not client.login():
            raise HTTPException(status_code=401, detail="Moodle login failed")
        data = client.get_deadlines(yr, mo)
        scrape_time_ms = (time.perf_counter() - t1) * 1000.0

        save_time_ms = None
        if username:
            t2 = time.perf_counter()
            try:
                deadlines_collection.update_one(
                    {"user_id": username, "year": yr, "month": mo},
                    {"$set": {
                        "user_id": username,
                        "year": yr,
                        "month": mo,
                        "events": data,
                        "updated_at": datetime.utcnow(),
                        "expires_at": datetime.utcnow() + timedelta(hours=1),
                        "source": "courses.uit.edu.vn",
                    }},
                    upsert=True,
                )
            except Exception:
                pass
            save_time_ms = (time.perf_counter() - t2) * 1000.0

        return {
            "success": True,
            "count": len(data),
            "data": data,
            "cached": False,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
