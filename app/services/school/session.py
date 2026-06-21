import time
import requests
from bs4 import BeautifulSoup

from app.services.school.constants import LOGIN_URL, SESSION_DURATION

SESSION_STORE = {}


def save_session(token, session, username, password):
    SESSION_STORE[token] = {
        "session": session,
        "auth_data": {"username": username, "password": password},
        "expires": time.time() + SESSION_DURATION
    }


def is_session_alive(session):
    try:
        res = session.get(LOGIN_URL, timeout=5, allow_redirects=False)
        return res.status_code == 200
    except:
        return False


def get_valid_session(token):
    data = SESSION_STORE.get(token)
    if not data:
        return None

    current_session = data["session"]

    session_expired = time.time() > data["expires"]
    session_dead = not is_session_alive(current_session)

    if session_expired or session_dead:
        username = data["auth_data"]["username"]
        password = data["auth_data"]["password"]

        new_session = login_and_get_session(username, password)
        if new_session:
            save_session(token, new_session, username, password)
            return new_session
        else:
            print("Re-login failed.")
            del SESSION_STORE[token]
            return None

    # chi refresh expires neu session con song
    data["expires"] = time.time() + SESSION_DURATION
    return current_session


def login_and_get_session(username, password):
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = session.get(LOGIN_URL, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        form = soup.find("form", {"id": "user-login"}) or soup.find("form", {"id": "user-login-form"})
        if not form:
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
            return session
        return None
    except:
        return None