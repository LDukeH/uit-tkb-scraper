from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: str


class Subject(BaseModel):
    day: str
    period: str
    time: str
    start_time: str
    end_time: str
    code: str
    name: str
    room: str
    teacher: str
    date: str


class ScheduleResponse(BaseModel):
    success: bool
    count: int
    data: List[Subject]


class RelatedArticle(BaseModel):
    title: str
    link: str


class AnnouncementDetails(BaseModel):
    content: str
    related: List[RelatedArticle] = []


class Announcement(BaseModel):
    node_id: str
    title: str
    preview: str
    date: str
    link: str
    source: str = "student.uit.edu.vn"
    details: Optional[AnnouncementDetails] = None


class AnnouncementResponse(BaseModel):
    success: bool
    count: int
    data: List[Announcement]


class SubjectDetail(BaseModel):
    stt: int
    ma_mh: str
    so_tchp: float
    hoc_lai_cai_thien: str = ""
    don_gia: int
    thanh_tien: int
    ghi_chu: str = ""


class TuitionSemester(BaseModel):
    hocky: int
    namhoc: int
    so_tc_dang_ky: str = ""
    mon_dang_ky: str = ""
    hoc_phi: str = ""
    phi_khac: str = ""
    so_tien_phai_dong: str = ""
    no_hoc_ky_truoc: str = ""
    so_tien_da_dong: str = ""
    con_no: str = ""
    ngan_hang: str = ""
    thoi_gian_dong: str = ""
    ghi_chu: str = ""
    chi_tiet_mon: List[SubjectDetail] = []


class StudentInfo(BaseModel):
    ho_ten: str
    mssv: str
    ngay_sinh: str
    khoa: str
    he_dao_tao: str


class BankInfo(BaseModel):
    ten_tai_khoan: str
    so_tai_khoan: str
    ngan_hang: str
    noi_dung_chuyen_khoan: str


class TuitionData(BaseModel):
    student_info: StudentInfo
    bank_info: BankInfo
    semesters: List[TuitionSemester]


class TuitionResponse(BaseModel):
    success: bool
    cached: bool
    count: int
    data: Optional[TuitionData] = None
    timings_ms: Optional[dict] = None
