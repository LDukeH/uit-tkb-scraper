from fastapi import APIRouter, HTTPException, Header

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
        # tìm và lấy cache theo username
        username = SESSION_STORE.get(token, {}).get("auth_data", {}).get("username")

        # tính toán thời gian đọc db
        if username:
            cached = load_cached_schedule(username)
            if cached and cached.get("schedule"):
                return {"success": True, "count": len(cached.get("schedule")), "data": cached.get("schedule"), "cached": True}

        # không có cache -> scrape và lưu
        data = get_schedule(session)

        if username:
            try:
                save_schedule(username, data)
            except Exception:
                pass

        return {"success": True, "count": len(data), "data": data, "cached": False}
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

        if username:
            cached = load_cached_exam_schedule(username, lanthi, hocky, namhoc)
            if cached and cached.get("exam_schedule"):
                return {
                    "success": True,
                    "count": len(cached.get("exam_schedule")),
                    "data": cached.get("exam_schedule"),
                    "cached": True,
                }

        data = get_exam_schedule(session, lanthi=lanthi, hocky=hocky, namhoc=namhoc)
        transformed = transform_exam_schedule(data)

        if username:
            try:
                save_exam_schedule(username, lanthi, hocky, namhoc, transformed)
            except Exception:
                pass

        return {"success": True, "count": len(transformed), "data": transformed, "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))