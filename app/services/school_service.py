import requests
from bs4 import BeautifulSoup
import re

LOGIN_URL = "https://student.uit.edu.vn/user/login"
SCHEDULE_URL = "https://student.uit.edu.vn/sinhvien/tkb"

DAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"]
PERIOD_TIME = {
    1: "07:30-08:15",
    2: "08:15-09:00",
    3: "09:00-09:45",
    4: "10:00-10:45",
    5: "10:45-11:30",
    6: "13:00-13:45",
    7: "13:45-14:30",
    8: "14:30-15:15",
    9: "15:30-16:15",
    10: "16:15-17:00",
}

def login_and_get_session(username, password):
    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = session.get(LOGIN_URL, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    form = soup.find("form", {"id": "user-login"}) or soup.find("form", {"id": "user-login-form"})
    if not form:
        print("❌ Login form not found")
        return None

    payload = {}

    for inp in form.find_all("input"):
        name = inp.get("name")
        value = inp.get("value", "")
        if name:
            payload[name] = value

    payload["name"] = username
    payload["pass"] = password

    img = form.select_one(".english-captcha-image img")
    captcha = img["alt"].replace("captcha:", "").strip() if img else ""
    payload["english_captcha_answer"] = captcha

    payload["op"] = "Đăng nhập"

    action = form.get("action")
    login_url = "https://student.uit.edu.vn" + action

    login_res = session.post(login_url, data=payload, headers=headers)

    success = "not-logged-in" not in login_res.text
    print("✅ Login success" if success else "❌ Login failed")

    return session if success else None


def get_schedule(session):
    res = session.get(SCHEDULE_URL)

    if res is None:
        print("❌ Request failed")
        return []

    if res.status_code != 200:
        print("❌ Bad response:", res.status_code)
        return []

    soup = BeautifulSoup(res.text, "html.parser")

    table = soup.select_one(".tkb-table")
    if not table:
        print("❌ Table not found (maybe access denied)")
        print(res.text[:500])
        return []

    rows = table.select("tbody tr")

    raw_schedule = []
    rowspan_tracker = {}

    for row in rows:
        cols = row.find_all("td")

        raw_period = cols[0].get_text(" ", strip=True)
        match = re.search(r"Tiết\s*(\d+)", raw_period)
        period_number = int(match.group(1)) if match else None

        if period_number is None:
            continue

        col_idx = -1

        for cell in cols[1:]:
            col_idx += 1

            while rowspan_tracker.get(col_idx, 0) > 0:
                rowspan_tracker[col_idx] -= 1
                col_idx += 1

            card = cell.select_one(".tkb-card")

            if card:
                titles = card.select(".title")
                subs = card.select(".sub")

                rowspan = int(cell.get("rowspan", 1))

                for i in range(rowspan):
                    raw_schedule.append({
                        "day": DAYS[col_idx] if col_idx < len(DAYS) else "",
                        "period": period_number + i if period_number else None,
                        "code": titles[0].text.strip() if len(titles) > 0 else "",
                        "name": titles[1].text.strip() if len(titles) > 1 else "",
                        "room": subs[0].text.strip() if len(subs) > 0 else "",
                        "teacher": subs[1].text.strip() if len(subs) > 1 else "",
                        "date": subs[2].text.strip() if len(subs) > 2 else "",
                    })

                if rowspan > 1:
                    rowspan_tracker[col_idx] = rowspan - 1

                rowspan = int(cell.get("rowspan", 1))
                if rowspan > 1:
                    rowspan_tracker[col_idx] = rowspan - 1

            else:
                rowspan = int(cell.get("rowspan", 1))
                if rowspan > 1:
                    rowspan_tracker[col_idx] = rowspan - 1

    return merge_schedule(raw_schedule)

def merge_schedule(schedule):
    merged = {}

    for item in schedule:
        key = (
            item["day"],
            item["code"],
            item["name"],
            item["room"],
            item["teacher"],
            item["date"],
        )

        if key not in merged:
            merged[key] = {
                **item,
                "periods": []
            }

        if item["period"] is not None:
            merged[key]["periods"].append(item["period"])

    result = []

    for data in merged.values():
        periods = sorted(set(data["periods"]))

        if not periods:
            continue

        ranges = []
        start = end = periods[0]

        for p in periods[1:]:
            if p == end + 1:
                end = p
            else:
                ranges.append((start, end))
                start = end = p

        ranges.append((start, end))

        period_str = ", ".join(
            f"Tiết {s}" if s == e else f"Tiết {s}-{e}"
            for s, e in ranges
        )

        time_ranges = []
        start_times = []
        end_times = []

        for s, e in ranges:
            start_time = PERIOD_TIME.get(s)
            end_time = PERIOD_TIME.get(e)

            if start_time and end_time:
                start_hour = start_time.split("-")[0]
                end_hour = end_time.split("-")[1]

                time_ranges.append(f"{start_hour}-{end_hour}")
                start_times.append(start_hour)
                end_times.append(end_hour)

        result.append({
            "day": data["day"],
            "period": period_str,
            "time": ", ".join(time_ranges),
            "start_time": min(start_times) if start_times else "",
            "end_time": max(end_times) if end_times else "",
            "code": data["code"],
            "name": data["name"],
            "room": data["room"],
            "teacher": data["teacher"],
            "date": data["date"],
        })

    return result

if __name__ == "__main__":
    username = input("Enter username: ")
    password = input("Enter password: ")

    session = login(username, password)
    if not session:
        print("❌ Login failed")
    else:
        print("✅ Fetching schedule...")

        subjects = get_schedule(session)

        for item in subjects:
            print(item)