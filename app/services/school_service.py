import requests
from bs4 import BeautifulSoup
import re
import time
import os
from datetime import datetime, timedelta

LOGIN_URL = "https://student.uit.edu.vn/user/login"
SCHEDULE_URL = "https://student.uit.edu.vn/sinhvien/tkb"
SESSION_DURATION = 900  

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


BASE_URL = "https://student.uit.edu.vn"
ANNOUNCEMENT_URL = BASE_URL + "/thong-bao-chung?page="

def get_all_announcements(max_pages=10):
    results = []

    for page in range(max_pages):
        url = ANNOUNCEMENT_URL + str(page)

        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.text, "html.parser")
            articles = soup.find_all("article")

            if not articles:
                break

            for article in articles:
                data = parse_article(article)
                if data:
                    results.append(data)

            # tam dung tranh block
            time.sleep(0.5)

        except Exception as e:
            print(f"Error page {page}: {e}")
            continue

    return results


def parse_article(article):
    try:
        node_id = article.get("id", "").replace("node-", "")

        header = article.find("h2")
        if not header:
            return None

        a_tag = header.find("a")
        title = header.get_text(strip=True)

        link = ""
        if a_tag and a_tag.get("href"):
            link = BASE_URL + a_tag["href"]

        date_val = ""
        submitted_span = article.select_one(".submitted span")
        if submitted_span and submitted_span.has_attr("content"):
            date_val = submitted_span["content"]

        content_text = ""
        content_div = article.find(class_="content")
        if content_div:
            content_text = content_div.get_text(separator="\n", strip=True)

        return {
            "node_id": node_id,
            "title": title,
            "preview": content_text,
            "date": date_val,
            "link": link
        }

    except Exception as e:
        print("Parse error:", e)
        return None

def parse_content_element(element) -> str:
    result = []

    for child in element.children:
        if isinstance(child, str):
            text = child.strip()
            if text:
                result.append(text)
            continue

        tag = child.name

        if tag == "table":
            result.append(parse_table(child))

        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "li"):
            inner = child.get_text(separator=" ", strip=True)
            if inner:
                result.append(inner)

        elif tag in ("ul", "ol"):
            for li in child.find_all("li", recursive=False):
                result.append("- " + li.get_text(separator=" ", strip=True))

        elif tag == "br":
            result.append("")

        else:
            # du phong lay text
            inner = child.get_text(separator=" ", strip=True)
            if inner:
                result.append(inner)

    return "\n".join(result)


def parse_table(table) -> str:
    rows = table.find_all("tr")
    if not rows:
        return ""

    table_data = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        table_data.append([cell.get_text(separator=" ", strip=True) for cell in cells])

    if not table_data:
        return ""

    # chuan hoa so cot
    col_count = max(len(row) for row in table_data)
    for row in table_data:
        while len(row) < col_count:
            row.append("")

    # tinh chieu rong cot
    col_widths = [
        max(len(row[i]) for row in table_data)
        for i in range(col_count)
    ]

    lines = []
    for i, row in enumerate(table_data):
        padded = [row[j].ljust(col_widths[j]) for j in range(col_count)]
        lines.append("| " + " | ".join(padded) + " |")
        if i == 0:  # header separator
            lines.append("| " + " | ".join("-" * col_widths[j] for j in range(col_count)) + " |")

    return "\n".join(lines)


def fetch_article_content(article_summary: dict) -> dict:
    try:
        res = requests.get(article_summary["link"], timeout=10)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, "html.parser")
        article = soup.find("article")
        if not article:
            return None

        content_div = article.select_one(".field-name-body .field-item")
        full_content = parse_content_element(content_div) if content_div else ""

        related = []
        for a in soup.select("#block-views-contents-block-1 .view-content a"):
            href = a.get("href", "")
            related.append({
                "title": a.get_text(strip=True),
                "link": BASE_URL + href if href.startswith("/") else href
            })

        return {
            "node_id": article_summary["node_id"],
            "title": article_summary["title"],
            "date": article_summary["date"],
            "link": article_summary["link"],
            "details": {
                "content": full_content,
                "related": related
                        }
        }

    except Exception as e:
        print(f"Error fetching {article_summary.get('link')}: {e}")
        return None
    


