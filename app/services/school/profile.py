from datetime import datetime, timedelta


def save_profile(user_id: str, student_profile: dict, ttl_days: int = 30) -> bool:
    """Lưu hoặc cập nhật profile sinh viên với TTL mặc định 30 ngày."""
    try:
        from app.core.db import get_profile_collection

        expires = datetime.utcnow() + timedelta(days=ttl_days)

        doc = {
            "user_id": user_id,
            "student_profile": student_profile,
            "updated_at": datetime.utcnow(),
            "expires_at": expires,
            "source": "student.uit.edu.vn",
        }

        get_profile_collection().update_one(
            {"user_id": user_id},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        print(f"Error saving profile: {e}")
        return False


def load_cached_profile(user_id: str):
    """Đọc profile sinh viên từ cache. Trả None nếu không có hoặc đã hết hạn."""
    try:
        from app.core.db import get_profile_collection
        doc = get_profile_collection().find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        if not doc:
            return None
        return doc.get("student_profile")
    except Exception as e:
        print(f"Error loading cached profile: {e}")
        return None