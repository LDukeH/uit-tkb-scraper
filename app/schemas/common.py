from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional, Dict, Any

T = TypeVar("T")


class SuccessResponse(BaseModel):
    """Base success response wrapper used across most endpoints."""

    success: bool = Field(
        default=True,
        description="Indicates whether the request was successful",
        examples=[True],
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response with metadata."""

    success: bool = Field(
        default=True,
        description="Indicates whether the request was successful",
        examples=[True],
    )
    count: int = Field(
        description="Number of items returned in this response",
        examples=[15],
    )
    data: List[T] = Field(description="List of response items")


class CachedResponse(BaseModel, Generic[T]):
    """Response that includes cache status information."""

    success: bool = Field(
        default=True,
        description="Indicates whether the request was successful",
        examples=[True],
    )
    cached: bool = Field(
        description="Whether the data was served from cache",
        examples=[True, False],
    )
    count: int = Field(
        description="Number of items returned",
        examples=[10],
    )
    data: T = Field(description="Response data payload")


class TimingInfo(BaseModel):
    """Timing information for performance monitoring."""

    scrape: Optional[float] = Field(
        default=None,
        description="Time spent scraping in milliseconds",
        examples=[123.4],
    )
    db_read: Optional[float] = Field(
        default=None,
        description="Time spent reading from database in milliseconds",
        examples=[5.2],
    )
    db_write: Optional[float] = Field(
        default=None,
        description="Time spent writing to database in milliseconds",
        examples=[12.3],
    )


class RelatedArticle(BaseModel):
    """Related article link in announcement details."""

    title: str = Field(
        description="Title of the related article",
        examples=["Hướng dẫn đăng ký học phần"],
    )
    link: str = Field(
        description="URL of the related article",
        examples=["https://student.uit.edu.vn/article/123"],
    )


class StudentInfo(BaseModel):
    """Basic student information from tuition/schedule endpoints."""

    ho_ten: str = Field(
        description="Student full name",
        examples=["Lê Hoàng Duy"],
    )
    mssv: str = Field(
        description="Student ID (MSSV)",
        examples=["24520378"],
    )
    ngay_sinh: str = Field(
        description="Date of birth",
        examples=["01/01/2003"],
    )
    khoa: str = Field(
        description="Faculty/Department",
        examples=["Công nghệ thông tin"],
    )
    he_dao_tao: str = Field(
        description="Training system",
        examples=["Chính quy"],
    )


class StudentProfile(BaseModel):
    """Detailed student profile from grades endpoint."""

    ho_ten: str = Field(
        description="Student full name",
        examples=["Lê Hoàng Duy"],
    )
    mssv: str = Field(
        description="Student ID (MSSV)",
        examples=["24520378"],
    )
    ngay_sinh: str = Field(
        description="Date of birth",
        examples=["01/01/2003"],
    )
    gioi_tinh: str = Field(
        description="Gender",
        examples=["Nam", "Nữ"],
    )
    lop_sinh_hoat: str = Field(
        description="Class name",
        examples=["CNTT1-K65"],
    )
    khoa: str = Field(
        description="Faculty/Department",
        examples=["Công nghệ thông tin"],
    )
    bac_dao_tao: str = Field(
        description="Training level",
        examples=["Đại học"],
    )
    he_dao_tao: str = Field(
        description="Training system",
        examples=["Chính quy"],
    )
    nganh: str = Field(
        description="Major",
        examples=["Khoa học máy tính"],
    )


class BankInfo(BaseModel):
    """Bank account information for tuition payment."""

    ten_tai_khoan: str = Field(
        description="Account holder name",
        examples=["LÊ HOÀNG DUY"],
    )
    so_tai_khoan: str = Field(
        description="Account number",
        examples=["1234567890"],
    )
    ngan_hang: str = Field(
        description="Bank name",
        examples=["Vietcombank"],
    )
    noi_dung_chuyen_khoan: str = Field(
        description="Transfer content/description",
        examples=["Hoc phi HK1 2024-2025"],
    )