import re
import os
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from app.services.school.constants import BASE_URL, TUITION_URL


def get_tuition_fee(session) -> dict:
    """Scrape trang học phí bằng session đã xác thực.

    Returns:
        dict với keys: `student_info`, `bank_info`, `semesters`.
        Mỗi học kỳ trong `semesters` bao gồm `chi_tiet_mon` (danh sách chi tiết môn).
    """
    try:
        res = session.get(TUITION_URL, timeout=10)
        if res.status_code != 200:
            return {"student_info": None, "bank_info": None, "semesters": []}

        soup = BeautifulSoup(res.text, "html.parser")

        # --- Thông tin sinh viên ---
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

        # Giá trị mặc định cho các trường thiếu
        student_info.setdefault("ho_ten", "")
        student_info.setdefault("mssv", "")
        student_info.setdefault("ngay_sinh", "")
        student_info.setdefault("khoa", "")
        student_info.setdefault("he_dao_tao", "")

        # --- Thông tin ngân hàng ---
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

        # --- Fieldsets học kỳ ---
        semesters = []
        all_fieldsets = soup.select("fieldset.container-inline")
        for fs in all_fieldsets:
            fs_id = fs.get("id", "")
            # Chỉ xử lý fieldsets học kỳ (bỏ qua thongtinsv)
            if not fs_id.startswith("edit-thongtinhp-"):
                continue

            # Parse hocky và namhoc từ id: edit-thongtinhp-{hocky}-{namhoc}
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

            # Lấy các dòng từ bảng chính
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

            # Lấy chi_tiet_mon từ div ẩn
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


def _parse_amount(value: str) -> int:
    """Parse a Vietnamese currency string like '4.500.000' or '4,500,000' to int."""
    if not value:
        return 0
    cleaned = re.sub(r"[^\d]", "", value)
    try:
        return int(cleaned)
    except ValueError:
        return 0


def _parse_semester_status(sem_data: dict) -> str:
    """Determine PAID or UNPAID from semester data."""
    con_no = sem_data.get("con_no", "")
    so_tien_da_dong = sem_data.get("so_tien_da_dong", "")
    if con_no:
        amount = _parse_amount(con_no)
        if amount > 0:
            return "UNPAID"
    if so_tien_da_dong:
        amount = _parse_amount(so_tien_da_dong)
        if amount > 0:
            return "PAID"
    return "UNPAID"


def _parse_deadline(sem_data: dict) -> str:
    """Extract deadline date from 'thoi_gian_dong' field if present."""
    thoi_gian_dong = sem_data.get("thoi_gian_dong", "")
    if not thoi_gian_dong:
        return ""
    patterns = [
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{2}/\d{2}/\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, thoi_gian_dong)
        if match:
            raw = match.group(1)
            if raw.startswith("20"):
                return raw
            parts = raw.split("/")
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return ""


def transform_tuition_response(raw: dict, username: str = "") -> dict:
    """Transform raw scraper output into the simplified API response format."""
    student_info = raw.get("student_info") or {}
    semesters = raw.get("semesters") or []

    student = {
        "name": student_info.get("ho_ten", ""),
        "student_id": student_info.get("mssv", username),
    }

    transformed_semesters = []
    total_due = 0
    total_paid = 0

    for sem in semesters:
        con_no = sem.get("con_no", "")
        so_tien_da_dong = sem.get("so_tien_da_dong", "")
        so_tien_phai_dong = sem.get("so_tien_phai_dong", "")

        remaining = _parse_amount(con_no) if con_no else _parse_amount(so_tien_phai_dong)
        paid = _parse_amount(so_tien_da_dong)

        status = _parse_semester_status(sem)
        deadline = _parse_deadline(sem)

        transformed_semesters.append({
            "namhoc": sem.get("namhoc"),
            "hocky": sem.get("hocky"),
            "sotien": remaining,
            "status": status,
            "deadline": deadline,
        })

        total_due += remaining
        total_paid += paid

    summary = {
        "total_due": total_due,
        "paid": total_paid,
        "remaining": total_due,
    }

    return {
        "success": True,
        "student": student,
        "summary": summary,
        "semesters": transformed_semesters,
    }


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

        # Tái cấu trúc dữ liệu TuitionData
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