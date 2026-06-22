from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse, RelatedArticle


class AnnouncementDetails(BaseModel):
    """Detailed content of an announcement."""

    content: str = Field(
        description="Full content of the announcement in markdown/text format",
        examples=["Nội dung chi tiết của thông báo..."],
    )
    related: list[RelatedArticle] = Field(
        default_factory=list,
        description="List of related articles",
    )


class Announcement(BaseModel):
    """Summary of an announcement."""

    node_id: str = Field(
        description="Unique node ID of the announcement",
        examples=["12345"],
    )
    title: str = Field(
        description="Title of the announcement",
        examples=["Thông báo về việc đăng ký học phần HK1 2024-2025"],
    )
    preview: str = Field(
        description="Short preview/summary of the announcement content",
        examples=["Nội dung tóm tắt của thông báo..."],
    )
    date: str = Field(
        description="Publication date in ISO format",
        examples=["2024-09-01T00:00:00"],
    )
    link: str = Field(
        description="URL to the full announcement",
        examples=["https://student.uit.edu.vn/article/12345"],
    )
    source: str = Field(
        default="student.uit.edu.vn",
        description="Source website of the announcement",
        examples=["student.uit.edu.vn"],
    )
    details: AnnouncementDetails | None = Field(
        default=None,
        description="Full details including content and related articles",
    )


class AnnouncementListResponse(PaginatedResponse):
    """Response containing a paginated list of announcements."""

    data: list[Announcement] = Field(description="List of announcements")


class AnnouncementDetailResponse(BaseModel):
    """Response containing a single announcement with full details."""

    success: bool = Field(
        default=True,
        description="Indicates whether the request was successful",
        examples=[True],
    )
    data: Announcement = Field(description="Full announcement details")