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

router = APIRouter(prefix="/tuition", tags=["Tuition"])


@router.get("/")
def tuition(
    hocky: Optional[int] = Query(default=None),
    namhoc: Optional[int] = Query(default=None),
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


@router.get("/summary")
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
