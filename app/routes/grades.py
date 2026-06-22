from fastapi import APIRouter, HTTPException, Header
import time

from app.services.school_service import (
    get_grades,
    get_valid_session,
    load_cached_grades,
    save_grades,
    SESSION_STORE,
)

router = APIRouter(prefix="/grades", tags=["Grades"])


@router.get("/")
def grades(authorization: str = Header(None)):
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
            cached = load_cached_grades(username)
            db_time_ms = (time.perf_counter() - t0) * 1000.0
            if cached and cached.get("semesters"):
                sem_count = len(cached.get("semesters", []))
                return {
                    "success": True,
                    "count": sem_count,
                    "data": {
                        "student_info": cached.get("student_info", {}),
                        "semesters": cached.get("semesters", []),
                        "overview": cached.get("overview", {}),
                    },
                    "cached": True,
                    "timings_ms": {"db_read": round(db_time_ms, 1)},
                }

        t1 = time.perf_counter()
        data = get_grades(session)
        scrape_time_ms = (time.perf_counter() - t1) * 1000.0

        save_time_ms = None
        if username:
            t2 = time.perf_counter()
            try:
                save_grades(username, data)
            except Exception:
                pass
            save_time_ms = (time.perf_counter() - t2) * 1000.0

        timings = {"scrape": round(scrape_time_ms, 1)}
        if db_time_ms is not None:
            timings["db_read"] = round(db_time_ms, 1)
        if save_time_ms is not None:
            timings["db_write"] = round(save_time_ms, 1)

        sem_count = len(data.get("semesters", []))
        return {
            "success": True,
            "count": sem_count,
            "data": {
                "student_info": data.get("student_info", {}),
                "semesters": data.get("semesters", []),
                "overview": data.get("overview", {}),
            },
            "cached": False,
            "timings_ms": timings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
