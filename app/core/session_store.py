import secrets
import time

sessions = {}

SESSION_DURATION = 1800  

def create_session(cookies):
    token = secrets.token_hex(32)

    sessions[token] = {
        "cookies": cookies,
        "expires": time.time() + SESSION_DURATION
    }

    return token

def get_session(token):
    data = sessions.get(token)

    if not data:
        return None

    if time.time() > data["expires"]:
        del sessions[token]
        return None

    return data["cookies"]