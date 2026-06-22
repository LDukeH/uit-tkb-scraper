from pydantic import BaseModel, Field

from app.schemas.common import StudentInfo, BankInfo


class SubjectDetail(BaseModel):
    """Detailed breakdown of a subject in tuition fee."""

    stt: int = Field(
        description="Serial number",
        examples=[1],
    )
    ma_mh: str = Field(
        description="Subject code",
        examples=["INT1001"],
    )
    so_tchp: float = Field(
        description="Number of credits",
        examples=[3.0],
    )
    hoc_lai_cai_thien: str = Field(
        default="",
        description="Retake/improvement status",
        examples=["", "Học lại"],
    )
    don_gia: int = Field(
        description="Unit price per credit",
        examples=[420000],
    )
    thanh_tien: int = Field(
        description="Total amount for this subject",
        examples=[1260000],
    )
    ghi_chu: str = Field(
        default="",
        description="Notes",
        examples=[""],
    )


class TuitionSemester(BaseModel):
    """Tuition information for a single semester."""

    hocky: int = Field(
        description="Semester number",
        examples=[1, 2],
    )
    namhoc: int = Field(
        description="Academic year",
        examples=[2024, 2025],
    )
    so_tc_dang_ky: str = Field(
        default="",
        description="Number of registered credits",
        examples=["21"],
    )
    mon_dang_ky: str = Field(
        default="",
        description="Registered subjects",
        examples=["INT1001, INT1002, ..."],
    )
    hoc_phi: str = Field(
        default="",
        description="Tuition fee amount",
        examples=["8.400.000"],
    )
    phi_khac: str = Field(
        default="",
        description="Other fees",
        examples=["200.000"],
    )
    so_tien_phai_dong: str = Field(
        default="",
        description="Total amount to pay",
        examples=["8.600.000"],
    )
    no_hoc_ky_truoc: str = Field(
        default="",
        description="Debt from previous semester",
        examples=["0"],
    )
    so_tien_da_dong: str = Field(
        default="",
        description="Amount already paid",
        examples=["8.600.000"],
    )
    con_no: str = Field(
        default="",
        description="Remaining debt",
        examples=["0"],
    )
    ngan_hang: str = Field(
        default="",
        description="Bank name for payment",
        examples=["Vietcombank"],
    )
    thoi_gian_dong: str = Field(
        default="",
        description="Payment deadline",
        examples=["15/10/2024"],
    )
    ghi_chu: str = Field(
        default="",
        description="Notes",
        examples=[""],
    )
    chi_tiet_mon: list[SubjectDetail] = Field(
        default_factory=list,
        description="Detailed breakdown by subject",
    )


class TuitionStudent(BaseModel):
    """Simplified student info in tuition response."""

    name: str = Field(
        description="Student full name",
        examples=["Lê Hoàng Duy"],
    )
    student_id: str = Field(
        description="Student ID (MSSV)",
        examples=["24520378"],
    )


class TuitionSummary(BaseModel):
    """Summary of tuition payment status."""

    total_due: int = Field(
        description="Total amount due across all semesters",
        examples=[17000000],
    )
    paid: int = Field(
        description="Total amount already paid",
        examples=[8600000],
    )
    remaining: int = Field(
        description="Remaining amount to pay",
        examples=[8400000],
    )


class TuitionSemesterSummary(BaseModel):
    """Simplified semester info for summary view."""

    namhoc: int = Field(
        description="Academic year",
        examples=[2024],
    )
    hocky: int = Field(
        description="Semester number",
        examples=[1],
    )
    sotien: int = Field(
        description="Amount due for this semester",
        examples=[8400000],
    )
    status: str = Field(
        description="Payment status",
        examples=["PAID", "UNPAID"],
    )
    deadline: str = Field(
        description="Payment deadline in YYYY-MM-DD format",
        examples=["2024-10-15"],
    )


class TuitionData(BaseModel):
    """Complete tuition data payload."""

    student_info: StudentInfo = Field(description="Student information")
    bank_info: BankInfo = Field(description="Bank account information")
    semesters: list[TuitionSemester] = Field(description="List of semesters")


class TuitionResponse(BaseModel):
    """Full tuition response with all details."""

    success: bool = Field(
        default=True,
        description="Indicates whether the request was successful",
        examples=[True],
    )
    cached: bool = Field(
        description="Whether the data was served from cache",
        examples=[True, False],
    )
    student: TuitionStudent = Field(description="Student information")
    summary: TuitionSummary = Field(description="Payment summary")
    semesters: list[TuitionSemesterSummary] = Field(description="List of semesters")


class TuitionSummaryResponse(BaseModel):
    """Lightweight summary response for home screen."""

    success: bool = Field(
        default=True,
        description="Indicates whether the request was successful",
        examples=[True],
    )
    cached: bool = Field(
        description="Whether the data was served from cache",
        examples=[True, False],
    )
    remaining: int = Field(
        description="Remaining amount to pay",
        examples=[8400000],
    )
    latest_semester: str = Field(
        description="Latest semester in format 'HK{X} {YYYY}'",
        examples=["HK1 2024-2025"],
    )
    status: str = Field(
        description="Payment status of latest semester",
        examples=["PAID", "UNPAID"],
    )