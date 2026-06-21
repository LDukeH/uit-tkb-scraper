"""
School service — backward-compatible re-exports.

Previously a monolithic module, now split into a package under app/services/school/.
All public symbols are re-exported here so existing imports continue to work.

To import directly from the sub-modules:
    from app.services.school.session import login_and_get_session
    from app.services.school.schedule import get_schedule, get_exam_schedule
    from app.services.school.announcement import get_all_announcements_full
    from app.services.school.tuition import get_tuition_fee
    from app.services.school.grades import get_grades
"""

from app.services.school.session import (  # noqa: F401
    save_session,
    is_session_alive,
    get_valid_session,
    login_and_get_session,
    SESSION_STORE,
)
from app.services.school.schedule import (  # noqa: F401
    get_schedule,
    merge_schedule,
    load_cached_schedule,
    save_schedule,
    load_cached_exam_schedule,
    save_exam_schedule,
    get_exam_schedule,
)
from app.services.school.announcement import (  # noqa: F401
    get_latest_announcement_node_id,
    get_all_announcements,
    parse_article,
    parse_content_element,
    parse_table,
    fetch_article_content,
    get_all_announcements_full,
)
from app.services.school.tuition import (  # noqa: F401
    get_tuition_fee,
    load_cached_tuition,
    save_tuition,
    load_all_cached_tuition,
)
from app.services.school.grades import (  # noqa: F401
    get_grades,
    load_cached_grade,
    save_grade,
    load_all_cached_grades,
)
from app.services.school.constants import (  # noqa: F401
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