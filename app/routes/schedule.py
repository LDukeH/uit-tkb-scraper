from fastapi import APIRouter, HTTPException, Header
import time

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

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.get("/")
def schedule(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    session = get_valid_session(token)

    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    try:
        # tim va lay cache theo username
        username = SESSION_STORE.get(token, {}).get("auth_data", {}).get("username")

        # tinh toan thoi gian doc db
        db_time_ms = None
        if username:
            t0 = time.perf_counter()
            cached = load_cached_schedule(username)
            db_time_ms = (time.perf_counter() - t0) * 1000.0
            if cached and cached.get("schedule"):
                return {"success": True, "count": len(cached.get("schedule")), "data": cached.get("schedule"), "cached": True, "timings_ms": {"db_read": round(db_time_ms, 1)}}

        # khong co cache scrape va luu tinh toan thoi gian
        t1 = time.perf_counter()
        data = get_schedule(session)
        scrape_time_ms = (time.perf_counter() - t1) * 1000.0

        save_time_ms = None
        if username:
            t2 = time.perf_counter()
            try:
                save_schedule(username, data)
            except Exception:
                pass
            save_time_ms = (time.perf_counter() - t2) * 1000.0

        timings = {"scrape": round(scrape_time_ms, 1)}
        if db_time_ms is not None:
            timings["db_read"] = round(db_time_ms, 1)
        if save_time_ms is not None:
            timings["db_write"] = round(save_time_ms, 1)

        return {"success": True, "count": len(data), "data": data, "cached": False, "timings_ms": timings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/exam")
def exam_schedule(lanthi: int = 1, hocky: int = 1, namhoc: int = 2025, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    session = get_valid_session(token)

    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    try:
        username = SESSION_STORE.get(token, {}).get("auth_data", {}).get("username")

        db_time_ms = None
        if username:
            t0 = time.perf_counter()
            cached = load_cached_exam_schedule(username, lanthi, hocky, namhoc)
            db_time_ms = (time.perf_counter() - t0) * 1000.0
            if cached and cached.get("exam_schedule"):
                return {
                    "success": True,
                    "count": len(cached.get("exam_schedule")),
                    "data": cached.get("exam_schedule"),
                    "cached": True,
                    "timings_ms": {"db_read": round(db_time_ms, 1)}
                }

        t1 = time.perf_counter()
        data = get_exam_schedule(session, lanthi=lanthi, hocky=hocky, namhoc=namhoc)
        scrape_time_ms = (time.perf_counter() - t1) * 1000.0

        save_time_ms = None
        if username:
            t2 = time.perf_counter()
            try:
                save_exam_schedule(username, lanthi, hocky, namhoc, data)
            except Exception:
                pass
            save_time_ms = (time.perf_counter() - t2) * 1000.0

        timings = {"scrape": round(scrape_time_ms, 1)}
        if db_time_ms is not None:
            timings["db_read"] = round(db_time_ms, 1)
        if save_time_ms is not None:
            timings["db_write"] = round(save_time_ms, 1)

        return {"success": True, "count": len(data), "data": data, "cached": False, "timings_ms": timings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))