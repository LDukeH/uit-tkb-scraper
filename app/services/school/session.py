import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from app.services.school.constants import LOGIN_URL, SESSION_DURATION
from app.core.db import get_session_collection

logger = logging.getLogger("uit.services.session")

_shared_session: requests.Session | None = None
SESSION_STORE = {}  # In-memory cache for performance


def get_shared_session() -> requests.Session:
    global _shared_session
    if _shared_session is None:
        _shared_session = requests.Session()
        _shared_session.headers.update({"User-Agent": "Mozilla/5.0"})
        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        _shared_session.mount("https://", adapter)
        _shared_session.mount("http://", adapter)
    return _shared_session


def save_session(token, session, username, password):
    """Save session to both MongoDB (persistent) and in-memory cache (fast)"""
    expires = time.time() + SESSION_DURATION
    
    # Save to in-memory cache
    SESSION_STORE[token] = {
        "session": session,
        "auth_data": {"username": username, "password": password},
        "expires": expires
    }
    
    # Save credentials and expiry to MongoDB (not the session object)
    try:
        doc = {
            "token": token,
            "username": username,
            "password": password,
            "expires": expires,
            "created_at": time.time()
        }
        get_session_collection().update_one(
            {"token": token},
            {"$set": doc},
            upsert=True
        )
        logger.info("[SESSION] Saved to MongoDB token=%s user=%s", token[:8], username)
    except Exception as e:
        logger.warning("[SESSION] Failed to save to MongoDB token=%s error=%s", token[:8], e)


def is_session_alive(session):
    """Check if session is still valid by hitting a lightweight endpoint"""
    t0 = time.perf_counter()
    try:
        res = session.get(LOGIN_URL, timeout=5, allow_redirects=False)
        elapsed = (time.perf_counter() - t0) * 1000.0
        # 200 = login page (not logged in)
        # 302 = redirect (already logged in)
        is_alive = res.status_code in (200, 302)
        logger.info("[SESSION] is_session_alive status=%d alive=%s in %.1fms", res.status_code, is_alive, elapsed)
        return is_alive
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000.0
        logger.warning("[SESSION] is_session_alive EXCEPTION %s in %.1fms", e, elapsed)
        return False


def get_session_from_mongodb(token):
    """Load session metadata from MongoDB (not the session object itself)"""
    try:
        doc = get_session_collection().find_one({"token": token})
        return doc
    except Exception as e:
        logger.warning("[SESSION] MongoDB query failed for token=%s error=%s", token[:8], e)
        return None


def get_valid_session(token):
    """Get valid session - returns None if not found or expired (no auto re-login)"""
    t0 = time.perf_counter()
    logger.info("[SESSION] get_valid_session called with token=%s, SESSION_STORE keys=%s", token[:8], list(SESSION_STORE.keys()))
    
    # Try in-memory cache first (fast path)
    data = SESSION_STORE.get(token)
    
    if not data:
        # Cache miss - check if we have credentials in MongoDB
        logger.info("[SESSION] Cache MISS for token=%s, checking MongoDB", token[:8])
        doc = get_session_from_mongodb(token)
        
        if not doc:
            logger.info("[SESSION] MISS token=%s (not found anywhere)", token[:8])
            return None
        
        # Found in MongoDB but not in cache - need fresh login
        logger.info("[SESSION] Found credentials in MongoDB for token=%s user=%s, but need re-login", 
                   token[:8], doc.get("username"))
        return None  # Caller must handle re-login
    else:
        logger.info("[SESSION] Cache HIT for token=%s", token[:8])

    # Check if session is expired
    current_session = data["session"]
    session_expired = time.time() > data["expires"]
    
    # Check if session is still alive (only if not expired by time)
    session_dead = False
    if not session_expired:
        session_dead = not is_session_alive(current_session)
    
    if session_expired or session_dead:
        username = data["auth_data"]["username"]
        logger.info("[SESSION] EXPIRED/DEAD token=%s user=%s expired=%s dead=%s", 
                   token[:8], username, session_expired, session_dead)
        
        # Remove from cache
        SESSION_STORE.pop(token, None)
        
        # Update MongoDB to mark as needing refresh
        try:
            get_session_collection().update_one(
                {"token": token},
                {"$set": {"expires": time.time()}}  # Mark as expired
            )
        except Exception:
            pass
        
        return None  # Caller must handle re-login

    # Session is valid - extend expiry
    data["expires"] = time.time() + SESSION_DURATION
    elapsed = (time.perf_counter() - t0) * 1000.0
    logger.info("[SESSION] VALID token=%s user=%s in %.1fms", token[:8], data["auth_data"]["username"], elapsed)
    return current_session


def login_and_get_session(username, password):
    """Perform UIT login and return session object"""
    t0 = time.perf_counter()
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = session.get(LOGIN_URL, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        form = soup.find("form", {"id": "user-login"}) or soup.find("form", {"id": "user-login-form"})
        if not form:
            logger.warning("[SESSION] login form not found for user=%s", username)
            return None

        payload = {inp.get("name"): inp.get("value", "") for inp in form.find_all("input") if inp.get("name")}
        payload.update({"name": username, "pass": password, "op": "Đăng nhập"})

        img = form.select_one(".english-captcha-image img")
        if img:
            payload["english_captcha_answer"] = img["alt"].replace("captcha:", "").strip()

        action = form.get("action", "/user/login")
        login_url = "https://student.uit.edu.vn" + action

        login_res = session.post(login_url, data=payload, headers=headers)

        if "not-logged-in" not in login_res.text and login_res.status_code == 200:
            elapsed = (time.perf_counter() - t0) * 1000.0
            logger.info("[SESSION] login_and_get_session OK user=%s in %.1fms", username, elapsed)
            return session
        elapsed = (time.perf_counter() - t0) * 1000.0
        logger.warning("[SESSION] login_and_get_session FAILED user=%s status=%d in %.1fms", username, login_res.status_code, elapsed)
        return None
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000.0
        logger.warning("[SESSION] login_and_get_session EXCEPTION user=%s %s in %.1fms", username, e, elapsed)
        return None


def get_credentials_from_db(token):
    """Get stored credentials from MongoDB for re-login"""
    try:
        doc = get_session_collection().find_one({"token": token})
        if doc:
            return doc.get("username"), doc.get("password")
        return None, None
    except Exception as e:
        logger.warning("[SESSION] Failed to get credentials for token=%s error=%s", token[:8], e)
        return None, None