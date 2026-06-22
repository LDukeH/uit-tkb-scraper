import time
from fastapi import APIRouter, HTTPException, Header, Query, Request
from typing import Optional

from app.core.cache_stampede import stampede
from app.services.school_service import (
    get_tuition_fee,
    get_valid_session,
    load_all_cached_tuition,
    save_tuition,
    save_tuition_bulk,
    SESSION_STORE,
)
from app.services.school.tuition import transform_tuition_response
from app.schemas.tuition import TuitionResponse, TuitionSummaryResponse

router = APIRouter(prefix="/tuition", tags=["Tuition"])


@router.get(
    "/",
    response_model=TuitionResponse,
    summary="Get tuition information",
    description="Retrieve detailed tuition fee information for all semesters, optionally filtered by semester and year",
    response_description="Complete tuition data including student info, bank info, and semester breakdown",
)
def tuition(
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

        # Try cache first
        if username:
            t0 = time.perf_counter()
            cached = load_all_cached_tuition(username)
            timings["db_read_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

            if cached and cached.get("semesters"):
                semesters = cached["semesters"]

                if hocky is not None and namhoc is not None:
                    semesters = [s for s in semesters if s["hocky"] == hocky and s["namhoc"] == namhoc]
                elif hocky is not None:
                    semesters = [s for s in semesters if s["hocky"] == hocky]
                elif namhoc is not None:
                    semesters = [s for s in semesters if s["namhoc"] == namhoc]

                raw = {
                    "student_info": cached.get("student_info", {}),
                    "bank_info": cached.get("bank_info", {}),
                    "semesters": semesters,
                }
                t1 = time.perf_counter()
                result = transform_tuition_response(raw, username=username)
                timings["transform_ms"] = round((time.perf_counter() - t1) * 1000.0, 1)

                total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
                timings["total_ms"] = total_ms

                return {
                    "success": True,
                    "cached": True,
                    "timings_ms": timings,
                    **result,
                }

        # No cache — scrape (with stampede protection)
        with stampede(f"tuition:{username}", timeout=10.0):
            t1 = time.perf_counter()
            raw = get_tuition_fee(session)
            timings["scrape_ms"] = round((time.perf_counter() - t1) * 1000.0, 1)

            student_info = raw.get("student_info") or {}
            bank_info = raw.get("bank_info") or {}
            all_semesters = raw.get("semesters") or []

            # Bulk save to cache
            if username and all_semesters:
                t2 = time.perf_counter()
                try:
                    save_tuition_bulk(username, student_info, bank_info, all_semesters)
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

        t3 = time.perf_counter()
        raw_filtered = {"student_info": student_info, "bank_info": bank_info, "semesters": semesters}
        result = transform_tuition_response(raw_filtered, username=username or "")
        timings["transform_ms"] = round((time.perf_counter() - t3) * 1000.0, 1)

        total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
        timings["total_ms"] = total_ms

        return {
            "success": True,
            "cached": False,
            "timings_ms": timings,
            **result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/summary",
    response_model=TuitionSummaryResponse,
    summary="Get tuition summary",
    description="Lightweight endpoint for home screen - returns only remaining balance and latest semester",
    response_description="Tuition summary with remaining balance and latest semester status",
)
def tuition_summary(
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

        # Try cache first
        if username:
            t0 = time.perf_counter()
            cached = load_all_cached_tuition(username)
            timings["db_read_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

            if cached and cached.get("semesters"):
                raw = {
                    "student_info": cached.get("student_info", {}),
                    "bank_info": cached.get("bank_info", {}),
                    "semesters": cached["semesters"],
                }
                result = transform_tuition_response(raw, username=username)
                semesters = result.get("semesters", [])
                summary = result.get("summary", {})

                latest = semesters[0] if semesters else None
                latest_semester = ""
                status = "UNPAID"
                if latest:
                    latest_semester = f"HK{latest['hocky']} {latest['namhoc']}"
                    status = latest.get("status", "UNPAID")

                total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
                timings["total_ms"] = total_ms

                return {
                    "success": True,
                    "cached": True,
                    "timings_ms": timings,
                    "remaining": summary.get("remaining", 0),
                    "latest_semester": latest_semester,
                    "status": status,
                }

        # No cache — scrape (with stampede protection)
        with stampede(f"tuition_summary:{username}", timeout=10.0):
            t1 = time.perf_counter()
            raw = get_tuition_fee(session)
            timings["scrape_ms"] = round((time.perf_counter() - t1) * 1000.0, 1)

            result = transform_tuition_response(raw, username=username or "")
            semesters = result.get("semesters", [])
            summary = result.get("summary", {})

            latest = semesters[0] if semesters else None
            latest_semester = ""
            status = "UNPAID"
            if latest:
                latest_semester = f"HK{latest['hocky']} {latest['namhoc']}"
                status = latest.get("status", "UNPAID")

            # Bulk save to cache
            if username and raw.get("semesters"):
                t2 = time.perf_counter()
                student_info = raw.get("student_info") or {}
                bank_info = raw.get("bank_info") or {}
                try:
                    save_tuition_bulk(username, student_info, bank_info, raw["semesters"])
                except Exception:
                    pass
                timings["db_write_ms"] = round((time.perf_counter() - t2) * 1000.0, 1)

        total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
        timings["total_ms"] = total_ms

        return {
            "success": True,
            "cached": False,
            "timings_ms": timings,
            "remaining": summary.get("remaining", 0),
            "latest_semester": latest_semester,
            "status": status,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