def get_all_announcements_full(max_pages=10) -> list:
    summaries = get_all_announcements(max_pages)
    if not summaries:
        print("No summaries fetched — scraping failed or site blocked.")
        return []

    results = []
    for i, summary in enumerate(summaries):
        print(f"Fetching [{i+1}/{len(summaries)}]: {summary['title'][:60]}...")
        try:
            full = fetch_article_content(summary)
            if full:
                full["preview"] = summary.get("preview", "")
                results.append(full)
            else:
                print(f"  ⚠ fetch_article_content returned None for: {summary['link']}")
        except Exception as e:
            print(f"  ✗ Exception on {summary['link']}: {e}")
        time.sleep(0.5)

    print(f"Successfully fetched: {len(results)}/{len(summaries)}")
    return results


def load_cached_schedule(user_id: str):
    """Return cached schedule document for given user_id.

    Note: schedule cache is stored per-user only; exam schedules (lanthi/hocky/namhoc)
    are stored separately if needed.
    """
    try:
        from app.core.db import schedule_collection
        doc = schedule_collection.find_one({"user_id": user_id}, {"_id": 0})
        return doc
    except Exception as e:
        print(f"Error loading cached schedule: {e}")
        return None


def save_schedule(user_id: str, schedule_rows: list, ttl_days: int = None):
    """Upsert schedule for user with an expiry (`expires_at`).

    `ttl_days` defaults to env `SCHEDULE_CACHE_TTL_DAYS` or 7 days.
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
    """Return cached exam schedule for a user and term."""
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
    """Upsert exam schedule for a user/term with expiry."""
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
    """Fetch exam schedule (lich thi) for given parameters using an authenticated session.

    Returns list of rows with keys: `stt`, `ma_mh`, `ma_lop`, `ca_tiet_thi`, `thu_thi`,
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

            # map cot sang truong xu ly thieu cell
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


TUITION_URL = BASE_URL + "/tracuu/hocphi"


