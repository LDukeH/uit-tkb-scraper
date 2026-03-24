import certifi
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

client = MongoClient(host=MONGO_URL, tlsCAFile=certifi.where())

db = client["uit-service"]
announcement_collection = db["announcements"]