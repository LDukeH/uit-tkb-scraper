import time
from fastapi import APIRouter, HTTPException, Header, Request

from app.services.school_service import (
    get_schedule,
    get_valid_session,
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

    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    try:
        username = SESSION_STORE.get(token, {}).get("auth_data", {}).get("username")

        # DB Cache read
        if username:
            t0 = time.perf_counter()
            cached = load_cached_schedule(username)
            timings["db_read_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

            if cached and cached.get("schedule"):
                total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
                timings["total_ms"] = total_ms
                return {"success": True, "count": len(cached.get("schedule")), "data": cached.get("schedule"), "cached": True, "timings_ms": timings}

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

    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

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
