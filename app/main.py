import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

from app.routes.auth import router as auth_router
from app.routes.schedule import router as schedule_router
from app.routes.announcements import router as announcement_router
from app.routes.internal_scraper import router as internal_router
from app.routes.tuition import router as tuition_router
from app.routes.deadlines import router as deadlines_router
from app.routes.grades import router as grades_router
from app.middleware.timing import TimingMiddleware
from app.core.timing import TimingCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("uit.main")

_APP_START_TIME = time.perf_counter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_start = time.perf_counter()
    from app.core.db import get_client
    mongo_client = get_client()
    try:
        ping_start = time.perf_counter()
        mongo_client.admin.command("ping")
        mongo_ping_ms = (time.perf_counter() - ping_start) * 1000.0
        logger.info("[TIMING] MongoDB ping: %.1f ms", mongo_ping_ms)
    except Exception as e:
        logger.warning("[TIMING] MongoDB ping failed: %s", e)

    startup_duration = (time.perf_counter() - startup_start) * 1000.0
    logger.info("[TIMING] App lifespan startup: %.1f ms", startup_duration)

    yield

    shutdown_start = time.perf_counter()
    from app.core.db import close_client
    close_client()
    shutdown_duration = (time.perf_counter() - shutdown_start) * 1000.0
    logger.info("[TIMING] Shutdown (MongoDB close): %.1f ms", shutdown_duration)


app = FastAPI(title="UIT Student API", lifespan=lifespan)
app.add_middleware(TimingMiddleware)


@app.get("/")
def root(request: Request = None):
    return {"message": "UIT School API is running!", "status": "healthy"}


@app.get("/timing-stats")
def timing_stats():
    import psutil
    process = psutil.Process()
    uptime_s = time.time() - process.create_time()
    return {
        "app_uptime_seconds": round(uptime_s, 1),
        "cold_start_ms": round((time.perf_counter() - _APP_START_TIME) * 1000.0, 1),
    }


app.include_router(auth_router)
app.include_router(schedule_router)
app.include_router(announcement_router)
app.include_router(internal_router)
app.include_router(tuition_router)
app.include_router(deadlines_router)
app.include_router(grades_router)