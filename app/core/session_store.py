import secrets
import time

SESSION_STORE = {} 

SESSION_DURATION = 1800  # 30 phút

def save_session(token, session, username, password):
    SESSION_STORE[token] = {
        "session": session,
        "auth_data": {"username": username, "password": password},
        "expires": time.time() + SESSION_DURATION
    }

def get_session_data(token):
    data = SESSION_STORE.get(token)
    if not data:
        return None
    return data

def create_session(cookies):
    token = secrets.token_hex(32)

    SESSION_STORE[token] = {
        "cookies": cookies,
        "expires": time.time() + SESSION_DURATION
    }

    return token

def get_session(token):
    data = SESSION_STORE.get(token)

    if not data:
        return None

    if time.time() > data["expires"]:
        del SESSION_STORE[token]
        return None

    return data["cookies"]