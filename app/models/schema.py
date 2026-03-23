from pydantic import BaseModel
from typing import List


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

class Announcement(BaseModel):
    title: str
    content: str
    date: str
    url: str

class AnnouncementResponse(BaseModel):
    success: bool
    data: List[Announcement]

