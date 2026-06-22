from app.services.school_service import get_all_announcements_full
from app.services.data_insert import insert_announcements
from app.services.analyze_service import label_announcements

from fastapi import APIRouter, HTTPException, Query
import os
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
def run_scraper(key: str = Query(description="Secret key for authentication")):
    if key != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = get_all_announcements_full()
    data = label_announcements(data)
    insert_announcements(data)

    return {"success": True, "count": len(data)}