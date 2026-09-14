from datetime import datetime
import re

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator
from typing import Literal

class ProjectTitle(BaseModel):
    """The first small validation exercise from Phase 0."""

    title: str = Field(min_length=3, max_length=120)

class ProjectCreate(BaseModel):  #ProjectCreate is i/p from client
    title: str = Field(min_length=3, max_length=120)
    summary: str = Field(min_length=10, max_length=1000)
    field: str = Field(min_length=2, max_length=80)
    tags: list[str] = Field(default_factory=list)
    visibility: Literal["private", "public"] = "private"

class Project(BaseModel): #Project is o/p from server
    id: int
    title: str
    summary: str
    field: str
    tags: list[str] = Field(default_factory=list)
    visibility: Literal["private", "public"] = "private"

class ProjectUpdate(BaseModel):
   title: str = Field(min_length=3, max_length=120)
   summary: str  = Field(min_length=10, max_length=1000)
   field: str  = Field(min_length=2, max_length=80)
   tags: list[str] = Field(default_factory=list)
   visibility: Literal["private", "public"] = "private"


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class User(BaseModel):
    id: int
    name: str
    email: EmailStr

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class PasswordResetRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class PasswordResetRequestResult(BaseModel):
    message: str
    development_reset_url: str | None = None


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class AccountRecoveryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    contact_email: EmailStr
    remembered_email: EmailStr | None = None
    details: str = Field(min_length=20, max_length=2_000)

    @field_validator("contact_email", "remembered_email")
    @classmethod
    def normalize_recovery_email(cls, value: EmailStr | None) -> str | None:
        return str(value).strip().lower() if value is not None else None


class AccountRecoveryResult(BaseModel):
    reference_code: str
    status: Literal["pending", "in_review", "resolved", "rejected"]
    message: str


class AccountRecoveryStatus(BaseModel):
    reference_code: str
    status: Literal["pending", "in_review", "resolved", "rejected"]
    updated_at: datetime


class ProjectMemberCreate(BaseModel):
    email: EmailStr
    role: Literal["owner", "editor", "viewer"]


class ProjectMember(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: Literal["owner", "editor", "viewer"]


class ProjectMemberUpdate(BaseModel):
    role: Literal["owner", "editor", "viewer"]


class NoteCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=1, max_length=10_000)


class NoteUpdate(NoteCreate):
    pass


class Note(BaseModel):
    id: int
    project_id: int
    author_id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class NoteVersion(BaseModel):
    id: int
    note_id: int
    project_id: int
    edited_by_id: int | None
    editor_name: str | None
    version: int
    title: str
    content: str
    created_at: datetime


TaskStatus = Literal["backlog", "in_progress", "in_review", "done"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=5_000)
    status: TaskStatus = "backlog"
    assignee_id: int | None = None


class TaskUpdate(TaskCreate):
    pass


class Task(BaseModel):
    id: int
    project_id: int
    creator_id: int
    assignee_id: int | None
    title: str
    description: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4_000)

    @field_validator("content")
    @classmethod
    def content_cannot_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Message content cannot be blank.")
        return cleaned_value


class Message(BaseModel):
    id: int
    project_id: int
    author_id: int
    author_name: str
    content: str
    created_at: datetime


SourceType = Literal["article", "book", "dataset", "report", "website", "other"]

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


def normalize_doi(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
            break

    if not normalized:
        return None
    if len(normalized) > 255 or DOI_PATTERN.fullmatch(normalized) is None:
        raise ValueError("Enter a valid DOI, such as 10.1000/example.")
    return normalized


class SourceCreate(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    authors: str = Field(default="", max_length=1_000)
    publication_year: int | None = Field(default=None, ge=1, le=2100)
    source_type: SourceType
    url: HttpUrl | None = None
    doi: str | None = None

    @field_validator("doi", mode="before")
    @classmethod
    def validate_doi(cls, value: object) -> str | None:
        if value is None or isinstance(value, str):
            return normalize_doi(value)
        raise ValueError("DOI must be text.")


class SourceUpdate(SourceCreate):
    pass


class Source(BaseModel):
    id: int
    project_id: int
    creator_id: int
    title: str
    authors: str
    publication_year: int | None
    source_type: SourceType
    url: str | None
    doi: str | None
    created_at: datetime
    updated_at: datetime


class Attachment(BaseModel):
    id: int
    project_id: int
    source_id: int | None
    uploaded_by_id: int
    original_filename: str
    content_type: str | None
    size_bytes: int
    created_at: datetime
    download_url: str
