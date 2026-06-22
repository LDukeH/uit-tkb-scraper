from fastapi import APIRouter, HTTPException, Header, Query, Request
from typing import Optional
import time

from app.core.cache_stampede import stampede
from app.services.school_service import (
    get_grades,
    get_valid_session,
    load_all_cached_grades,
    save_grade,
    save_grades_bulk,
    SESSION_STORE,
)
from app.schemas.grade import GradeResponse

router = APIRouter(prefix="/grades", tags=["Grades"])


@router.get(
    "/",
    response_model=GradeResponse,
    summary="Get student grades",
    description="Retrieve academic grades for all semesters, optionally filtered by semester and year",
    response_description="Complete grades data including student profile, semester grades, and academic summary",
)
def grades(
    hocky: Optional[int] = Query(
        default=None,
        ge=1,
        le=3,
        description="Filter by semester number (1, 2, or 3)",
        examples=[1, 2],
    ),
    namhoc: Optional[int] = Query(
        default=None,
        ge=2000,
        le=2100,
        description="Filter by academic year",
        examples=[2024, 2025],
    ),
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
            cached = load_all_cached_grades(username)
            timings["db_read_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

            if cached and cached.get("semesters"):
                semesters = cached["semesters"]

                if hocky is not None and namhoc is not None:
                    semesters = [s for s in semesters if s["hocky"] == hocky and s["namhoc"] == namhoc]
                elif hocky is not None:
                    semesters = [s for s in semesters if s["hocky"] == hocky]
                elif namhoc is not None:
                    semesters = [s for s in semesters if s["namhoc"] == namhoc]

                total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
                timings["total_ms"] = total_ms

                return {
                    "success": True,
                    "cached": True,
                    "count": len(semesters),
                    "data": {
                        "student_profile": cached["student_profile"],
                        "semesters": semesters,
                        "summary": cached.get("summary", {}),
                    },
                    "timings_ms": timings,
                }

        # No cache — scrape (with stampede protection)
        with stampede(f"grades:{username}", timeout=10.0):
            t1 = time.perf_counter()
            raw = get_grades(session)
            timings["scrape_ms"] = round((time.perf_counter() - t1) * 1000.0, 1)

            student_profile = raw.get("student_profile") or {}
            all_semesters = raw.get("semesters") or []
            summary = raw.get("summary") or {}

            # Bulk save to cache
            if username and all_semesters:
                t2 = time.perf_counter()
                try:
                    save_grades_bulk(username, student_profile, summary, all_semesters)
                except Exception:
                    pass
                timings["db_write_ms"] = round((time.perf_counter() - t2) * 1000.0, 1)

        # Filter
        semesters = all_semesters
        if hocky is not None and namhoc is not None:
            semesters = [s for s in semesters if s["hocky"] == hocky and s["namhoc"] == namhoc]
        elif hocky is not None:
            semesters = [s for s in semesters if s["hocky"] == hocky]
        elif namhoc is not None:
            semesters = [s for s in semesters if s["namhoc"] == namhoc]

        total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
        timings["total_ms"] = total_ms

        return {
            "success": True,
            "cached": False,
            "count": len(semesters),
            "data": {
                "student_profile": student_profile,
                "semesters": semesters,
                "summary": summary,
            },
            "timings_ms": timings,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
