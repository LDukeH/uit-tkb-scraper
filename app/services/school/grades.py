import re
import os
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from app.services.school.constants import GRADES_URL


def get_grades(session) -> dict:
    """Scrape trang điểm học phần bằng session đã xác thực.

    Trang trả về điểm của tất cả học kỳ trong một bảng. Hàm này
    cần POST form Drupal (với form_build_id, form_token, form_id)
    để lấy dữ liệu điểm thực tế.

    Returns:
        dict với keys: `student_profile`, `semesters`, `summary`.
    """
    try:
        # Đầu tiên GET để lấy form tokens
        get_res = session.get(GRADES_URL, timeout=10)
        if get_res.status_code != 200:
            return {"student_profile": None, "semesters": [], "summary": None}

        soup_get = BeautifulSoup(get_res.text, "html.parser")
        form = soup_get.select_one("form#uit-sinhvien-tracuu-kqhoctap")
        if not form:
            # Thử parse trực tiếp nếu không tìm thấy form (có thể đã hiển thị dữ liệu)
            soup = soup_get
        else:
            # Lấy form tokens và POST
            payload = {}
            for inp in form.find_all("input"):
                name = inp.get("name")
                if name:
                    payload[name] = inp.get("value", "")
            # POST để lấy dữ liệu điểm
            post_res = session.post(GRADES_URL, data=payload, timeout=10)
            if post_res.status_code != 200:
                return {"student_profile": None, "semesters": [], "summary": None}
            soup = BeautifulSoup(post_res.text, "html.parser")
            # Tìm lại form trong response
            form = soup.select_one("form#uit-sinhvien-tracuu-kqhoctap")
            if not form:
                return {"student_profile": None, "semesters": [], "summary": None}

        # --- Thông tin sinh viên (bảng đầu tiên) ---
        profile = {"ho_ten": "", "mssv": "", "ngay_sinh": "", "gioi_tinh": "",
                   "lop_sinh_hoat": "", "khoa": "", "bac_dao_tao": "",
                   "he_dao_tao": "", "nganh": ""}
        profile_table = soup.select_one("form#uit-sinhvien-tracuu-kqhoctap table")
        if profile_table:
            for row in profile_table.find_all("tr"):
                cells = row.find_all("td")
                for i in range(0, len(cells) - 1, 2):
                    if i + 1 >= len(cells):
                        continue
                    label = cells[i].get_text(strip=True).rstrip(":")
                    value = cells[i + 1].get_text(strip=True)
                    if "Họ và tên" in label:
                        profile["ho_ten"] = value
                    elif "Ngày sinh" in label:
                        profile["ngay_sinh"] = value
                    elif "Giới tính" in label:
                        profile["gioi_tinh"] = value
                    elif "Mã SV" in label:
                        profile["mssv"] = value
                    elif "Lớp sinh hoạt" in label:
                        profile["lop_sinh_hoat"] = value
                    elif "Khoa" in label:
                        profile["khoa"] = value
                    elif "Bậc đào tạo" in label:
                        profile["bac_dao_tao"] = value
                    elif "Hệ đào tạo" in label:
                        profile["he_dao_tao"] = value
                    elif "Ngành" in label:
                        profile["nganh"] = value

        # --- Bảng điểm (bảng thứ hai) ---
        all_tables = soup.find_all("table")
        grade_table = all_tables[1] if len(all_tables) > 1 else None

        semesters = []
        current_sem = None
        summary = {
            "so_tin_chi_da_hoc": None,
            "so_tin_chi_tich_luy": None,
            "diem_trung_binh_chung": None,
            "diem_trung_binh_chung_tich_luy": None,
        }

        if grade_table:
            rows = grade_table.find_all("tr")
            for row in rows:
                # Kiểm tra header học kỳ
                tds = row.find_all("td")
                cols = row.find_all(["td", "th"])
                col_texts = [c.get_text(strip=True).replace("\xa0", " ").strip() for c in cols]
                colspan = tds[0].get("colspan") if tds else None

                # Phát hiện header học kỳ
                if colspan and colspan == "10" and len(tds) == 1:
                    text = tds[0].get_text(strip=True).replace("\xa0", " ")
                    match = re.search(r"Học kỳ\s*(\d+)\s*-\s*Năm học\s*(\d+)-(\d+)", text)
                    if match:
                        # Lưu học kỳ trước
                        if current_sem and current_sem["subjects"]:
                            semesters.append(current_sem)
                        hocky = int(match.group(1))
                        namhoc = int(match.group(2))
                        current_sem = {
                            "hocky": hocky,
                            "namhoc": namhoc,
                            "so_tin_chi": None,
                            "diem_trung_binh": "",
                            "subjects": [],
                        }
                    continue

                # Phát hiện dòng tổng kết footer (luôn ở cuối bảng)
                if cols and len(col_texts) >= 2:
                    # Dòng tổng kết có nhãn ở ô đầu tiên (colspan=3)
                    label = col_texts[0] if len(col_texts) > 0 else ""
                    # Tìm ô giá trị — là <td> thứ hai có <strong>
                    value_cell = ""
                    for cell in cols:
                        strong = cell.find("strong")
                        if strong and cell != cols[0]:
                            value_cell = strong.get_text(strip=True)
                            break
                    if "Số tín chỉ đã học" in label:
                        try:
                            summary["so_tin_chi_da_hoc"] = float(value_cell) if value_cell else None
                        except:
                            pass
                        continue
                    elif "Số tín chỉ tích lũy" in label:
                        try:
                            summary["so_tin_chi_tich_luy"] = float(value_cell) if value_cell else None
                        except:
                            pass
                        continue
                    elif "Điểm trung bình chung" in label and "tích lũy" not in label:
                        # Value is in the last <td> with <strong>
                        for cell in reversed(cols):
                            strong = cell.find("strong")
                            if strong:
                                try:
                                    summary["diem_trung_binh_chung"] = float(strong.get_text(strip=True))
                                except:
                                    pass
                                break
                        continue
                    elif "Điểm trung bình chung tích lũy" in label:
                        for cell in reversed(cols):
                            strong = cell.find("strong")
                            if strong:
                                try:
                                    summary["diem_trung_binh_chung_tich_luy"] = float(strong.get_text(strip=True))
                                except:
                                    pass
                                break
                        continue

                # Phát hiện dòng tổng kết học kỳ ("Trung bình học kỳ")
                if current_sem and col_texts and "Trung bình học kỳ" in (col_texts[2] if len(col_texts) > 2 else ""):
                    try:
                        tc_str = col_texts[3] if len(col_texts) > 3 else "0"
                        current_sem["so_tin_chi"] = float(tc_str)
                    except:
                        pass
                    # diem_trung_binh nằm ở <td> cuối có <strong>
                    for cell in cols:
                        strong = cell.find("strong")
                        if strong:
                            try:
                                current_sem["diem_trung_binh"] = float(strong.get_text(strip=True))
                            except:
                                current_sem["diem_trung_binh"] = strong.get_text(strip=True)
                    continue

                # Phát hiện dòng môn học
                if current_sem and len(tds) >= 6:
                    stt_text = tds[0].get_text(strip=True)
                    if not stt_text or not stt_text.isdigit():
                        continue  # skip non-subject rows (spacers, etc.)

                    # Parse điểm các môn
                    def parse_score(td):
                        text = td.get_text(strip=True)
                        if not text:
                            return None
                        try:
                            return float(text)
                        except:
                            return None

                    def parse_weight(td):
                        title_attr = td.get("title", "")
                        if title_attr:
                            m = re.search(r"Trọng số:\s*(\d+)%", title_attr)
                            if m:
                                return int(m.group(1))
                        return None

                    trong_so = {}
                    diem_qt = parse_score(tds[4]) if len(tds) > 4 else None
                    w_qt = parse_weight(tds[4]) if len(tds) > 4 else None
                    if w_qt is not None:
                        trong_so["qt"] = w_qt

                    diem_gk = parse_score(tds[5]) if len(tds) > 5 else None
                    w_gk = parse_weight(tds[5]) if len(tds) > 5 else None
                    if w_gk is not None:
                        trong_so["gk"] = w_gk

                    diem_th = parse_score(tds[6]) if len(tds) > 6 else None
                    w_th = parse_weight(tds[6]) if len(tds) > 6 else None
                    if w_th is not None:
                        trong_so["th"] = w_th

                    diem_ck = parse_score(tds[7]) if len(tds) > 7 else None
                    w_ck = parse_weight(tds[7]) if len(tds) > 7 else None
                    if w_ck is not None:
                        trong_so["ck"] = w_ck

                    # Điểm HP — có thể là float hoặc "Miễn"
                    diem_hp_raw = tds[8].get_text(strip=True) if len(tds) > 8 else ""
                    diem_hp = diem_hp_raw if diem_hp_raw else None

                    ghi_chu = tds[9].get_text(strip=True) if len(tds) > 9 else ""

                    subject = {
                        "stt": int(stt_text),
                        "ma_hp": tds[1].get_text(strip=True).replace("\xa0", " ").strip(),
                        "ten_hoc_phan": tds[2].get_text(strip=True).replace("\xa0", " ").strip(),
                        "tin_chi": int(parse_score(tds[3]) or 0),
                        "diem_qt": diem_qt,
                        "diem_gk": diem_gk,
                        "diem_th": diem_th,
                        "diem_ck": diem_ck,
                        "diem_hp": diem_hp,
                        "ghi_chu": ghi_chu,
                        "trong_so": trong_so if trong_so else None,
                    }
                    current_sem["subjects"].append(subject)

            # Lưu học kỳ cuối
            if current_sem and current_sem["subjects"]:
                semesters.append(current_sem)

        return {
            "student_profile": profile,
            "semesters": semesters,
            "summary": summary,
        }

    except Exception as e:
        print(f"Error fetching grades: {e}")
        import traceback
        traceback.print_exc()
        return {"student_profile": None, "semesters": [], "summary": None}


