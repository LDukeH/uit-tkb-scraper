from app.services.school_service import get_all_announcements_full
from app.services.data_insert import insert_announcements
from app.services.analyze_service import label_announcements

from fastapi import APIRouter, HTTPException, Query, Request
import os
import time
from pydantic import BaseModel, Field

router = APIRouter(prefix="/internal_scraper", tags=["Internal"])

SECRET_KEY = os.getenv("SCRAPER_SECRET")


class ScraperResponse(BaseModel):
    """Response from the internal scraper endpoint."""

    success: bool = Field(
        default=True,
        description="Indicates whether the scraper ran successfully",
        examples=[True],
    )
    count: int = Field(
        description="Number of announcements scraped and inserted",
        examples=[25],
    )


@router.get(
    "/",
    response_model=ScraperResponse,
    summary="Run internal scraper",
    description="Internal endpoint to trigger announcement scraping and labeling. Requires secret key.",
    response_description="Scraper execution result with count of processed announcements",
)
def run_scraper(key: str = Query(description="Secret key for authentication"), request: Request = None):
    t_request = time.perf_counter()
    timings = {}

    if key != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    t0 = time.perf_counter()
    data = get_all_announcements_full()
    timings["scrape_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

    t1 = time.perf_counter()
    data = label_announcements(data)
    timings["label_ms"] = round((time.perf_counter() - t1) * 1000.0, 1)

    t2 = time.perf_counter()
    insert_announcements(data)
    timings["db_insert_ms"] = round((time.perf_counter() - t2) * 1000.0, 1)

    timings["total_ms"] = round((time.perf_counter() - t_request) * 1000.0, 1)

    return {"success": True, "count": len(data), "timings_ms": timings}
