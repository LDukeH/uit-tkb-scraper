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