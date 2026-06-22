from pydantic import BaseModel, Field

from app.schemas.common import StudentProfile


class GradeSubject(BaseModel):
    """A single subject grade entry."""

    stt: int = Field(
        description="Serial number",
        examples=[1],
    )
    ma_hp: str = Field(
        description="Course code",
        examples=["INT1001"],
    )
    ten_hoc_phan: str = Field(
        description="Course name",
        examples=["Nhập môn lập trình"],
    )
    tin_chi: int = Field(
        description="Number of credits",
        examples=[3],
    )
    diem_qt: float | None = Field(
        default=None,
        description="Quizz score",
        examples=[8.5],
    )
    diem_gk: float | None = Field(
        default=None,
        description="Midterm score",
        examples=[7.5],
    )
    diem_th: float | None = Field(
        default=None,
        description="Practice score",
        examples=[8.0],
    )
    diem_ck: float | None = Field(
        default=None,
        description="Final exam score",
        examples=[8.5],
    )
    diem_hp: str | None = Field(
        default=None,
        description="Final course score (can be 'Miễn' for exemption)",
        examples=["8.5", "Miễn"],
    )
    ghi_chu: str = Field(
        default="",
        description="Notes",
        examples=[""],
    )
    trong_so: dict | None = Field(
        default=None,
        description="Weight distribution for score components",
        examples=[{"qt": 10, "gk": 20, "th": 20, "ck": 50}],
    )


class GradeSemester(BaseModel):
    """Grades for a single semester."""

    hocky: int = Field(
        description="Semester number",
        examples=[1, 2],
    )
    namhoc: int = Field(
        description="Academic year",
        examples=[2024, 2025],
    )
    so_tin_chi: float | None = Field(
        default=None,
        description="Number of credits for this semester",
        examples=[21.0],
    )
    diem_trung_binh: str | None = Field(
        default=None,
        description="Average score for this semester",
        examples=["8.5"],
    )
    subjects: list[GradeSubject] = Field(
        default_factory=list,
        description="List of subjects with grades",
    )


class GradeSummary(BaseModel):
    """Overall academic summary."""

    so_tin_chi_da_hoc: float | None = Field(
        default=None,
        description="Total credits studied",
        examples=[120.0],
    )
    so_tin_chi_tich_luy: float | None = Field(
        default=None,
        description="Total accumulated credits",
        examples=[115.0],
    )
    diem_trung_binh_chung: float | None = Field(
        default=None,
        description="Overall average score",
        examples=[8.2],
    )
    diem_trung_binh_chung_tich_luy: float | None = Field(
        default=None,
        description="Cumulative average score",
        examples=[8.5],
    )


class GradeData(BaseModel):
    """Complete grades data payload."""

    student_profile: StudentProfile = Field(description="Student profile information")
    semesters: list[GradeSemester] = Field(description="List of semesters with grades")
    summary: GradeSummary | None = Field(
        default=None,
        description="Academic summary",
    )


class GradeResponse(BaseModel):
    """Full grades response."""

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
        description="Number of semesters returned",
        examples=[2],
    )
    data: GradeData | None = Field(
        default=None,
        description="Grades data payload",
    )
    timings_ms: dict | None = Field(
        default=None,
        description="Performance timing information",
        examples=[{"scrape": 123.4, "db_read": 5.2, "db_write": 12.3}],
    )