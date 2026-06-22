from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional

from app.services.school_service import (
    get_tuition_fee,
    get_valid_session,
    load_all_cached_tuition,
    save_tuition,
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
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    session = get_valid_session(token)

    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    try:
        username = SESSION_STORE.get(token, {}).get("auth_data", {}).get("username")

        # Thử cache trước
        if username:
            cached = load_all_cached_tuition(username)
            if cached and cached.get("semesters"):
                semesters = cached["semesters"]

                # Lọc theo học kỳ/năm học nếu có
                if hocky is not None and namhoc is not None:
                    semesters = [
                        s for s in semesters
                        if s["hocky"] == hocky and s["namhoc"] == namhoc
                    ]
                elif hocky is not None:
                    semesters = [s for s in semesters if s["hocky"] == hocky]
                elif namhoc is not None:
                    semesters = [s for s in semesters if s["namhoc"] == namhoc]

                raw = {
                    "student_info": cached.get("student_info", {}),
                    "bank_info": cached.get("bank_info", {}),
                    "semesters": semesters,
                }
                result = transform_tuition_response(raw, username=username)

                return {
                    "success": True,
                    "cached": True,
                    **result,
                }

        # Không có cache — scrape
        raw = get_tuition_fee(session)

        student_info = raw.get("student_info") or {}
        bank_info = raw.get("bank_info") or {}
        all_semesters = raw.get("semesters") or []

        # Lưu từng học kỳ vào cache
        if username and all_semesters:
            for sem in all_semesters:
                try:
                    save_tuition(
                        username,
                        sem["hocky"],
                        sem["namhoc"],
                        student_info,
                        bank_info,
                        {
                            "so_tc_dang_ky": sem.get("so_tc_dang_ky", ""),
                            "mon_dang_ky": sem.get("mon_dang_ky", ""),
                            "hoc_phi": sem.get("hoc_phi", ""),
                            "phi_khac": sem.get("phi_khac", ""),
                            "so_tien_phai_dong": sem.get("so_tien_phai_dong", ""),
                            "no_hoc_ky_truoc": sem.get("no_hoc_ky_truoc", ""),
                            "so_tien_da_dong": sem.get("so_tien_da_dong", ""),
                            "con_no": sem.get("con_no", ""),
                            "ngan_hang": sem.get("ngan_hang", ""),
                            "thoi_gian_dong": sem.get("thoi_gian_dong", ""),
                            "ghi_chu": sem.get("ghi_chu", ""),
                            "chi_tiet_mon": sem.get("chi_tiet_mon", []),
                        },
                    )
                except Exception:
                    pass

        # Lọc theo học kỳ/năm học nếu có
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

        raw_filtered = {
            "student_info": student_info,
            "bank_info": bank_info,
            "semesters": semesters,
        }
        result = transform_tuition_response(raw_filtered, username=username or "")

        return {
            "success": True,
            "cached": False,
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
def tuition_summary(authorization: str = Header(None)):
    """Lightweight endpoint for Home screen — returns only remaining balance and latest semester."""
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
            cached = load_all_cached_tuition(username)
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

                return {
                    "success": True,
                    "cached": True,
                    "remaining": summary.get("remaining", 0),
                    "latest_semester": latest_semester,
                    "status": status,
                }

        # No cache — scrape
        raw = get_tuition_fee(session)
        result = transform_tuition_response(raw, username=username or "")
        semesters = result.get("semesters", [])
        summary = result.get("summary", {})

        latest = semesters[0] if semesters else None
        latest_semester = ""
        status = "UNPAID"
        if latest:
            latest_semester = f"HK{latest['hocky']} {latest['namhoc']}"
            status = latest.get("status", "UNPAID")

        # Save to cache
        if username and raw.get("semesters"):
            student_info = raw.get("student_info") or {}
            bank_info = raw.get("bank_info") or {}
            for sem in raw["semesters"]:
                try:
                    save_tuition(
                        username,
                        sem["hocky"],
                        sem["namhoc"],
                        student_info,
                        bank_info,
                        {
                            "so_tc_dang_ky": sem.get("so_tc_dang_ky", ""),
                            "mon_dang_ky": sem.get("mon_dang_ky", ""),
                            "hoc_phi": sem.get("hoc_phi", ""),
                            "phi_khac": sem.get("phi_khac", ""),
                            "so_tien_phai_dong": sem.get("so_tien_phai_dong", ""),
                            "no_hoc_ky_truoc": sem.get("no_hoc_ky_truoc", ""),
                            "so_tien_da_dong": sem.get("so_tien_da_dong", ""),
                            "con_no": sem.get("con_no", ""),
                            "ngan_hang": sem.get("ngan_hang", ""),
                            "thoi_gian_dong": sem.get("thoi_gian_dong", ""),
                            "ghi_chu": sem.get("ghi_chu", ""),
                            "chi_tiet_mon": sem.get("chi_tiet_mon", []),
                        },
                    )
                except Exception:
                    pass

        return {
            "success": True,
            "cached": False,
            "remaining": summary.get("remaining", 0),
            "latest_semester": latest_semester,
            "status": status,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
