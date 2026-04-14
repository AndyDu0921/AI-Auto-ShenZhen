from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InquiryCreate(BaseModel):
    source_channel: str = "form"
    sender_name: str | None = None
    sender_email: str | None = None
    company: str | None = None
    subject: str | None = None
    body: str = Field(min_length=1)


class InquiryRead(BaseModel):
    id: int
    source_channel: str
    sender_name: str | None
    sender_email: str | None
    company: str | None
    subject: str | None
    body: str
    status: str
    lead_score: int
    lead_grade: str
    suggested_action: str | None
    reply_subject: str | None
    reply_body_en: str | None
    analysis_json: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]


class DocumentRead(BaseModel):
    id: int
    file_name: str
    title: str
    file_type: str
    created_at: datetime

    class Config:
        from_attributes = True
