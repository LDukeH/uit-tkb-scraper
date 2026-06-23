import time
import logging
from fastapi import APIRouter, HTTPException, Header, Request

logger = logging.getLogger("uit.routes.schedule")

from app.services.school_service import (
    get_schedule,
    get_valid_session,
    get_credentials_from_db,
    login_and_get_session,
    save_session,
    load_cached_schedule,
    save_schedule,
    load_cached_exam_schedule,
    save_exam_schedule,
    SESSION_STORE,
)
from app.services.school_service import get_exam_schedule
from app.services.school.schedule import transform_exam_schedule
from app.schemas.schedule import ScheduleResponse
from app.schemas.exam import ExamScheduleResponse

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.get(
    "/",
    response_model=ScheduleResponse,
    summary="Get class schedule",
    description="Retrieve the weekly class schedule for the authenticated student",
    response_description="Weekly class schedule with all subjects",
)
def schedule(authorization: str = Header(None), request: Request = None):
    t_request = time.perf_counter()
    timings = {}

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    session = get_valid_session(token)

    # If session not in cache or expired, try to re-login
    if not session:
        username, password = get_credentials_from_db(token)
        if username and password:
            logger.info("[SCHEDULE] Re-login required for user=%s", username)
            new_session = login_and_get_session(username, password)
            if new_session:
                save_session(token, new_session, username, password)
                session = new_session
                logger.info("[SCHEDULE] Re-login successful for user=%s", username)
            else:
                logger.warning("[SCHEDULE] Re-login failed for user=%s", username)
                raise HTTPException(status_code=401, detail="Session expired - re-login failed")
        else:
            logger.warning("[SCHEDULE] No credentials found for token=%s", token[:8])
            raise HTTPException(status_code=401, detail="Session not found")

    try:
        username = SESSION_STORE.get(token, {}).get("auth_data", {}).get("username")

        # DB Cache read
        cache_check_time = time.perf_counter()
        if username:
            t0 = time.perf_counter()
            cached = load_cached_schedule(username)
            timings["db_read_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

            if cached and cached.get("schedule"):
                total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
                timings["total_ms"] = total_ms
                logger.info("[CACHE] HIT for user=%s, db_read=%.1fms, total=%.1fms", username, timings["db_read_ms"], total_ms)
                return {"success": True, "count": len(cached.get("schedule")), "data": cached.get("schedule"), "cached": True, "timings_ms": timings}
            else:
                logger.info("[CACHE] MISS for user=%s, db_read=%.1fms", username, timings["db_read_ms"])

        # Scrape from UIT
        t1 = time.perf_counter()
        data = get_schedule(session)
        timings["scrape_ms"] = round((time.perf_counter() - t1) * 1000.0, 1)

        # DB write
        if username:
            t2 = time.perf_counter()
            try:
                save_schedule(username, data)
            except Exception:
                pass
            timings["db_write_ms"] = round((time.perf_counter() - t2) * 1000.0, 1)

        total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
        timings["total_ms"] = total_ms
        return {"success": True, "count": len(data), "data": data, "cached": False, "timings_ms": timings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-cache")
def test_cache():
    t0 = time.perf_counter()
    from app.core.db import get_client
    client = get_client()
    db = client["uit-service"]
    doc = db["schedules"].find_one({"user_id": "24520378"})
    elapsed = (time.perf_counter() - t0) * 1000.0
    return {
        "found": doc is not None,
        "db_query_ms": round(elapsed, 1),
        "keys": list(doc.keys()) if doc else [],
    }


@router.get(
    "/exam",
    response_model=ExamScheduleResponse,
    summary="Get exam schedule",
    description="Retrieve the exam schedule for a specific semester and exam attempt",
    response_description="Exam schedule with dates, times, and locations",
)
def exam_schedule(
    lanthi: int = 1,
    hocky: int = 1,
    namhoc: int = 2025,
    authorization: str = Header(None),
    request: Request = None,
):
    t_request = time.perf_counter()
    timings = {}

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    session = get_valid_session(token)

    # If session not in cache or expired, try to re-login
    if not session:
        username, password = get_credentials_from_db(token)
        if username and password:
            logger.info("[EXAM] Re-login required for user=%s", username)
            new_session = login_and_get_session(username, password)
            if new_session:
                save_session(token, new_session, username, password)
                session = new_session
                logger.info("[EXAM] Re-login successful for user=%s", username)
            else:
                logger.warning("[EXAM] Re-login failed for user=%s", username)
                raise HTTPException(status_code=401, detail="Session expired - re-login failed")
        else:
            logger.warning("[EXAM] No credentials found for token=%s", token[:8])
            raise HTTPException(status_code=401, detail="Session not found")

    try:
        username = SESSION_STORE.get(token, {}).get("auth_data", {}).get("username")

        # DB Cache read
        if username:
            t0 = time.perf_counter()
            cached = load_cached_exam_schedule(username, lanthi, hocky, namhoc)
            timings["db_read_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

            if cached and cached.get("exam_schedule"):
                total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
                timings["total_ms"] = total_ms
                return {
                    "success": True,
                    "count": len(cached.get("exam_schedule")),
                    "data": cached.get("exam_schedule"),
                    "cached": True,
                    "timings_ms": timings,
                }

        # Scrape from UIT
        t1 = time.perf_counter()
        data = get_exam_schedule(session, lanthi=lanthi, hocky=hocky, namhoc=namhoc)
        timings["scrape_ms"] = round((time.perf_counter() - t1) * 1000.0, 1)

        # Transform
        t2 = time.perf_counter()
        transformed = transform_exam_schedule(data)
        timings["transform_ms"] = round((time.perf_counter() - t2) * 1000.0, 1)

        # DB write
        if username:
            t3 = time.perf_counter()
            try:
                save_exam_schedule(username, lanthi, hocky, namhoc, transformed)
            except Exception:
                pass
            timings["db_write_ms"] = round((time.perf_counter() - t3) * 1000.0, 1)

        total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
        timings["total_ms"] = total_ms
        return {"success": True, "count": len(transformed), "data": transformed, "cached": False, "timings_ms": timings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
