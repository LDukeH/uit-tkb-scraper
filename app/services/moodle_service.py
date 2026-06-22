import re
from datetime import datetime, timezone
from typing import Optional
from icalendar import Calendar

import requests
from bs4 import BeautifulSoup

MOODLE_BASE = "https://courses.uit.edu.vn"
LOGIN_URL = f"{MOODLE_BASE}/login/index.php"
LOGIN_TOKEN_URL = f"{MOODLE_BASE}/login/token.php"
REST_API_URL = f"{MOODLE_BASE}/webservice/rest/server.php"
EXPORT_PAGE_URL = f"{MOODLE_BASE}/calendar/export.php"
ICAL_EXPORT_URL = f"{MOODLE_BASE}/calendar/export_execute.php"


class MoodleClient:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.userid: Optional[int] = None
        self.export_token: Optional[str] = None
        self.sesskey: Optional[str] = None
        self.wstoken: Optional[str] = None

    def login(self) -> bool:
        resp = self.session.get(LOGIN_URL)
        match = re.search(r'name="logintoken" value="([^"]+)"', resp.text)
        if not match:
            return False

        resp = self.session.post(LOGIN_URL, data={
            "logintoken": match.group(1),
            "username": self.username,
            "password": self.password,
            "anchor": "",
        })

        if "Bạn chưa đăng nhập" in resp.text:
            return False

        self._extract_session_data(resp.text)
        return True

    def _extract_session_data(self, html: str):
        uid_match = re.search(r'userid["\']?\s*[:=]\s*["\']?(\d+)', html)
        if uid_match:
            self.userid = int(uid_match.group(1))

        token_match = re.search(r'authtoken=([a-f0-9]+)', html)
        if token_match:
            self.export_token = token_match.group(1)

        sesskey_match = re.search(r'"sesskey":"([^"]+)"', html)
        if sesskey_match:
            self.sesskey = sesskey_match.group(1)

    def _fetch_export_page(self) -> bool:
        resp = self.session.get(EXPORT_PAGE_URL)
        if resp.status_code != 200:
            return False
        self._extract_session_data(resp.text)
        return bool(self.userid and self.export_token)

    def _login_via_token(self) -> bool:
        resp = self.session.post(LOGIN_TOKEN_URL, data={
            "username": self.username,
            "password": self.password,
            "service": "moodle_mobile_app",
        })
        data = resp.json()
        if "token" not in data:
            return False
        self.wstoken = data["token"]
        return True

    def fetch_ical(self, preset: str = "monthnow",
                   timefrom: Optional[int] = None,
                   timeto: Optional[int] = None) -> Optional[str]:

        if not self.userid or not self.export_token:
            if not self._fetch_export_page():
                if not self._login_via_token():
                    return None
                # thử lấy export token qua REST
                params = {
                    "wstoken": self.wstoken,
                    "wsfunction": "core_calendar_get_calendar_export_token",
                    "moodlewsrestformat": "json",
                }
                resp = self.session.get(REST_API_URL, params=params)
                data = resp.json()
                if isinstance(data, dict):
                    self.export_token = data.get("exporttoken") or data.get("token")
                if not self.export_token:
                    return None

        params = {
            "userid": self.userid,
            "authtoken": self.export_token,
            "preset_what": "all",
            "preset_time": preset,
        }

        if timefrom is not None:
            params["preset_time"] = "custom"
            params["timefrom"] = str(timefrom)
            params["timeto"] = str(timeto or (timefrom + 86400 * 62))

        resp = self.session.get(ICAL_EXPORT_URL, params=params)
        if resp.status_code == 200 and "BEGIN:VCALENDAR" in resp.text:
            return resp.text
        return None

    @staticmethod
    def parse_ical(text: str) -> list[dict]:
        cal = Calendar.from_ical(text)
        events = []
        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            uid = str(component.get("UID", ""))
            summary = str(component.get("SUMMARY", ""))
            description = str(component.get("DESCRIPTION", ""))
            dtstart = component.get("DTSTART")
            dtend = component.get("DTEND")
            cats = component.get("CATEGORIES")
            categories = ", ".join(str(c) for c in cats.cats) if cats else ""
            url = str(component.get("URL", ""))

            desc_text = ""
            if description:
                soup = BeautifulSoup(description, "html.parser")
                desc_text = soup.get_text(separator="\n", strip=True)

            start_val = dtstart.dt if dtstart else None
            end_val = dtend.dt if dtend else None

            if isinstance(start_val, datetime):
                start_val = start_val.replace(tzinfo=None)
            if isinstance(end_val, datetime):
                end_val = end_val.replace(tzinfo=None)

            event_id = uid.split("@")[0] if "@" in uid else uid

            events.append({
                "id": event_id,
                "title": summary,
                "description": desc_text,
                "course_code": categories,
                "start": start_val.isoformat() if start_val else None,
                "end": end_val.isoformat() if end_val else None,
                "url": url,
            })

        return events

    @staticmethod
    def enrich_deadline(event: dict) -> dict:
        """Thêm status và days_remaining vào event."""
        enriched = dict(event)
        deadline_str = event.get("deadline") or event.get("start")
        if not deadline_str:
            enriched["status"] = "UNKNOWN"
            enriched["days_remaining"] = 0
            return enriched

        try:
            dt = datetime.fromisoformat(deadline_str)
            now = datetime.now()
            delta = (dt - now).total_seconds() / 86400.0
            enriched["days_remaining"] = int(delta)
            enriched["status"] = "OVERDUE" if delta < 0 else "UPCOMING"
        except (ValueError, TypeError):
            enriched["status"] = "UNKNOWN"
            enriched["days_remaining"] = 0

        return enriched

    def get_deadlines(self, year: Optional[int] = None,
                      month: Optional[int] = None) -> list[dict]:
        """Lấy danh sách deadline trong tháng/năm cụ thể."""
        now = datetime.now()
        if year is None:
            year = now.year
        if month is None:
            month = now.month

        ical_text = self.fetch_ical(preset="monthnow")
        if not ical_text:
            return []

        all_events = self.parse_ical(ical_text)

        filtered = []
        for e in all_events:
            start = e["start"]
            if start:
                try:
                    ev_start = datetime.fromisoformat(start)
                    if ev_start.year == year and ev_start.month == month:
                        filtered.append(e)
                except (ValueError, TypeError):
                    filtered.append(e)
            else:
                filtered.append(e)

        return [self.enrich_deadline(ev) for ev in filtered]
