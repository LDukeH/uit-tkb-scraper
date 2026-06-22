import certifi
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

client = MongoClient(host=MONGO_URL, tlsCAFile=certifi.where())

db = client["uit-service"]
announcement_collection = db["announcements"]

schedule_collection = db["schedules"]
exam_collection = db["exam_schedules"]
tuition_collection = db["tuition_fees"]
grades_collection = db["grades"]

try:
	# luu cache lich theo user thong tin ky thi luu rieng
	schedule_collection.create_index(
		[("user_id", 1)],
		unique=True,
		name="unique_user"
	)
	# tao index ttl tren expires_at de xoa cache het han
	schedule_collection.create_index("expires_at", expireAfterSeconds=0, name="ttl_expires_at")
except Exception:
	pass

try:
	# luu lich thi theo user va ky
	exam_collection.create_index(
		[("user_id", 1), ("lanthi", 1), ("hocky", 1), ("namhoc", 1)],
		unique=True,
		name="unique_user_exam_term"
	)
	exam_collection.create_index("expires_at", expireAfterSeconds=0, name="ttl_expires_at_exam")
except Exception:
	pass

try:
	# luu hoc phi theo user va ky
	tuition_collection.create_index(
		[("user_id", 1), ("hocky", 1), ("namhoc", 1)],
		unique=True,
		name="unique_user_tuition_term"
	)
	tuition_collection.create_index("expires_at", expireAfterSeconds=0, name="ttl_expires_at_tuition")
except Exception:
	pass

deadlines_collection = db["deadlines"]

try:
	grades_collection.create_index(
		[("user_id", 1)],
		unique=True,
		name="unique_user_grades"
	)
	grades_collection.create_index("expires_at", expireAfterSeconds=0, name="ttl_expires_at_grades")
except Exception:
	pass

try:
	deadlines_collection.create_index(
		[("user_id", 1), ("year", 1), ("month", 1)],
		unique=True,
		name="unique_user_month"
	)
	deadlines_collection.create_index("expires_at", expireAfterSeconds=0, name="ttl_expires_at_deadlines")
except Exception:
	pass
