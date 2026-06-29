# 🎓 UIT TKB Scraper API

**UIT TKB Scraper** là RESTful API cho phép sinh viên Trường Đại học Công nghệ Thông tin (UIT) truy xuất dữ liệu từ cổng thông tin sinh viên (`student.uit.edu.vn`) một cách nhanh chóng thông qua cơ chế **scraping + caching**. Dữ liệu được cache trong MongoDB, giúp giảm tải cho hệ thống UIT và cải thiện tốc độ phản hồi.

---

## ✨ Tính năng

| Tính năng                  | Mô tả                                                                      |
| -------------------------- | -------------------------------------------------------------------------- |
| 🔐 **Xác thực**            | Đăng nhập bằng tài khoản UIT, tự động refresh session khi hết hạn          |
| 📅 **Lịch học**            | Lịch học theo tuần (TKB) từ cổng sinh viên                                 |
| 📝 **Lịch thi**            | Lịch thi theo học kỳ, số lần thi                                           |
| 📢 **Thông báo**           | Danh sách thông báo từ trường (phân trang, lọc theo chủ đề)                |
| 💰 **Học phí**             | Tra cứu học phí theo học kỳ                                                |
| 📊 **Điểm**                | Kết quả học tập (bảng điểm)                                                |
| ⏰ **Deadline**            | Các hạn chót học vụ (lấy từ Moodle)                                        |
| 👤 **Hồ sơ**               | Thông tin cá nhân sinh viên                                                |
| 🏷️ **Phân loại thông báo** | Tự động gán nhãn chủ đề cho thông báo bằng Machine Learning (scikit-learn) |
| ⚡ **Caching**             | Cache MongoDB với TTL tự động hết hạn + chống cache stampede               |

---

