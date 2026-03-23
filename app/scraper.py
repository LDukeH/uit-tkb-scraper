from app.services.school_service import get_all_announcements
from app.services.data_insert import insert_announcements

def main():
    data = get_all_announcements()
    insert_announcements(data)

if __name__ == "__main__":
    main()