def get_tuition_fee(session) -> dict:
    """Scrape tuition fee page using an authenticated session.

    Returns a dict with keys: `student_info`, `bank_info`, `semesters`.
    Each semester in `semesters` includes `chi_tiet_mon` (subject detail list).
    """
    try:
        res = session.get(TUITION_URL, timeout=10)
        if res.status_code != 200:
            return {"student_info": None, "bank_info": None, "semesters": []}

        soup = BeautifulSoup(res.text, "html.parser")

        # --- Student info ---
        student_info = {}
        student_table = soup.select_one("#edit-thongtinsv table")
        if student_table:
            for row in student_table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if "Họ và tên" in label:
                    student_info["ho_ten"] = value
                elif "MSSV" in label:
                    student_info["mssv"] = value
                elif "Ngày sinh" in label:
                    student_info["ngay_sinh"] = value
                elif "Khoa" in label:
                    student_info["khoa"] = value
                elif "Hệ đào tạo" in label:
                    student_info["he_dao_tao"] = value

        # Defaults for missing fields
        student_info.setdefault("ho_ten", "")
        student_info.setdefault("mssv", "")
        student_info.setdefault("ngay_sinh", "")
        student_info.setdefault("khoa", "")
        student_info.setdefault("he_dao_tao", "")

        # --- Bank info ---
        bank_info = {}
        bank_div = soup.select_one("#edit-thongtinsv hr ~ div")
        if bank_div:
            bank_text = bank_div.get_text("\n", strip=True)
            for line in bank_text.split("\n"):
                line_clean = line.strip()
                if "Tên tài khoản:" in line_clean:
                    bank_info["ten_tai_khoan"] = line_clean.split(":", 1)[1].strip()
                elif "Số tài khoản:" in line_clean:
                    bank_info["so_tai_khoan"] = line_clean.split(":", 1)[1].strip()
                elif "Tại ngân hàng:" in line_clean:
                    bank_info["ngan_hang"] = line_clean.split(":", 1)[1].strip()
                elif "Nội dung:" in line_clean:
                    bank_info["noi_dung_chuyen_khoan"] = line_clean.split(":", 1)[1].strip()

        bank_info.setdefault("ten_tai_khoan", "")
        bank_info.setdefault("so_tai_khoan", "")
        bank_info.setdefault("ngan_hang", "")
        bank_info.setdefault("noi_dung_chuyen_khoan", "")

        # --- Semester fieldsets ---
        semesters = []
        all_fieldsets = soup.select("fieldset.container-inline")
        for fs in all_fieldsets:
            fs_id = fs.get("id", "")
            # Only process tuition-semester fieldsets (skip thongtinsv)
            if not fs_id.startswith("edit-thongtinhp-"):
                continue

            # Parse hocky and namhoc from id: edit-thongtinhp-{hocky}-{namhoc}
            match = re.match(r"edit-thongtinhp-(\d+)-(\d+)", fs_id)
            if not match:
                continue
            hocky = int(match.group(1))
            namhoc = int(match.group(2))

            sem_data = {
                "hocky": hocky,
                "namhoc": namhoc,
                "so_tc_dang_ky": "",
                "mon_dang_ky": "",
                "hoc_phi": "",
                "phi_khac": "",
                "so_tien_phai_dong": "",
                "no_hoc_ky_truoc": "",
                "so_tien_da_dong": "",
                "con_no": "",
                "ngan_hang": "",
                "thoi_gian_dong": "",
                "ghi_chu": "",
                "chi_tiet_mon": [],
            }

            # Extract rows from main table
            main_table = fs.select_one("table")
            if main_table:
                for row in main_table.find_all("tr"):
                    cells = row.find_all("td")
                    if len(cells) < 2:
                        continue
                    label = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)

                    if "Số TC học phí đăng ký" in label:
                        sem_data["so_tc_dang_ky"] = value
                    elif "Môn đăng ký" in label:
                        sem_data["mon_dang_ky"] = value
                    elif "Học phí" in label and "Phí khác" not in label:
                        sem_data["hoc_phi"] = value
                    elif "Phí khác" in label:
                        sem_data["phi_khac"] = value
                    elif "Số tiền phải đóng" in label:
                        sem_data["so_tien_phai_dong"] = value
                    elif "Nợ học kỳ trước" in label:
                        sem_data["no_hoc_ky_truoc"] = value
                    elif "Số tiền đã đóng" in label:
                        sem_data["so_tien_da_dong"] = value
                    elif "Còn nợ" in label:
                        sem_data["con_no"] = value
                    elif "Tại ngân hàng" in label:
                        sem_data["ngan_hang"] = value
                    elif "Thời gian đóng" in label:
                        sem_data["thoi_gian_dong"] = value
                    elif "Ghi chú" in label:
                        sem_data["ghi_chu"] = value

            # Extract chi_tiet_mon from hidden div
            detail_div = fs.select_one(f"div[id^='chitiethp']")
            if detail_div:
                detail_table = detail_div.select_one("table")
                if detail_table:
                    detail_rows = detail_table.find_all("tr")
                    for drow in detail_rows:
                        dcells = drow.find_all("td")
                        if not dcells or dcells[0].get_text(strip=True) == "STT":
                            continue
                        try:
                            stt = int(dcells[0].get_text(strip=True))
                        except:
                            continue
                        ma_mh = dcells[1].get_text(strip=True) if len(dcells) > 1 else ""
                        try:
                            so_tchp = float(dcells[2].get_text(strip=True))
                        except:
                            so_tchp = 0.0
                        hoc_lai = dcells[3].get_text(strip=True) if len(dcells) > 3 else ""
                        try:
                            don_gia = int(dcells[4].get_text(strip=True))
                        except:
                            don_gia = 0
                        try:
                            thanh_tien = int(dcells[5].get_text(strip=True))
                        except:
                            thanh_tien = 0
                        ghi_chu = dcells[6].get_text(strip=True) if len(dcells) > 6 else ""

                        sem_data["chi_tiet_mon"].append({
                            "stt": stt,
                            "ma_mh": ma_mh,
                            "so_tchp": so_tchp,
                            "hoc_lai_cai_thien": hoc_lai,
                            "don_gia": don_gia,
                            "thanh_tien": thanh_tien,
                            "ghi_chu": ghi_chu,
                        })

            semesters.append(sem_data)

        return {
            "student_info": student_info,
            "bank_info": bank_info,
            "semesters": semesters,
        }

    except Exception as e:
        print(f"Error fetching tuition fee: {e}")
        return {"student_info": None, "bank_info": None, "semesters": []}


