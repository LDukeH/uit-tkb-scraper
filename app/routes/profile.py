import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Request

logger = logging.getLogger("uit.routes.profile")

from app.core.cache_stampede import stampede
from app.services.school_service import (
    get_grades,
    get_valid_session,
    get_credentials_from_db,
    login_and_get_session,
    save_session,
    load_cached_profile,
    save_profile,
    SESSION_STORE,
)
from app.schemas.common import StudentProfile

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get(
    "/",
    response_model=StudentProfile,
    summary="Get student profile",
    description="Retrieve detailed student profile information including name, ID, date of birth, gender, class, faculty, training level, system, and major",
    response_description="Complete student profile information",
)
def get_profile(authorization: str = Header(None), request: Request = None):
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
            logger.info("[PROFILE] Re-login required for user=%s", username)
            new_session = login_and_get_session(username, password)
            if new_session:
                save_session(token, new_session, username, password)
                session = new_session
                logger.info("[PROFILE] Re-login successful for user=%s", username)
            else:
                logger.warning("[PROFILE] Re-login failed for user=%s", username)
                raise HTTPException(status_code=401, detail="Session expired - re-login failed")
        else:
            logger.warning("[PROFILE] No credentials found for token=%s", token[:8])
            raise HTTPException(status_code=401, detail="Session not found")

    try:
        username = SESSION_STORE.get(token, {}).get("auth_data", {}).get("username")

        # Try to get from cache first
        if username:
            t0 = time.perf_counter()
            cached_profile = load_cached_profile(username)
            timings["db_read_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

            if cached_profile:
                total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
                timings["total_ms"] = total_ms
                logger.info("[PROFILE] CACHE HIT for user=%s, total=%.1fms", username, total_ms)
                return cached_profile

        # No cache — scrape (with stampede protection)
        with stampede(f"profile:{username}", timeout=10.0):
            t1 = time.perf_counter()
            raw = get_grades(session)
            timings["scrape_ms"] = round((time.perf_counter() - t1) * 1000.0, 1)

            student_profile = raw.get("student_profile") or {}
            all_semesters = raw.get("semesters") or []
            summary = raw.get("summary") or {}

            # Save profile to cache for future use
            if username and student_profile:
                t2 = time.perf_counter()
                try:
                    save_profile(username, student_profile)
                except Exception:
                    pass
                timings["db_write_ms"] = round((time.perf_counter() - t2) * 1000.0, 1)

        total_ms = round((time.perf_counter() - t_request) * 1000.0, 1)
        timings["total_ms"] = total_ms
        logger.info("[PROFILE] SCRAPED for user=%s, total=%.1fms", username, total_ms)

        if not student_profile:
            raise HTTPException(status_code=404, detail="Student profile not found")

        return student_profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[PROFILE] Error for user=%s: %s", username, str(e))
        raise HTTPException(status_code=500, detail=str(e))