## 🛠️ Công nghệ sử dụng

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Scraping:** [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) + `lxml`
- **Database:** [MongoDB](https://www.mongodb.com/) (Atlas / local)
- **ML Labeling:** [scikit-learn](https://scikit-learn.org/) (phân loại thông báo)
- **Calendar:** `icalendar` (xuất lịch thi)
- **Auth:** `python-jose` (JWT)
- **Deploy:** [Vercel](https://vercel.com/) (Serverless Functions + Cron Jobs)

---

## 📋 Yêu cầu

- Python **3.11+**
- MongoDB instance (MongoDB Atlas hoặc local)
- Git

---

## 🔧 Cài đặt & Cấu hình

### 1. Clone repository

```bash
git clone https://github.com/LDukeH/uit-tkb-scraper.git
cd uit-tkb-scraper
```

### 2. Tạo môi trường ảo (khuyến nghị)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 4. Cấu hình biến môi trường

Copy file `sample.env` thành `.env` và điền các giá trị:

```env
MONGO_URL= mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
SCRAPER_SECRET = <secret_key_for_internal_scraper>
SECRET_KEY = <jwt_secret_key>
ALGORITHM = HS256
CRON_SECRET = <secret_for_vercel_cron>
```

| Biến             | Bắt buộc | Mô tả                                                           |
| ---------------- | :------: | --------------------------------------------------------------- |
| `MONGO_URL`      |    ✅    | Chuỗi kết nối MongoDB                                           |
| `SCRAPER_SECRET` |    ✅    | Secret dùng cho endpoint `/internal_scraper/`                   |
| `SECRET_KEY`     |    ✅    | Key dùng để ký JWT token                                        |
| `ALGORITHM`      |    ✅    | Thuật toán JWT (mặc định: `HS256`)                              |
| `CRON_SECRET`    |    ❌    | Secret xác thực Vercel Cron Job (chỉ cần nếu deploy lên Vercel) |

---

## 🚀 Chạy ứng dụng

### Local development

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Truy cập:

- **API:** http://localhost:8000
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 📚 API Endpoints

### Health & Monitoring

| Method | Path            | Mô tả                                   | Auth |
| ------ | --------------- | --------------------------------------- | :--: |
| `GET`  | `/`             | Health check                            |  ✗   |
| `GET`  | `/timing-stats` | Thống kê thời gian hoạt động của server |  ✗   |

### Authentication

| Method | Path           | Mô tả                                            | Auth |
| ------ | -------------- | ------------------------------------------------ | :--: |
| `POST` | `/auth/login`  | Đăng nhập bằng tài khoản UIT, nhận session token |  ✗   |
| `POST` | `/auth/logout` | Đăng xuất, hủy token                             |  ✓   |

### Schedule (Lịch học & Lịch thi)

| Method | Path                                          | Mô tả                    | Auth |
| ------ | --------------------------------------------- | ------------------------ | :--: |
| `GET`  | `/schedule/`                                  | Lịch học theo tuần (TKB) |  ✓   |
| `GET`  | `/schedule/exam?lanthi=1&hocky=1&namhoc=2025` | Lịch thi theo học kỳ     |  ✓   |

### Announcements (Thông báo)

| Method | Path                              | Mô tả                                                     | Auth |
| ------ | --------------------------------- | --------------------------------------------------------- | :--: |
| `GET`  | `/announcements/?limit=15&skip=0` | Danh sách thông báo (phân trang, có thể lọc theo `topic`) |  ✗   |
| `GET`  | `/announcements/{node_id}`        | Chi tiết một thông báo                                    |  ✗   |

### Grades (Điểm)

| Method | Path       | Mô tả                       | Auth |
| ------ | ---------- | --------------------------- | :--: |
| `GET`  | `/grades/` | Kết quả học tập (bảng điểm) |  ✓   |

### Tuition (Học phí)

| Method | Path               | Mô tả                         | Auth |
| ------ | ------------------ | ----------------------------- | :--: |
| `GET`  | `/tuition/`        | Thông tin học phí theo học kỳ |  ✓   |
| `GET`  | `/tuition/summary` | Tổng quan học phí             |  ✓   |

### Deadlines

| Method | Path                       | Mô tả                                     | Auth |
| ------ | -------------------------- | ----------------------------------------- | :--: |
| `GET`  | `/deadlines/?refresh=true` | Danh sách deadline học vụ (lấy từ Moodle) |  ✓   |

### Profile (Hồ sơ)

| Method | Path        | Mô tả                       | Auth |
| ------ | ----------- | --------------------------- | :--: |
| `GET`  | `/profile/` | Thông tin cá nhân sinh viên |  ✓   |

### Internal (Nội bộ)

| Method | Path                                      | Mô tả                                          |          Auth          |
| ------ | ----------------------------------------- | ---------------------------------------------- | :--------------------: |
| `GET`  | `/internal_scraper/?key=<SCRAPER_SECRET>` | Kích hoạt scraper thông báo + labeling tự động | ✗ (yêu cầu secret key) |

---

## 🔐 Luồng xác thực

1. **Đăng nhập:** Gửi `POST /auth/login` với `username` và `password` UIT
2. **Nhận token:** API trả về `token` (UUID) dùng cho các request sau
3. **Tự động re-login:** Session có thời gian sống ~150 giây. Khi hết hạn, các endpoint có auth sẽ tự động đăng nhập lại bằng credentials đã lưu
4. **Sử dụng token:** Gửi header `Authorization: Bearer <token>` cho các endpoint yêu cầu auth

### Ví dụ đăng nhập

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "24520001", "password": "yourpassword"}'
```

Response:

```json
{
  "success": true,
  "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timings_ms": { "uit_login_ms": 850.3 }
}
```

### Ví dụ request có auth

```bash
curl http://localhost:8000/schedule/ \
  -H "Authorization: Bearer a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

---

## 💾 Kiến trúc Caching

### Cache-first strategy

```
Request → Kiểm tra MongoDB cache
         ├── Có dữ liệu → Trả về ngay (cache hit) 🚀
         └── Không có dữ liệu → Scrape từ UIT → Lưu vào DB → Trả về (cache miss)
```

### MongoDB Collections & Indexes

| Collection       |             Unique Key              | TTL | Mô tả             |
| ---------------- | :---------------------------------: | :-: | ----------------- |
| `schedules`      |              `user_id`              | ✅  | Lịch học tuần     |
| `exam_schedules` | `user_id + lanthi + hocky + namhoc` | ✅  | Lịch thi          |
| `tuition_fees`   |     `user_id + hocky + namhoc`      | ✅  | Học phí           |
| `grades`         |     `user_id + hocky + namhoc`      | ✅  | Bảng điểm         |
| `deadlines`      |      `user_id + year + month`       | ✅  | Deadline          |
| `profiles`       |              `user_id`              | ✅  | Hồ sơ             |
| `sessions`       |               `token`               | ✅  | Session đăng nhập |

### Chống Cache Stampede

Khi cache hết hạn và có nhiều request đồng thời cùng gọi đến, `StampedeGuard` (trong `app/core/cache_stampede.py`) sử dụng **thread-level locking** để đảm bảo chỉ một request thực hiện scraping, các request còn lại chờ kết quả.

---

## 🏷️ Phân loại thông báo (Topic Labeling)

Thông báo từ UIT được tự động gán nhãn chủ đề (ví dụ: "Đăng ký học phần", "Thi", "Tài chính",...) bằng **scikit-learn**.

**Cách kích hoạt:**

1. **Thủ công:** Gọi `GET /internal_scraper/?key=<SCRAPER_SECRET>`
2. **Tự động:** Vercel Cron Job chạy mỗi ngày lúc 00:00 (UTC)

**Luồng xử lý:**

```
Scrape danh sách thông báo → Lấy nội dung chi tiết từng bài →
Phân loại chủ đề bằng ML → Lưu vào MongoDB
```

---

## 📊 Theo dõi hiệu năng

Mỗi request đều được đo thời gian tự động thông qua `TimingMiddleware`.

### Response Headers

Các header `X-Timing-*` được thêm vào mỗi response:

```http
X-Timing-Total-Ms: 185.3
X-Timing-Cold-Start-Ms: 2340.1
X-Timing-Request-Received: 0.1
X-Timing-Auth-Header-Parsing: 0.05
X-Timing-Route-Handler-Service-Logic: 180.2
X-Timing-Response-Build-Serialization: 5.0
```

### Response Body Timing

Các route handler cũng trả về trường `timings_ms` chi tiết trong response body:

```json
{
  "success": true,
  "data": [...],
  "timings_ms": {
    "db_read_ms": 12.5,
    "scrape_ms": 850.3,
    "db_write_ms": 15.7,
    "total_ms": 905.1
  }
}
```

### Script đo hiệu năng

Có sẵn script để benchmark toàn bộ API:

```bash
# Bắt đầu server trước
uvicorn app.main:app --port 8000

# Chạy đo hiệu năng
python scripts/measure_performance.py --base-url http://localhost:8000 --token <your_token>
```

---

## 🚢 Triển khai lên Vercel

Dự án hỗ trợ deploy lên Vercel dưới dạng Serverless Functions.

### Cấu hình Vercel (`vercel.json`)

```json
{
  "crons": [
    {
      "path": "/api/cron-scrape",
      "schedule": "0 0 * * *"
    }
  ]
}
```

Cron job chạy mỗi ngày lúc **00:00 UTC** để tự động scrape thông báo mới.

### Cron Handler (`api/cron-scrape.py`)

Endpoint `/api/cron-scrape` được Vercel gọi định kỳ. Nó yêu cầu header `Authorization: Bearer <CRON_SECRET>` để xác thực.

### Environment Variables trên Vercel

Khi deploy lên Vercel, cần cấu hình đầy đủ các biến môi trường trong Vercel Dashboard:

- `MONGO_URL`
- `SCRAPER_SECRET`
- `SECRET_KEY`
- `ALGORITHM`
- `CRON_SECRET`

---

## 📁 Cấu trúc thư mục

```
uit-tkb-scraper/
├── api/
│   └── cron-scrape.py          # Vercel cron job handler
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── db.py               # MongoDB client & index management
│   │   ├── timing.py           # Timing collector & spans
│   │   ├── cache_stampede.py   # Cache stampede protection
│   │   └── session_store.py    # (Legacy) in-memory session store
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── timing.py           # Request timing middleware
│   ├── models/
│   │   ├── __init__.py
│   │   └── schema.py           # DB schema definitions
│   ├── routes/
│   │   ├── auth.py             # POST /auth/login, /auth/logout
│   │   ├── schedule.py         # GET /schedule/, /schedule/exam
│   │   ├── announcements.py    # GET /announcements/, /{node_id}
│   │   ├── grades.py           # GET /grades/
│   │   ├── tuition.py          # GET /tuition/, /tuition/summary
│   │   ├── deadlines.py        # GET /deadlines/
│   │   ├── profile.py          # GET /profile/
│   │   └── internal_scraper.py # GET /internal_scraper/
│   ├── schemas/
│   │   ├── auth.py             # LoginRequest, LoginResponse, LogoutResponse
│   │   ├── announcement.py     # Announcement schemas
│   │   ├── schedule.py         # Schedule response schema
│   │   ├── exam.py             # Exam schedule schema
│   │   ├── grade.py            # Grade schema
│   │   ├── tuition.py          # Tuition schema
│   │   └── deadline.py         # Deadline schema
│   └── services/
│       ├── school_service.py   # Service orchestrator (aggregates school services)
│       ├── data_insert.py      # Bulk data insertion
│       ├── analyze_service.py  # ML labeling service
│       ├── moodle_service.py   # Moodle scraping for deadlines
│       └── school/
│           ├── session.py      # UIT login & session management
│           ├── schedule.py     # Schedule scraping
│           ├── announcement.py # Announcement scraping
│           ├── tuition.py      # Tuition scraping
│           ├── grades.py       # Grades scraping
│           ├── profile.py      # Profile scraping
│           └── constants.py    # URLs & time constants
├── scripts/
│   ├── measure_performance.py  # Performance benchmark script
│   ├── test_caching.py         # Cache testing scripts
│   ├── test_caching2.py
│   └── timing_test.py
├── requirements.txt            # Python dependencies
├── sample.env                  # Environment variable template
├── vercel.json                 # Vercel deployment config
└── .gitignore
```
