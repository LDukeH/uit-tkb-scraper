from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional
import time

from app.services.school_service import (
    get_grades,
    get_valid_session,
    load_all_cached_grades,
    save_grade,
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
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    session = get_valid_session(token)

    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    try:
        username = SESSION_STORE.get(token, {}).get("auth_data", {}).get("username")

        # tìm cache
        db_time_ms = None
        if username:
            t0 = time.perf_counter()
            cached = load_all_cached_grades(username)
            db_time_ms = (time.perf_counter() - t0) * 1000.0

            if cached and cached.get("semesters"):
                semesters = cached["semesters"]

                # lọc theo năm và học kỳ nếu có
                if hocky is not None and namhoc is not None:
                    semesters = [
                        s for s in semesters
                        if s["hocky"] == hocky and s["namhoc"] == namhoc
                    ]
                elif hocky is not None:
                    semesters = [s for s in semesters if s["hocky"] == hocky]
                elif namhoc is not None:
                    semesters = [s for s in semesters if s["namhoc"] == namhoc]

                return {
                    "success": True,
                    "cached": True,
                    "count": len(semesters),
                    "data": {
                        "student_profile": cached["student_profile"],
                        "semesters": semesters,
                        "summary": cached.get("summary", {}),
                    },
                    "timings_ms": {"db_read": round(db_time_ms, 1)},
                }

        # không có cache -> scrape
        t1 = time.perf_counter()
        raw = get_grades(session)
        scrape_time_ms = (time.perf_counter() - t1) * 1000.0

        student_profile = raw.get("student_profile") or {}
        all_semesters = raw.get("semesters") or []
        summary = raw.get("summary") or {}

        # lưu cache vào db
        save_time_ms = None
        if username and all_semesters:
            t2 = time.perf_counter()
            for sem in all_semesters:
                try:
                    save_grade(
                        username,
                        sem["hocky"],
                        sem["namhoc"],
                        student_profile,
                        {
                            "subjects": sem.get("subjects", []),
                            "so_tin_chi": sem.get("so_tin_chi"),
                            "diem_trung_binh": sem.get("diem_trung_binh", ""),
                        },
                        summary,
                    )
                except Exception:
                    pass
            save_time_ms = (time.perf_counter() - t2) * 1000.0

        # lọc theo năm và học kỳ nếu có
        semesters = all_semesters
        if hocky is not None and namhoc is not None:
            semesters = [
                s for s in semesters
                if s["hocky"] == hocky and s["namhoc"] == namhoc
            ]
        elif hocky is not None:
            semesters = [s for s in semesters if s["hocky"] == hocky]
        elif namhoc is not None:
            semesters = [s for s in semesters if s["namhoc"] == namhoc]

        timings = {"scrape": round(scrape_time_ms, 1)}
        if db_time_ms is not None:
            timings["db_read"] = round(db_time_ms, 1)
        if save_time_ms is not None:
            timings["db_write"] = round(save_time_ms, 1)

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