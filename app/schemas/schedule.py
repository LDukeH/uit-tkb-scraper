from pydantic import BaseModel, Field

from app.schemas.common import CachedResponse


class Subject(BaseModel):
    """A single class schedule entry."""

    day: str = Field(
        description="Day of the week in Vietnamese",
        examples=["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"],
    )
    period: str = Field(
        description="Period(s) in format 'Tiết X' or 'Tiết X-Y'",
        examples=["Tiết 1", "Tiết 3-4", "Tiết 1, 3, 5"],
    )
    time: str = Field(
        description="Time range for the class",
        examples=["07:00-08:45"],
    )
    start_time: str = Field(
        description="Start time of the class",
        examples=["07:00"],
    )
    end_time: str = Field(
        description="End time of the class",
        examples=["08:45"],
    )
    code: str = Field(
        description="Course code",
        examples=["INT1001"],
    )
    name: str = Field(
        description="Course name",
        examples=["Nhập môn lập trình"],
    )
    room: str = Field(
        description="Classroom location",
        examples=["Phòng A1.201"],
    )
    teacher: str = Field(
        description="Instructor name",
        examples=["TS. Nguyễn Văn A"],
    )
    date: str = Field(
        description="Date range for the class",
        examples=["05/09/2024 -> 20/12/2024"],
    )


class ScheduleResponse(CachedResponse):
    """Response containing the weekly class schedule."""

    data: list[Subject] = Field(description="List of scheduled classes")