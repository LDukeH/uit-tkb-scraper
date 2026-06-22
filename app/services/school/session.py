import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from app.services.school.constants import LOGIN_URL, SESSION_DURATION

logger = logging.getLogger("uit.services.session")

_shared_session: requests.Session | None = None


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


SESSION_STORE = {}


def save_session(token, session, username, password):
    SESSION_STORE[token] = {
        "session": session,
        "auth_data": {"username": username, "password": password},
        "expires": time.time() + SESSION_DURATION
    }


def is_session_alive(session):
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


def get_valid_session(token):
    t0 = time.perf_counter()
    data = SESSION_STORE.get(token)
    if not data:
        logger.info("[SESSION] MISS token=%s (not in store)", token[:8])
        return None

    current_session = data["session"]

    session_expired = time.time() > data["expires"]
    session_dead = not is_session_alive(current_session)

    if session_expired or session_dead:
        username = data["auth_data"]["username"]
        password = data["auth_data"]["password"]
        logger.info("[SESSION] EXPIRED/DEAD token=%s user=%s expired=%s dead=%s", token[:8], username, session_expired, session_dead)

        new_session = login_and_get_session(username, password)
        elapsed = (time.perf_counter() - t0) * 1000.0
        if new_session:
            logger.info("[SESSION] RE-LOGIN OK user=%s in %.1fms", username, elapsed)
            save_session(token, new_session, username, password)
            return new_session
        else:
            logger.warning("[SESSION] RE-LOGIN FAILED user=%s in %.1fms", username, elapsed)
            del SESSION_STORE[token]
            return None

    data["expires"] = time.time() + SESSION_DURATION
    elapsed = (time.perf_counter() - t0) * 1000.0
    logger.info("[SESSION] VALID token=%s user=%s in %.1fms", token[:8], data["auth_data"]["username"], elapsed)
    return current_session


def login_and_get_session(username, password):
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
