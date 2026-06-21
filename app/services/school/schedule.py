import re
import os
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from app.services.school.constants import (
    SCHEDULE_URL, BASE_URL, DAYS, PERIOD_TIME,
)


def get_schedule(session):
    res = session.get(SCHEDULE_URL)
    if not res or res.status_code != 200:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.select_one(".tkb-table")
    if not table:
        return []

    rows = table.select("tbody tr")
    raw_schedule = []
    rowspan_tracker = {}

    for row in rows:
        cols = row.find_all("td")
        if not cols:
            continue

        raw_period = cols[0].get_text(strip=True)
        match = re.search(r"Tiết\s*(\d+)", raw_period)
        if not match:
            continue
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


def load_cached_schedule(user_id: str):
    """Lấy tkb đã cache từ DB theo user_id.

    Note: cache tkb được lưu theo từng user; lịch thi (lanthi/hocky/namhoc)
    được lưu riêng nếu cần.
    """
    try:
        from app.core.db import schedule_collection
        doc = schedule_collection.find_one({"user_id": user_id}, {"_id": 0})
        return doc
    except Exception as e:
        print(f"Error loading cached schedule: {e}")
        return None


def save_schedule(user_id: str, schedule_rows: list, ttl_days: int = None):
    """Lưu hoặc cập nhật tkb cho user với thời gian hết hạn (`expires_at`).

    `ttl_days` mặc định lấy từ env `SCHEDULE_CACHE_TTL_DAYS` hoặc 7 ngày.
    """
    try:
        from app.core.db import schedule_collection

        if ttl_days is None:
            try:
                ttl_days = int(os.getenv("SCHEDULE_CACHE_TTL_DAYS", "7"))
            except Exception:
                ttl_days = 7

        expires = datetime.utcnow() + timedelta(days=ttl_days)

        doc = {
            "user_id": user_id,
            "schedule": schedule_rows,
            "updated_at": datetime.utcnow(),
            "expires_at": expires,
            "source": "student.uit.edu.vn",
        }

        schedule_collection.update_one(
            {"user_id": user_id},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        print(f"Error saving schedule: {e}")
        return False


def load_cached_exam_schedule(user_id: str, lanthi: int, hocky: int, namhoc: int):
    """Lấy lịch thi đã cache từ DB theo user và học kỳ."""
    try:
        from app.core.db import exam_collection
        return exam_collection.find_one(
            {"user_id": user_id, "lanthi": lanthi, "hocky": hocky, "namhoc": namhoc},
            {"_id": 0}
        )
    except Exception as e:
        print(f"Error loading cached exam schedule: {e}")
        return None


def save_exam_schedule(user_id: str, lanthi: int, hocky: int, namhoc: int, exam_rows: list, ttl_days: int = None):
    """Lưu hoặc cập nhật lịch thi cho user/học kỳ với thời gian hết hạn."""
    try:
        from app.core.db import exam_collection

        if ttl_days is None:
            try:
                ttl_days = int(os.getenv("EXAM_CACHE_TTL_DAYS", os.getenv("SCHEDULE_CACHE_TTL_DAYS", "7")))
            except Exception:
                ttl_days = 7

        expires = datetime.utcnow() + timedelta(days=ttl_days)

        doc = {
            "user_id": user_id,
            "lanthi": lanthi,
            "hocky": hocky,
            "namhoc": namhoc,
            "exam_schedule": exam_rows,
            "updated_at": datetime.utcnow(),
            "expires_at": expires,
            "source": "student.uit.edu.vn",
        }

        exam_collection.update_one(
            {"user_id": user_id, "lanthi": lanthi, "hocky": hocky, "namhoc": namhoc},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        print(f"Error saving exam schedule: {e}")
        return False


def get_exam_schedule(session, lanthi: int = 1, hocky: int = 1, namhoc: int = 2025) -> list:
    """Lấy lịch thi với các tham số đã cho bằng session đã xác thực.

    Returns:
        Danh sách các dòng với keys: `stt`, `ma_mh`, `ma_lop`, `ca_tiet_thi`, `thu_thi`,
        `ngay_thi`, `phong_thi`, `ghi_chu`.
    """
    url = BASE_URL + "/sinhvien/lichhoc/lichthi"
    params = {"lanthi": str(lanthi), "hocky": str(hocky), "namhoc": str(namhoc)}

    try:
        res = session.get(url, params=params, timeout=10)
        if res.status_code != 200:
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table.sticky-enabled.tableheader-processed.sticky-table") or soup.find("table")
        if not table:
            return []

        rows = table.select("tbody tr")
        results = []
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if not cols:
                continue

            # ánh xạ cột sang trường, xử lý thiếu cell
            def col(i):
                return cols[i] if i < len(cols) else ""

            try:
                stt = int(col(0)) if col(0).isdigit() else col(0)
            except:
                stt = col(0)

            item = {
                "stt": stt,
                "ma_mh": col(1),
                "ma_lop": col(2),
                "ca_tiet_thi": col(3),
                "thu_thi": col(4),
                "ngay_thi": col(5),
                "phong_thi": col(6),
                "ghi_chu": col(7),
            }
            results.append(item)

        return results

    except Exception as e:
        print(f"Error fetching exam schedule: {e}")
        return []