from pydantic import BaseModel, Field

from app.schemas.common import CachedResponse


class Deadline(BaseModel):
    """A single deadline/event entry from Moodle."""

    id: str = Field(
        description="Unique identifier for the deadline",
        examples=["12345"],
    )
    title: str = Field(
        description="Title of the deadline/event",
        examples=["Bài tập lớn môn INT1001"],
    )
    description: str = Field(
        default="",
        description="Detailed description of the deadline",
        examples=["Nộp bài tập lớn trước 23:59 ngày 20/12/2024"],
    )
    course_code: str = Field(
        default="",
        description="Course code associated with the deadline",
        examples=["INT1001"],
    )
    start: str | None = Field(
        default=None,
        description="Start datetime in ISO format",
        examples=["2024-12-15T00:00:00"],
    )
    end: str | None = Field(
        default=None,
        description="End datetime in ISO format",
        examples=["2024-12-20T23:59:00"],
    )
    url: str = Field(
        default="",
        description="URL to the assignment/event",
        examples=["https://courses.uit.edu.vn/mod/assign/view.php?id=123"],
    )


class DeadlineResponse(CachedResponse):
    """Response containing deadlines/events from Moodle."""

    data: list[Deadline] = Field(description="List of deadline events")