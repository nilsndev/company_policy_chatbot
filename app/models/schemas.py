from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Department = Literal[
    "Clinical",
    "IT & Security",
    "HR",
    "Compliance & Risk",
    "Finance",
    "Facilities & Operations",
]
Role = Literal["staff", "manager", "director", "compliance_officer"]


class ProfileIn(BaseModel):
    department: Department
    role: Role


class ProfileOut(BaseModel):
    id: str
    department: Department | None
    role: Role | None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class ConversationOut(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class CitationOut(BaseModel):
    index: int
    policy_id: str
    title: str
    version: int
    section: str | None


class MessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    citations: list[CitationOut] = Field(default_factory=list)


class PolicyOut(BaseModel):
    id: str
    slug: str
    title: str
    department: Department | None
    version: int
    status: Literal["queued", "processing", "ready", "failed"]
