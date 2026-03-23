import requests
from bs4 import BeautifulSoup
import re
import time
from fastapi import HTTPException

LOGIN_URL = "https://student.uit.edu.vn/user/login"
SCHEDULE_URL = "https://student.uit.edu.vn/sinhvien/tkb"
SESSION_DURATION = 180  

SESSION_STORE = {}

DAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"]
PERIOD_TIME = {
    1: "07:30-08:15", 2: "08:15-09:00", 3: "09:00-09:45", 4: "10:00-10:45", 5: "10:45-11:30",
    6: "13:00-13:45", 7: "13:45-14:30", 8: "14:30-15:15", 9: "15:30-16:15", 10: "16:15-17:00",
}


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
    
    if time.time() > data["expires"] or not is_session_alive(current_session):
        
        username = data["auth_data"]["username"]
        password = data["auth_data"]["password"]
        
        new_session = login_and_get_session(username, password)
        
        if new_session:
            save_session(token, new_session, username, password)
            return new_session
        else:
            print("Silent re-login failed.")
            del SESSION_STORE[token]
            return None
            
    return current_session

def login_and_get_session(username, password):
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = session.get(LOGIN_URL, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        form = soup.find("form", {"id": "user-login"}) or soup.find("form", {"id": "user-login-form"})
        if not form: return None

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
def get_schedule(session):
    res = session.get(SCHEDULE_URL)
    if not res or res.status_code != 200: return []

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.select_one(".tkb-table")
    if not table: return []

    rows = table.select("tbody tr")
    raw_schedule = []
    rowspan_tracker = {}

    for row in rows:
        cols = row.find_all("td")
        if not cols: continue
        
        raw_period = cols[0].get_text(strip=True)
        match = re.search(r"Tiết\s*(\d+)", raw_period)
        if not match: continue
        period_number = int(match.group(1))

        col_idx = -1
        for cell in cols[1:]:
            col_idx += 1
            while rowspan_tracker.get(col_idx, 0) > 0:
                rowspan_tracker[col_idx] -= 1
                col_idx += 1

            card = cell.select_one(".tkb-card")
            rowspan = int(cell.get("rowspan", 1))

            if card:
                titles = card.select(".title")
                subs = card.select(".sub")
                
                full_date_range = subs[2].text.strip() if len(subs) > 2 else ""

                for i in range(rowspan):
                    raw_schedule.append({
                        "day": DAYS[col_idx] if col_idx < len(DAYS) else "",
                        "period": period_number + i,
                        "code": titles[0].text.strip() if titles else "",
                        "name": titles[1].text.strip() if len(titles) > 1 else "",
                        "room": subs[0].text.strip() if subs else "",
                        "teacher": subs[1].text.strip() if len(subs) > 1 else "",
                        "date": full_date_range,
                    })

            if rowspan > 1:
                rowspan_tracker[col_idx] = rowspan - 1

    return merge_schedule(raw_schedule)

def merge_schedule(schedule):
    merged = {}
    for item in schedule:
        key = (item["day"], item["code"], item["name"], item["room"], item["teacher"], item["date"])
        if key not in merged:
            merged[key] = {**item, "periods": []}
        merged[key]["periods"].append(item["period"])

    result = []
    for data in merged.values():
        periods = sorted(set(data["periods"]))
        if not periods: continue

        ranges = []
        start = end = periods[0]
        for p in periods[1:]:
            if p == end + 1: end = p
            else:
                ranges.append((start, end))
                start = end = p
        ranges.append((start, end))

        p_str = ", ".join(f"Tiết {s}-{e}" if s != e else f"Tiết {s}" for s, e in ranges)
        
        start_h = PERIOD_TIME.get(min(periods), "").split("-")[0]
        end_h = PERIOD_TIME.get(max(periods), "").split("-")[1]

        raw_date = data["date"]
        start_date = ""
        end_date = ""
        
        if "->" in raw_date:
            parts = raw_date.split("->")
            start_date = parts[0].strip()
            end_date = parts[1].strip()
        else:
            start_date = raw_date 

        result.append({
            "day": data["day"],
            "period": p_str,
            "time": f"{start_h}-{end_h}",
            "start_time": start_h,
            "end_time": end_h,
            "start_date": start_date, 
            "end_date": end_date,     
            "code": data["code"],
            "name": data["name"],
            "room": data["room"],
            "teacher": data["teacher"],
            "date": data["date"], 
        })
    return result


# Add this to your school_service.py
def get_announcements():
    ANNOUNCEMENT_URL = "https://student.uit.edu.vn/thong-bao-chung"
    try:
        res = requests.get(ANNOUNCEMENT_URL, timeout=10)
        if res.status_code != 200:
            return []
            
        soup = BeautifulSoup(res.text, "html.parser")
        articles = soup.find_all("article")
        announcement_list = []

        for article in articles:
            header = article.find("h2")
            if not header: continue
            
            a_tag = header.find("a")
            title = header.get_text(strip=True)
            url = "https://student.uit.edu.vn" + a_tag["href"] if a_tag else ""
            
            content_div = article.find(class_="content")
            content_text = content_div.get_text(strip=True) if content_div else ""
            
            # Parsing the date from the 'submitted' span
            submitted_span = article.select_one(".submitted span")
            date_val = ""
            if submitted_span and submitted_span.has_attr("content"):
                date_val = submitted_span["content"] # ISO format string
            
            announcement_list.append({
                "title": title,
                "content": content_text,
                "date": date_val,
                "url": url
            })
            
        return announcement_list
    except Exception as e:
        print(f"Scraping error: {e}")
        return []   
    
