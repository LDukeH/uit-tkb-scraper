from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional
import time

from app.services.school_service import (
    get_tuition_fee,
    get_valid_session,
    load_all_cached_tuition,
    save_tuition,
    SESSION_STORE,
)

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
        db_time_ms = None
        if username:
            t0 = time.perf_counter()
            cached = load_all_cached_tuition(username)
            db_time_ms = (time.perf_counter() - t0) * 1000.0

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

                return {
                    "success": True,
                    "cached": True,
                    "count": len(semesters),
                    "data": {
                        "student_info": cached["student_info"],
                        "bank_info": cached["bank_info"],
                        "semesters": semesters,
                    },
                    "timings_ms": {"db_read": round(db_time_ms, 1)},
                }

        # Không có cache — scrape
        t1 = time.perf_counter()
        raw = get_tuition_fee(session)
        scrape_time_ms = (time.perf_counter() - t1) * 1000.0

        student_info = raw.get("student_info") or {}
        bank_info = raw.get("bank_info") or {}
        all_semesters = raw.get("semesters") or []

        # Lưu từng học kỳ vào cache
        save_time_ms = None
        if username and all_semesters:
            t2 = time.perf_counter()
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
            save_time_ms = (time.perf_counter() - t2) * 1000.0

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
                "student_info": student_info,
                "bank_info": bank_info,
                "semesters": semesters,
            },
            "timings_ms": timings,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))