import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query, Request

logger = logging.getLogger("uit.routes.grades")

from app.core.cache_stampede import stampede
from app.services.school_service import (
    get_grades,
    get_valid_session,
    get_credentials_from_db,
    login_and_get_session,
    save_session,
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

    # If session not in cache or expired, try to re-login
    if not session:
        username, password = get_credentials_from_db(token)
        if username and password:
            logger.info("[GRADES] Re-login required for user=%s", username)
            new_session = login_and_get_session(username, password)
            if new_session:
                save_session(token, new_session, username, password)
                session = new_session
                logger.info("[GRADES] Re-login successful for user=%s", username)
            else:
                logger.warning("[GRADES] Re-login failed for user=%s", username)
                raise HTTPException(status_code=401, detail="Session expired - re-login failed")
        else:
            logger.warning("[GRADES] No credentials found for token=%s", token[:8])
            raise HTTPException(status_code=401, detail="Session not found")

    try:
        username = SESSION_STORE.get(token, {}).get("auth_data", {}).get("username")

        # DB Cache read — only use cache when filter params are provided
        # Without filter params, always fetch fresh data (grades may have changed)
        if username and (hocky is not None or namhoc is not None):
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

                # Normalize diem_trung_binh to string for Pydantic validation
                for sem in semesters:
                    dtb = sem.get("diem_trung_binh")
                    if dtb is not None and not isinstance(dtb, str):
                        sem["diem_trung_binh"] = str(dtb)

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

        # Normalize diem_trung_binh to string for Pydantic validation
        for sem in semesters:
            dtb = sem.get("diem_trung_binh")
            if dtb is not None and not isinstance(dtb, str):
                sem["diem_trung_binh"] = str(dtb)

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