def load_cached_tuition(user_id: str, hocky: int, namhoc: int):
    """Return cached tuition document for a user and term."""
    try:
        from app.core.db import tuition_collection
        return tuition_collection.find_one(
            {"user_id": user_id, "hocky": hocky, "namhoc": namhoc},
            {"_id": 0}
        )
    except Exception as e:
        print(f"Error loading cached tuition: {e}")
        return None


def save_tuition(user_id: str, hocky: int, namhoc: int,
                 student_info: dict, bank_info: dict, sem_data: dict,
                 ttl_days: int = None):
    """Upsert tuition data for a user/term with expiry."""
    try:
        from app.core.db import tuition_collection

        if ttl_days is None:
            try:
                ttl_days = int(os.getenv("TUITION_CACHE_TTL_DAYS",
                             os.getenv("SCHEDULE_CACHE_TTL_DAYS", "7")))
            except Exception:
                ttl_days = 7

        expires = datetime.utcnow() + timedelta(days=ttl_days)

        doc = {
            "user_id": user_id,
            "hocky": hocky,
            "namhoc": namhoc,
            "student_info": student_info,
            "bank_info": bank_info,
            **sem_data,
            "updated_at": datetime.utcnow(),
            "expires_at": expires,
            "source": "student.uit.edu.vn",
        }

        tuition_collection.update_one(
            {"user_id": user_id, "hocky": hocky, "namhoc": namhoc},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        print(f"Error saving tuition: {e}")
        return False


def load_all_cached_tuition(user_id: str):
    """Return all cached tuition semesters for a user, as structured data."""
    try:
        from app.core.db import tuition_collection
        docs = list(tuition_collection.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort([("namhoc", -1), ("hocky", -1)]))

        if not docs:
            return None

        # Reconstruct TuitionData structure
        student_info = docs[0].get("student_info", {})
        bank_info = docs[0].get("bank_info", {})

        semesters = []
        for doc in docs:
            semesters.append({
                "hocky": doc.get("hocky"),
                "namhoc": doc.get("namhoc"),
                "so_tc_dang_ky": doc.get("so_tc_dang_ky", ""),
                "mon_dang_ky": doc.get("mon_dang_ky", ""),
                "hoc_phi": doc.get("hoc_phi", ""),
                "phi_khac": doc.get("phi_khac", ""),
                "so_tien_phai_dong": doc.get("so_tien_phai_dong", ""),
                "no_hoc_ky_truoc": doc.get("no_hoc_ky_truoc", ""),
                "so_tien_da_dong": doc.get("so_tien_da_dong", ""),
                "con_no": doc.get("con_no", ""),
                "ngan_hang": doc.get("ngan_hang", ""),
                "thoi_gian_dong": doc.get("thoi_gian_dong", ""),
                "ghi_chu": doc.get("ghi_chu", ""),
                "chi_tiet_mon": doc.get("chi_tiet_mon", []),
            })

        return {
            "student_info": student_info,
            "bank_info": bank_info,
            "semesters": semesters,
        }
    except Exception as e:
        print(f"Error loading all cached tuition: {e}")
        return None


if __name__ == "__main__":
    data = get_all_announcements_full(max_pages=2)
    print(f"Total fetched: {len(data)}")
    for item in data[:2]:
        print("---")
        print(f"ID: {item['node_id']}")
        print(f"Title: {item['title']}")
        print(f"Date: {item['date']}")
        print(f"Content preview: {item['details']['content'][:200]}")

