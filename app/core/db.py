import threading
from typing import Optional
import certifi
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import OperationFailure
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

_client: Optional[MongoClient] = None
_lock = threading.Lock()
_indexes_created = False
_indexes_lock = threading.Lock()


def get_client() -> MongoClient:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = MongoClient(
                    host=MONGO_URL,
                    tlsCAFile=certifi.where(),
                    connectTimeoutMS=3000,
                    serverSelectionTimeoutMS=5000,
                    maxPoolSize=10,
                    minPoolSize=0,
                )
    return _client


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def _ensure_indexes() -> None:
    global _indexes_created
    if _indexes_created:
        return
    with _indexes_lock:
        if _indexes_created:
            return

        client = get_client()
        db = client["uit-service"]

        _try_index(db["schedules"], [
            ([("user_id", 1)], {"unique": True, "name": "unique_user"}),
            ([("expires_at", 1)], {"expireAfterSeconds": 0, "name": "ttl_expires_at"}),
        ])
        _try_index(db["exam_schedules"], [
            ([("user_id", 1), ("lanthi", 1), ("hocky", 1), ("namhoc", 1)],
             {"unique": True, "name": "unique_user_exam_term"}),
            ([("expires_at", 1)], {"expireAfterSeconds": 0, "name": "ttl_expires_at_exam"}),
        ])
        _try_index(db["tuition_fees"], [
            ([("user_id", 1), ("hocky", 1), ("namhoc", 1)],
             {"unique": True, "name": "unique_user_tuition_term"}),
            ([("expires_at", 1)], {"expireAfterSeconds": 0, "name": "ttl_expires_at_tuition"}),
        ])
        _try_index(db["deadlines"], [
            ([("user_id", 1), ("year", 1), ("month", 1)],
             {"unique": True, "name": "unique_user_month"}),
            ([("expires_at", 1)], {"expireAfterSeconds": 0, "name": "ttl_expires_at_deadlines"}),
        ])
        # Drop legacy index if it exists (old single-field unique on user_id)
        try:
            db["grades"].drop_index("unique_user_grades")
        except Exception:
            pass

        _try_index(db["grades"], [
            ([("user_id", 1), ("hocky", 1), ("namhoc", 1)],
             {"unique": True, "name": "unique_user_grade_term"}),
            ([("expires_at", 1)], {"expireAfterSeconds": 0, "name": "ttl_expires_at_grade"}),
        ])
        _try_index(db["sessions"], [
            ([("token", 1)], {"unique": True, "name": "unique_token"}),
            ([("expires", 1)], {"expireAfterSeconds": 0, "name": "ttl_expires"}),
        ])

        _indexes_created = True


def _try_index(collection: Collection, specs: list) -> None:
    for keys, kwargs in specs:
        try:
            collection.create_index(keys, **kwargs)
        except OperationFailure:
            pass
        except Exception:
            pass


def get_announcement_collection() -> Collection:
    _ensure_indexes()
    return get_client()["uit-service"]["announcements"]


def get_schedule_collection() -> Collection:
    _ensure_indexes()
    return get_client()["uit-service"]["schedules"]


def get_exam_collection() -> Collection:
    _ensure_indexes()
    return get_client()["uit-service"]["exam_schedules"]


def get_tuition_collection() -> Collection:
    _ensure_indexes()
    return get_client()["uit-service"]["tuition_fees"]


def get_deadlines_collection() -> Collection:
    _ensure_indexes()
    return get_client()["uit-service"]["deadlines"]


def get_grade_collection() -> Collection:
    _ensure_indexes()
    return get_client()["uit-service"]["grades"]


def get_session_collection() -> Collection:
    _ensure_indexes()
    return get_client()["uit-service"]["sessions"]
