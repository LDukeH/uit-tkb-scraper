from app.services.school_service import get_all_announcements_full
from app.services.data_insert import insert_announcements
from app.services.analyze_service import label_announcements
from fastapi import HTTPException
import os

def handler(request):

    cron_secret = os.getenv("CRON_SECRET")
    auth_header = request.headers.get("authorization", "")
    
    if not cron_secret or f"Bearer {cron_secret}" != auth_header:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        # Run the scraper
        data = get_all_announcements_full()
        data = label_announcements(data)
        insert_announcements(data)
        
        return {
            "success": True,
            "count": len(data),
            "message": f"Successfully scraped {len(data)} announcements"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))