def load_cached_grade(user_id: str, hocky: int, namhoc: int):
    """Return cached grade document for a user and term."""
    try:
        from app.core.db import get_grade_collection
        return get_grade_collection().find_one(
            {"user_id": user_id, "hocky": hocky, "namhoc": namhoc},
            {"_id": 0}
        )
    except Exception as e:
        print(f"Error loading cached grade: {e}")
        return None


def save_grade(user_id: str, hocky: int, namhoc: int,
               student_profile: dict, sem_data: dict, summary: dict,
               ttl_days: int = None):
    """Lưu hoặc cập nhật điểm cho user/học kỳ với TTL thông minh.

    Học kỳ đã hoàn thành (diem_trung_binh != 0) → TTL 365 ngày.
    Học kỳ đang xử lý (diem_trung_binh == 0 hoặc rỗng) → TTL 1 ngày.
    """
    try:
        from app.core.db import get_grade_collection

        if ttl_days is None:
            # TTL thông minh: nếu điểm cuối kỳ tồn tại và != 0, cache lâu
            diem_tb = sem_data.get("diem_trung_binh")
            try:
                if diem_tb is not None and diem_tb != "" and float(diem_tb) != 0:
                    ttl_days = 365  # Finalized semester
                else:
                    ttl_days = 1    # In progress, re-scrape daily
            except (ValueError, TypeError):
                ttl_days = 1

        expires = datetime.utcnow() + timedelta(days=ttl_days)

        doc = {
            "user_id": user_id,
            "hocky": hocky,
            "namhoc": namhoc,
            "student_profile": student_profile,
            "subjects": sem_data.get("subjects", []),
            "so_tin_chi": sem_data.get("so_tin_chi"),
            "diem_trung_binh": sem_data.get("diem_trung_binh", ""),
            "summary": summary,
            "updated_at": datetime.utcnow(),
            "expires_at": expires,
            "source": "student.uit.edu.vn",
        }

        get_grade_collection().update_one(
            {"user_id": user_id, "hocky": hocky, "namhoc": namhoc},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        print(f"Error saving grade: {e}")
        return False


def save_grades_bulk(user_id: str, student_profile: dict, summary: dict,
                     semesters: list[dict], ttl_days: int = None) -> bool:
    """Bulk upsert all grade semesters for a user in a single DB round-trip."""
    try:
        from pymongo import UpdateOne
        from app.core.db import get_grade_collection

        operations = []
        for sem in semesters:
            # TTL thông minh per semester
            if ttl_days is None:
                diem_tb = sem.get("diem_trung_binh")
                try:
                    if diem_tb is not None and diem_tb != "" and float(diem_tb) != 0:
                        sem_ttl = 365
                    else:
                        sem_ttl = 1
                except (ValueError, TypeError):
                    sem_ttl = 1
            else:
                sem_ttl = ttl_days

            expires = datetime.utcnow() + timedelta(days=sem_ttl)

            doc = {
                "user_id": user_id,
                "hocky": sem["hocky"],
                "namhoc": sem["namhoc"],
                "student_profile": student_profile,
                "subjects": sem.get("subjects", []),
                "so_tin_chi": sem.get("so_tin_chi"),
                "diem_trung_binh": sem.get("diem_trung_binh", ""),
                "summary": summary,
                "updated_at": datetime.utcnow(),
                "expires_at": expires,
                "source": "student.uit.edu.vn",
            }

            operations.append(UpdateOne(
                {"user_id": user_id, "hocky": sem["hocky"], "namhoc": sem["namhoc"]},
                {"$set": doc},
                upsert=True,
            ))

        if operations:
            get_grade_collection().bulk_write(operations)
        return True
    except Exception as e:
        print(f"Error saving grades bulk: {e}")
        return False


def load_all_cached_grades(user_id: str):
    """Return all cached grade semesters for a user."""
    try:
        from app.core.db import get_grade_collection
        docs = list(get_grade_collection().find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort([("namhoc", -1), ("hocky", -1)]))

        if not docs:
            return None

        student_profile = docs[0].get("student_profile", {})
        summary = docs[0].get("summary", {})
        semesters = []
        for doc in docs:
            semesters.append({
                "hocky": doc.get("hocky"),
                "namhoc": doc.get("namhoc"),
                "so_tin_chi": doc.get("so_tin_chi"),
                "diem_trung_binh": doc.get("diem_trung_binh", ""),
                "subjects": doc.get("subjects", []),
            })

        return {
            "student_profile": student_profile,
            "semesters": semesters,
            "summary": summary,
        }
    except Exception as e:
        print(f"Error loading all cached grades: {e}")
        return None
