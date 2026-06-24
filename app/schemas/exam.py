from pydantic import BaseModel, Field

from app.schemas.common import CachedResponse


class ExamScheduleItem(BaseModel):
    """A single exam schedule entry."""

    stt: int = Field(
        description="Serial number",
        examples=[1],
    )
    course_code: str = Field(
        description="Course code",
        examples=["INT1001"],
    )
    class_code: str = Field(
        description="Class code",
        examples=["CNTT1"],
    )
    exam_date: str = Field(
        description="Exam date in YYYY-MM-DD format",
        examples=["2024-12-20"],
    )
    exam_shift: str = Field(
        description="Exam shift/period",
        examples=["Ca 1", "Ca 2"],
    )
    start_time: str = Field(
        description="Exam start time derived from shift",
        examples=["07:30"],
    )
    weekday: str = Field(
        description="Day of the week in Vietnamese",
        examples=["Thứ Sáu"],
    )
    room: str = Field(
        description="Exam room location",
        examples=["Phòng A1.201"],
    )


class ExamScheduleResponse(CachedResponse):
    """Response containing the exam schedule."""

    data: list[ExamScheduleItem] = Field(description="List of exam schedule entries")
