from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class HomeworkOptionResponse(BaseModel):
    subjectName: str
    teacherId: Optional[int] = None
    teacherName: Optional[str] = None
    lessonType: Optional[str] = None

class HomeworkCreateRequest(BaseModel):
    lesson_date: str
    lesson_time: Optional[str] = None
    subject: str
    teacher: Optional[str] = None
    room: Optional[str] = None
    text: str

class HomeworkUpdateRequest(BaseModel):
    lesson_date: Optional[str] = None
    lesson_time: Optional[str] = None
    subject: Optional[str] = None
    teacher: Optional[str] = None
    room: Optional[str] = None
    text: Optional[str] = None

class HomeworkResponse(BaseModel):
    id: int
    group_id: int
    lesson_date: str
    lesson_time: Optional[str] = None
    subject: str
    teacher: Optional[str] = None
    room: Optional[str] = None
    text: str
    created_by: int
    created_at: datetime
    updated_at: datetime
