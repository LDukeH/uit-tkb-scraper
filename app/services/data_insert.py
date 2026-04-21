from app.core.db import announcement_collection
from datetime import datetime


def insert_announcements(data_list):
    for item in data_list:
        doc = {
            "_id": item["node_id"],
            "node_id": item["node_id"],
            "title": item["title"],
            "link": item["link"],
            "preview": item.get("preview", ""),
            "date": item["date"],
            "source": "student.uit.edu.vn",
            "updated_at": datetime.utcnow(),
            "details": {
                "content": item.get("content", ""),
                "related": item.get("related", [])
            }
        }

        announcement_collection.update_one(
            {"_id": doc["_id"]},
            {"$set": doc},
            upsert=True
        )
