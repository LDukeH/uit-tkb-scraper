from app.services.school.session import (
    save_session,
    is_session_alive,
    get_valid_session,
    get_credentials_from_db,
    login_and_get_session,
    SESSION_STORE,
)
from app.services.school.schedule import (
    get_schedule,
    merge_schedule,
    load_cached_schedule,
    save_schedule,
    load_cached_exam_schedule,
    save_exam_schedule,
    get_exam_schedule,
)
from app.services.school.announcement import (
    get_latest_announcement_node_id,
    get_all_announcements,
    parse_article,
    parse_content_element,
    parse_table,
    fetch_article_content,
    get_all_announcements_full,
)
from app.services.school.tuition import (
    get_tuition_fee,
    load_cached_tuition,
    save_tuition,
    save_tuition_bulk,
    load_all_cached_tuition,
)
from app.services.school.grades import (
    get_grades,
    load_cached_grade,
    save_grade,
    save_grades_bulk,
    load_all_cached_grades,
)
from app.services.school.constants import (  
    LOGIN_URL,
    SCHEDULE_URL,
    SESSION_DURATION,
    BASE_URL,
    ANNOUNCEMENT_URL,
    TUITION_URL,
    GRADES_URL,
    DAYS,
    PERIOD_TIME,
)

if __name__ == "__main__":
    from app.services.school.announcement import get_all_announcements_full
    data = get_all_announcements_full(max_pages=2)
    print(f"Total fetched: {len(data)}")
    for item in data[:2]:
        print("---")
        print(f"ID: {item['node_id']}")
        print(f"Title: {item['title']}")
        print(f"Date: {item['date']}")
        print(f"Content preview: {item['details']['content'][:200]}")