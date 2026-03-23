from fastapi import FastAPI

from app.routes.auth import router as auth_router
from app.routes.schedule import router as schedule_router
from app.routes.announcements import router as announcement_router
from app.routes.internal_scraper import router as internal_router

app = FastAPI(title="UIT Student API")

import os

print("MONGO_URL =", os.getenv("MONGO_URL"))
print("SCRAPER_SECRET =", os.getenv("SCRAPER_SECRET"))


@app.get("/")
def root():
    return {
        "message": "UIT School API is running!",
        "status": "healthy",
        "MONGO_URL":os.getenv("MONGO_URL"),
        "SCRAPER_SECRET ": os.getenv("SCRAPER_SECRET")
    }


app.include_router(auth_router)
app.include_router(schedule_router)
app.include_router(announcement_router)
app.include_router(internal_router)