from typing import List, Optional
from pydantic import BaseModel

class AssistantChatContext(BaseModel):
    selectedGroupId: Optional[int] = None
    selectedDate: Optional[str] = None

class CachedScheduleLesson(BaseModel):
    name: str
    type: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    date: Optional[str] = None
    room: Optional[str] = None
    teacher: Optional[str] = None
    roomId: Optional[int] = None
    teacherId: Optional[int] = None
    classUrl: Optional[str] = None
    note: Optional[str] = None
    isExam: Optional[bool] = None

class CachedSchedulePayload(BaseModel):
    generatedAt: str
    source: Optional[str] = None
    lessons: List[CachedScheduleLesson] = []

class AssistantChatRequest(BaseModel):
    message: str
    persona: str
    context: Optional[AssistantChatContext] = None
    conversationId: Optional[str] = None
    groupId: Optional[int] = None
    targetDate: Optional[str] = None
    cachedSchedule: Optional[CachedSchedulePayload] = None

class AssistantChatResponse(BaseModel):
    reply: str
    remaining: int
    plan: str
