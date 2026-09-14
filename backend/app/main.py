from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from .schemas import (
    Project,
    ProjectCreate,
    ProjectMember,
    ProjectMemberCreate,
    ProjectMemberUpdate,
    ProjectTitle,
    ProjectUpdate,
    Note,
    NoteCreate,
    NoteUpdate,
    NoteVersion,
    Message,
    MessageCreate,
    Source,
    SourceCreate,
    SourceType,
    SourceUpdate,
    Attachment,
    Task,
    TaskCreate,
    TaskStatus,
    TaskUpdate,
    Token,
    User,
    UserCreate,
    UserLogin,
    AccountRecoveryCreate,
    AccountRecoveryResult,
    AccountRecoveryStatus,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequestResult,
)
from typing import Literal
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError

from .config import (
    JWT_SECRET_KEY,
    PASSWORD_RESET_DELIVERY_MODE,
    PASSWORD_RESET_EXPIRE_MINUTES,
    PASSWORD_RESET_MAX_REQUESTS_PER_HOUR,
)
from .database import SessionLocal
from .models import AccountRecoveryRequestRecord, AttachmentRecord, MessageRecord, NoteRecord, NoteVersionRecord, PasswordResetAttemptRecord, PasswordResetTokenRecord, ProjectMemberRecord, ProjectRecord, SourceRecord, TaskRecord, UserRecord
from fastapi.middleware.cors import CORSMiddleware
from .security import create_access_token, get_access_token_identity, hash_password, verify_password
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .storage import attachment_file_path, delete_upload, save_upload

app = FastAPI(title="ResearchHub API", version="0.1.0")
bearer_scheme = HTTPBearer()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def validate_project_title(title: str) -> str:
    cleaned_title = title.strip()
    if len(cleaned_title) < 3:
        raise ValueError("A project title needs at least 3 characters.")
    return cleaned_title
    
def project_to_response(record: ProjectRecord) -> Project:
    return Project(
        id=record.id,
        title=record.title,
        summary=record.summary,
        field=record.field,
        tags=record.tags,
        visibility=record.visibility,
    )


def user_to_response(record: UserRecord) -> User:
    return User(id=record.id, name=record.name, email=record.email)


def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UserRecord:
    user_id, token_version = get_access_token_identity(credentials.credentials)

    with SessionLocal() as session:
        record = session.get(UserRecord, user_id)

        if record is None:
            raise HTTPException(status_code=401, detail="User no longer exists.")
        if record.token_version != token_version:
            raise HTTPException(status_code=401, detail="This session is no longer valid.")

        session.expunge(record)
        return record


def get_project_membership(
    session: SessionLocal,
    project_id: int,
    user_id: int,
) -> ProjectMemberRecord:
    membership = session.scalar(
        select(ProjectMemberRecord).where(
            ProjectMemberRecord.project_id == project_id,
            ProjectMemberRecord.user_id == user_id,
        )
    )

    if membership is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return membership


def project_member_to_response(
    membership: ProjectMemberRecord,
    user: UserRecord,
) -> ProjectMember:
    return ProjectMember(
        id=user.id,
        name=user.name,
        email=user.email,
        role=membership.role,
    )


def note_to_response(record: NoteRecord) -> Note:
    return Note(
        id=record.id,
        project_id=record.project_id,
        author_id=record.author_id,
        title=record.title,
        content=record.content,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def note_version_to_response(
    record: NoteVersionRecord,
    editor: UserRecord | None,
) -> NoteVersion:
    return NoteVersion(
        id=record.id,
        note_id=record.note_id,
        project_id=record.project_id,
        edited_by_id=record.edited_by_id,
        editor_name=editor.name if editor is not None else None,
        version=record.version,
        title=record.title,
        content=record.content,
        created_at=record.created_at,
    )


def create_note_version(
    session: SessionLocal,
    record: NoteRecord,
    editor_id: int,
) -> NoteVersionRecord:
    latest_version = session.scalar(
        select(func.max(NoteVersionRecord.version)).where(
            NoteVersionRecord.note_id == record.id
        )
    )
    version = NoteVersionRecord(
        note_id=record.id,
        project_id=record.project_id,
        edited_by_id=editor_id,
        version=(latest_version or 0) + 1,
        title=record.title,
        content=record.content,
    )
    session.add(version)
    return version


def task_to_response(record: TaskRecord) -> Task:
    return Task(
        id=record.id,
        project_id=record.project_id,
        creator_id=record.creator_id,
        assignee_id=record.assignee_id,
        title=record.title,
        description=record.description,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def message_to_response(record: MessageRecord, author: UserRecord) -> Message:
    return Message(
        id=record.id,
        project_id=record.project_id,
        author_id=record.author_id,
        author_name=author.name,
        content=record.content,
        created_at=record.created_at,
    )


def source_to_response(record: SourceRecord) -> Source:
    return Source(
        id=record.id,
        project_id=record.project_id,
        creator_id=record.creator_id,
        title=record.title,
        authors=record.authors,
        publication_year=record.publication_year,
        source_type=record.source_type,
        url=record.url,
        doi=record.doi,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def attachment_to_response(record: AttachmentRecord) -> Attachment:
    return Attachment(
        id=record.id,
        project_id=record.project_id,
        source_id=record.source_id,
        uploaded_by_id=record.uploaded_by_id,
        original_filename=record.original_filename,
        content_type=record.content_type,
        size_bytes=record.size_bytes,
        created_at=record.created_at,
        download_url=(
            f"/projects/{record.project_id}/attachments/{record.id}/download"
        ),
    )


def require_project_editor(
    session: SessionLocal,
    project_id: int,
    user_id: int,
) -> ProjectMemberRecord:
    membership = get_project_membership(session, project_id, user_id)
    if membership.role not in {"owner", "editor"}:
        raise HTTPException(status_code=403, detail="Project edit permission required")
    return membership


def get_project_note(session: SessionLocal, project_id: int, note_id: int) -> NoteRecord:
    record = session.get(NoteRecord, note_id)
    if record is None or record.project_id != project_id:
        raise HTTPException(status_code=404, detail="Note not found")
    return record


def get_note_version(
    session: SessionLocal,
    project_id: int,
    note_id: int,
    version_id: int,
) -> NoteVersionRecord:
    record = session.get(NoteVersionRecord, version_id)
    if (
        record is None
        or record.project_id != project_id
        or record.note_id != note_id
    ):
        raise HTTPException(status_code=404, detail="Note version not found")
    return record


def get_project_task(session: SessionLocal, project_id: int, task_id: int) -> TaskRecord:
    record = session.get(TaskRecord, task_id)
    if record is None or record.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return record


def validate_task_assignee(
    session: SessionLocal,
    project_id: int,
    assignee_id: int | None,
) -> None:
    if assignee_id is None:
        return

    assignee = session.get(UserRecord, assignee_id)
    membership = session.scalar(
        select(ProjectMemberRecord).where(
            ProjectMemberRecord.project_id == project_id,
            ProjectMemberRecord.user_id == assignee_id,
        )
    )
    if assignee is None or membership is None:
        raise HTTPException(status_code=422, detail="Task assignee must be a project member")

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "researchhub-api"}

## response_model = project tells FastAPI that this route must return data matching Porject schema
@app.post("/projects", status_code = 201, response_model = Project) 
async def create_project(
    payload: ProjectCreate,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Project:
    record = ProjectRecord(
        title=payload.title,
        summary=payload.summary,
        field=payload.field,
        tags=payload.tags,
        visibility=payload.visibility,
    )

    with SessionLocal() as session:
        session.add(record)
        session.flush()
        session.add(
            ProjectMemberRecord(
                project_id=record.id,
                user_id=current_user.id,
                role="owner",
            )
        )
        session.commit()
        session.refresh(record)
        return project_to_response(record)


@app.get("/projects", response_model=list[Project])
async def list_projects(
    visibility: Literal["private", "public"] | None = None,
    tag: str | None = None,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> list[Project]:
    statement = (
        select(ProjectRecord)
        .join(ProjectMemberRecord)
        .where(ProjectMemberRecord.user_id == current_user.id)
    )

    if visibility is not None:
        statement = statement.where(ProjectRecord.visibility == visibility)

    with SessionLocal() as session:
        records = session.scalars(statement).all()

    if tag is not None:
        records = [record for record in records if tag in record.tags]

    return [project_to_response(record) for record in records]

@app.post("/learning/validate-project-title")
async def validate_title(payload: ProjectTitle) -> dict[str, str]:
    try:
        return {"title": validate_project_title(payload.title)}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@app.get("/projects/{project_id}", response_model=Project)
async def get_project(
    project_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Project:
    with SessionLocal() as session:
        record = session.get(ProjectRecord, project_id)

        if record is None:
            raise HTTPException(status_code=404, detail="Project not found")

        get_project_membership(session, project_id, current_user.id)
        return project_to_response(record)

@app.put("/projects/{project_id}", response_model=Project)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Project:
    with SessionLocal() as session:
        record = session.get(ProjectRecord, project_id)

        if record is None:
            raise HTTPException(status_code=404, detail="Project not found")

        membership = get_project_membership(session, project_id, current_user.id)
        if membership.role not in {"owner", "editor"}:
            raise HTTPException(status_code=403, detail="Project edit permission required")

        record.title = payload.title
        record.summary = payload.summary
        record.field = payload.field
        record.tags = payload.tags
        record.visibility = payload.visibility
        session.commit()
        session.refresh(record)
        return project_to_response(record)

@app.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> None:
    with SessionLocal() as session:
        record = session.get(ProjectRecord, project_id)

        if record is None:
            raise HTTPException(status_code=404, detail="Project not found")

        membership = get_project_membership(session, project_id, current_user.id)
        if membership.role != "owner":
            raise HTTPException(status_code=403, detail="Project owner permission required")

        session.delete(record)
        session.commit()


@app.post("/projects/{project_id}/members", status_code=201, response_model=ProjectMember)
async def add_project_member(
    project_id: int,
    payload: ProjectMemberCreate,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> ProjectMember:
    with SessionLocal() as session:
        project = session.get(ProjectRecord, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        current_membership = get_project_membership(session, project_id, current_user.id)
        if current_membership.role != "owner":
            raise HTTPException(status_code=403, detail="Project owner permission required")

        user = session.scalar(
            select(UserRecord).where(UserRecord.email == str(payload.email))
        )
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        existing_membership = session.scalar(
            select(ProjectMemberRecord).where(
                ProjectMemberRecord.project_id == project_id,
                ProjectMemberRecord.user_id == user.id,
            )
        )
        if existing_membership is not None:
            raise HTTPException(status_code=409, detail="User is already a project member")

        membership = ProjectMemberRecord(
            project_id=project_id,
            user_id=user.id,
            role=payload.role,
        )
        session.add(membership)
        session.commit()
        session.refresh(membership)
        return project_member_to_response(membership, user)


@app.get("/projects/{project_id}/members", response_model=list[ProjectMember])
async def list_project_members(
    project_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> list[ProjectMember]:
    with SessionLocal() as session:
        project = session.get(ProjectRecord, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        get_project_membership(session, project_id, current_user.id)
        rows = session.execute(
            select(ProjectMemberRecord, UserRecord)
            .join(UserRecord, ProjectMemberRecord.user_id == UserRecord.id)
            .where(ProjectMemberRecord.project_id == project_id)
        ).all()

        return [
            project_member_to_response(membership, user)
            for membership, user in rows
        ]


@app.put("/projects/{project_id}/members/{user_id}", response_model=ProjectMember)
async def update_project_member(
    project_id: int,
    user_id: int,
    payload: ProjectMemberUpdate,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> ProjectMember:
    with SessionLocal() as session:
        project = session.get(ProjectRecord, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        current_membership = get_project_membership(session, project_id, current_user.id)
        if current_membership.role != "owner":
            raise HTTPException(status_code=403, detail="Project owner permission required")

        membership = get_project_membership(session, project_id, user_id)
        user = session.get(UserRecord, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        if membership.role == "owner" and payload.role != "owner":
            owner_count = session.scalar(
                select(func.count())
                .select_from(ProjectMemberRecord)
                .where(
                    ProjectMemberRecord.project_id == project_id,
                    ProjectMemberRecord.role == "owner",
                )
            )
            if owner_count <= 1:
                raise HTTPException(status_code=409, detail="A project needs at least one owner")

        membership.role = payload.role
        session.commit()
        session.refresh(membership)
        return project_member_to_response(membership, user)


@app.delete("/projects/{project_id}/members/{user_id}", status_code=204)
async def remove_project_member(
    project_id: int,
    user_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> None:
    with SessionLocal() as session:
        project = session.get(ProjectRecord, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        current_membership = get_project_membership(session, project_id, current_user.id)
        if current_membership.role != "owner":
            raise HTTPException(status_code=403, detail="Project owner permission required")

        membership = get_project_membership(session, project_id, user_id)
        if membership.role == "owner":
            owner_count = session.scalar(
                select(func.count())
                .select_from(ProjectMemberRecord)
                .where(
                    ProjectMemberRecord.project_id == project_id,
                    ProjectMemberRecord.role == "owner",
                )
            )
            if owner_count <= 1:
                raise HTTPException(status_code=409, detail="A project needs at least one owner")

        session.delete(membership)
        session.commit()


@app.post("/projects/{project_id}/notes", status_code=201, response_model=Note)
async def create_note(
    project_id: int,
    payload: NoteCreate,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Note:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        require_project_editor(session, project_id, current_user.id)
        record = NoteRecord(
            project_id=project_id,
            author_id=current_user.id,
            title=payload.title,
            content=payload.content,
        )
        session.add(record)
        session.flush()
        create_note_version(session, record, current_user.id)
        session.commit()
        session.refresh(record)
        return note_to_response(record)


@app.get("/projects/{project_id}/notes", response_model=list[Note])
async def list_notes(
    project_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> list[Note]:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        get_project_membership(session, project_id, current_user.id)
        records = session.scalars(
            select(NoteRecord)
            .where(NoteRecord.project_id == project_id)
            .order_by(NoteRecord.updated_at.desc())
        ).all()
        return [note_to_response(record) for record in records]


@app.put("/projects/{project_id}/notes/{note_id}", response_model=Note)
async def update_note(
    project_id: int,
    note_id: int,
    payload: NoteUpdate,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Note:
    with SessionLocal() as session:
        record = get_project_note(session, project_id, note_id)
        membership = get_project_membership(session, project_id, current_user.id)
        if membership.role not in {"owner", "editor"} and record.author_id != current_user.id:
            raise HTTPException(status_code=403, detail="Note edit permission required")

        record.title = payload.title
        record.content = payload.content
        create_note_version(session, record, current_user.id)
        session.commit()
        session.refresh(record)
        return note_to_response(record)


@app.get(
    "/projects/{project_id}/notes/{note_id}/versions",
    response_model=list[NoteVersion],
)
async def list_note_versions(
    project_id: int,
    note_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> list[NoteVersion]:
    with SessionLocal() as session:
        get_project_note(session, project_id, note_id)
        get_project_membership(session, project_id, current_user.id)
        rows = session.execute(
            select(NoteVersionRecord, UserRecord)
            .outerjoin(UserRecord, NoteVersionRecord.edited_by_id == UserRecord.id)
            .where(
                NoteVersionRecord.project_id == project_id,
                NoteVersionRecord.note_id == note_id,
            )
            .order_by(NoteVersionRecord.version.desc())
        ).all()
        return [
            note_version_to_response(record, editor)
            for record, editor in rows
        ]


@app.post(
    "/projects/{project_id}/notes/{note_id}/versions/{version_id}/restore",
    response_model=Note,
)
async def restore_note_version(
    project_id: int,
    note_id: int,
    version_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Note:
    with SessionLocal() as session:
        record = get_project_note(session, project_id, note_id)
        membership = get_project_membership(session, project_id, current_user.id)
        if membership.role not in {"owner", "editor"} and record.author_id != current_user.id:
            raise HTTPException(status_code=403, detail="Note edit permission required")

        version = get_note_version(session, project_id, note_id, version_id)
        record.title = version.title
        record.content = version.content
        create_note_version(session, record, current_user.id)
        session.commit()
        session.refresh(record)
        return note_to_response(record)


@app.delete("/projects/{project_id}/notes/{note_id}", status_code=204)
async def delete_note(
    project_id: int,
    note_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> None:
    with SessionLocal() as session:
        record = get_project_note(session, project_id, note_id)
        membership = get_project_membership(session, project_id, current_user.id)
        if membership.role not in {"owner", "editor"} and record.author_id != current_user.id:
            raise HTTPException(status_code=403, detail="Note delete permission required")

        session.delete(record)
        session.commit()


@app.post("/projects/{project_id}/tasks", status_code=201, response_model=Task)
async def create_task(
    project_id: int,
    payload: TaskCreate,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Task:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        require_project_editor(session, project_id, current_user.id)
        validate_task_assignee(session, project_id, payload.assignee_id)
        record = TaskRecord(
            project_id=project_id,
            creator_id=current_user.id,
            assignee_id=payload.assignee_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return task_to_response(record)


@app.get("/projects/{project_id}/tasks", response_model=list[Task])
async def list_tasks(
    project_id: int,
    status: TaskStatus | None = None,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> list[Task]:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        get_project_membership(session, project_id, current_user.id)
        statement = select(TaskRecord).where(TaskRecord.project_id == project_id)
        if status is not None:
            statement = statement.where(TaskRecord.status == status)
        records = session.scalars(statement.order_by(TaskRecord.updated_at.desc())).all()
        return [task_to_response(record) for record in records]


@app.put("/projects/{project_id}/tasks/{task_id}", response_model=Task)
async def update_task(
    project_id: int,
    task_id: int,
    payload: TaskUpdate,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Task:
    with SessionLocal() as session:
        record = get_project_task(session, project_id, task_id)
        require_project_editor(session, project_id, current_user.id)
        validate_task_assignee(session, project_id, payload.assignee_id)

        record.title = payload.title
        record.description = payload.description
        record.status = payload.status
        record.assignee_id = payload.assignee_id
        session.commit()
        session.refresh(record)
        return task_to_response(record)


@app.delete("/projects/{project_id}/tasks/{task_id}", status_code=204)
async def delete_task(
    project_id: int,
    task_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> None:
    with SessionLocal() as session:
        record = get_project_task(session, project_id, task_id)
        require_project_editor(session, project_id, current_user.id)
        session.delete(record)
        session.commit()


@app.post("/projects/{project_id}/messages", status_code=201, response_model=Message)
async def create_message(
    project_id: int,
    payload: MessageCreate,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Message:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        get_project_membership(session, project_id, current_user.id)
        record = MessageRecord(
            project_id=project_id,
            author_id=current_user.id,
            content=payload.content,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return message_to_response(record, current_user)


@app.get("/projects/{project_id}/messages", response_model=list[Message])
async def list_messages(
    project_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> list[Message]:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        get_project_membership(session, project_id, current_user.id)
        rows = session.execute(
            select(MessageRecord, UserRecord)
            .join(UserRecord, MessageRecord.author_id == UserRecord.id)
            .where(MessageRecord.project_id == project_id)
            .order_by(MessageRecord.created_at.asc(), MessageRecord.id.asc())
        ).all()
        return [
            message_to_response(record, author)
            for record, author in rows
        ]


@app.post("/projects/{project_id}/sources", status_code=201, response_model=Source)
async def create_source(
    project_id: int,
    payload: SourceCreate,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Source:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        require_project_editor(session, project_id, current_user.id)
        record = SourceRecord(
            project_id=project_id,
            creator_id=current_user.id,
            title=payload.title,
            authors=payload.authors,
            publication_year=payload.publication_year,
            source_type=payload.source_type,
            url=str(payload.url) if payload.url is not None else None,
            doi=payload.doi,
        )
        session.add(record)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                status_code=409,
                detail="A source with this DOI already exists in this project.",
            )
        session.refresh(record)
        return source_to_response(record)


@app.get("/projects/{project_id}/sources", response_model=list[Source])
async def list_sources(
    project_id: int,
    source_type: SourceType | None = None,
    q: str | None = Query(default=None, max_length=200),
    current_user: UserRecord = Depends(get_authenticated_user),
) -> list[Source]:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        get_project_membership(session, project_id, current_user.id)
        statement = select(SourceRecord).where(SourceRecord.project_id == project_id)
        if source_type is not None:
            statement = statement.where(SourceRecord.source_type == source_type)
        search_text = q.strip() if q is not None else ""
        if search_text:
            escaped_search = (
                search_text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped_search}%"
            statement = statement.where(or_(
                SourceRecord.title.ilike(pattern, escape="\\"),
                SourceRecord.authors.ilike(pattern, escape="\\"),
                SourceRecord.doi.ilike(pattern, escape="\\"),
            ))
        records = session.scalars(statement.order_by(SourceRecord.updated_at.desc())).all()
        return [source_to_response(record) for record in records]


@app.put("/projects/{project_id}/sources/{source_id}", response_model=Source)
async def update_source(
    project_id: int,
    source_id: int,
    payload: SourceUpdate,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Source:
    with SessionLocal() as session:
        record = session.get(SourceRecord, source_id)
        if record is None or record.project_id != project_id:
            raise HTTPException(status_code=404, detail="Source not found")

        require_project_editor(session, project_id, current_user.id)
        record.title = payload.title
        record.authors = payload.authors
        record.publication_year = payload.publication_year
        record.source_type = payload.source_type
        record.url = str(payload.url) if payload.url is not None else None
        record.doi = payload.doi
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                status_code=409,
                detail="A source with this DOI already exists in this project.",
            )
        session.refresh(record)
        return source_to_response(record)


@app.delete("/projects/{project_id}/sources/{source_id}", status_code=204)
async def delete_source(
    project_id: int,
    source_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> None:
    with SessionLocal() as session:
        record = session.get(SourceRecord, source_id)
        if record is None or record.project_id != project_id:
            raise HTTPException(status_code=404, detail="Source not found")

        require_project_editor(session, project_id, current_user.id)
        session.delete(record)
        session.commit()


@app.post("/projects/{project_id}/attachments", status_code=201, response_model=Attachment)
async def create_attachment(
    project_id: int,
    file: UploadFile = File(...),
    source_id: int | None = Form(default=None),
    current_user: UserRecord = Depends(get_authenticated_user),
) -> Attachment:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        require_project_editor(session, project_id, current_user.id)
        if source_id is not None:
            source = session.get(SourceRecord, source_id)
            if source is None or source.project_id != project_id:
                raise HTTPException(status_code=404, detail="Source not found")

        original_filename, stored_filename, size_bytes, content_type = await save_upload(file)
        try:
            record = AttachmentRecord(
                project_id=project_id,
                source_id=source_id,
                uploaded_by_id=current_user.id,
                original_filename=original_filename,
                stored_filename=stored_filename,
                content_type=content_type,
                size_bytes=size_bytes,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return attachment_to_response(record)
        except Exception:
            session.rollback()
            delete_upload(stored_filename)
            raise


@app.get("/projects/{project_id}/attachments", response_model=list[Attachment])
async def list_attachments(
    project_id: int,
    source_id: int | None = None,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> list[Attachment]:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        get_project_membership(session, project_id, current_user.id)
        if source_id is not None:
            source = session.get(SourceRecord, source_id)
            if source is None or source.project_id != project_id:
                raise HTTPException(status_code=404, detail="Source not found")

        statement = select(AttachmentRecord).where(
            AttachmentRecord.project_id == project_id
        )
        if source_id is not None:
            statement = statement.where(AttachmentRecord.source_id == source_id)
        records = session.scalars(
            statement.order_by(AttachmentRecord.created_at.desc(), AttachmentRecord.id.desc())
        ).all()
        return [attachment_to_response(record) for record in records]


@app.get("/projects/{project_id}/attachments/{attachment_id}/download")
async def download_attachment(
    project_id: int,
    attachment_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> FileResponse:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        get_project_membership(session, project_id, current_user.id)
        record = session.get(AttachmentRecord, attachment_id)
        if record is None or record.project_id != project_id:
            raise HTTPException(status_code=404, detail="Attachment not found")

        file_path = attachment_file_path(record.stored_filename)
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="Attachment file not found")

        return FileResponse(
            file_path,
            filename=record.original_filename,
            media_type=record.content_type or "application/octet-stream",
        )


@app.delete("/projects/{project_id}/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    project_id: int,
    attachment_id: int,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> None:
    with SessionLocal() as session:
        record = session.get(AttachmentRecord, attachment_id)
        if record is None or record.project_id != project_id:
            raise HTTPException(status_code=404, detail="Attachment not found")

        require_project_editor(session, project_id, current_user.id)
        stored_filename = record.stored_filename
        session.delete(record)
        session.commit()
        delete_upload(stored_filename)


PASSWORD_RESET_RESPONSE = (
    "If an account exists for that email, password reset instructions are available."
)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def email_fingerprint(email: str) -> str:
    return hmac.new(
        JWT_SECRET_KEY.encode("utf-8"),
        email.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@app.post("/auth/password-reset/request", status_code=202, response_model=PasswordResetRequestResult)
async def request_password_reset(payload: PasswordResetRequest) -> PasswordResetRequestResult:
    now = datetime.now(timezone.utc)
    raw_token = secrets.token_urlsafe(32)
    fingerprint = email_fingerprint(str(payload.email))

    with SessionLocal() as session:
        recent_attempts = session.scalar(
            select(func.count(PasswordResetAttemptRecord.id)).where(
                PasswordResetAttemptRecord.email_fingerprint == fingerprint,
                PasswordResetAttemptRecord.created_at >= now - timedelta(hours=1),
            )
        ) or 0
        session.add(PasswordResetAttemptRecord(email_fingerprint=fingerprint))

        user = session.scalar(
            select(UserRecord).where(func.lower(UserRecord.email) == str(payload.email))
        )
        if user is not None and recent_attempts < PASSWORD_RESET_MAX_REQUESTS_PER_HOUR:
            session.execute(
                update(PasswordResetTokenRecord)
                .where(
                    PasswordResetTokenRecord.user_id == user.id,
                    PasswordResetTokenRecord.used_at.is_(None),
                )
                .values(used_at=now)
            )
            session.add(PasswordResetTokenRecord(
                user_id=user.id,
                token_hash=hash_reset_token(raw_token),
                expires_at=now + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES),
            ))
        session.commit()

    development_url = None
    if PASSWORD_RESET_DELIVERY_MODE == "development":
        development_url = f"http://localhost:3000/auth/reset?token={raw_token}"
    return PasswordResetRequestResult(
        message=PASSWORD_RESET_RESPONSE,
        development_reset_url=development_url,
    )


@app.post("/auth/password-reset/confirm", status_code=204)
async def confirm_password_reset(payload: PasswordResetConfirm) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        reset_token = session.scalar(
            select(PasswordResetTokenRecord).where(
                PasswordResetTokenRecord.token_hash == hash_reset_token(payload.token),
                PasswordResetTokenRecord.used_at.is_(None),
            )
        )
        if reset_token is None or as_utc(reset_token.expires_at) <= now:
            raise HTTPException(status_code=400, detail="Reset link is invalid or has expired.")

        user = session.get(UserRecord, reset_token.user_id)
        if user is None:
            raise HTTPException(status_code=400, detail="Reset link is invalid or has expired.")

        user.password_hash = hash_password(payload.new_password)
        user.token_version += 1
        session.execute(
            update(PasswordResetTokenRecord)
            .where(
                PasswordResetTokenRecord.user_id == user.id,
                PasswordResetTokenRecord.used_at.is_(None),
            )
            .values(used_at=now)
        )
        session.commit()


@app.post("/auth/account-recovery", status_code=202, response_model=AccountRecoveryResult)
async def create_account_recovery(payload: AccountRecoveryCreate) -> AccountRecoveryResult:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        recent_requests = session.scalar(
            select(func.count(AccountRecoveryRequestRecord.id)).where(
                func.lower(AccountRecoveryRequestRecord.contact_email) == str(payload.contact_email),
                AccountRecoveryRequestRecord.created_at >= now - timedelta(hours=1),
            )
        ) or 0
        if recent_requests >= PASSWORD_RESET_MAX_REQUESTS_PER_HOUR:
            raise HTTPException(status_code=429, detail="Too many recovery requests. Try again later.")

        record = AccountRecoveryRequestRecord(
            reference_code=f"RH-{secrets.token_hex(8).upper()}",
            name=payload.name.strip(),
            contact_email=str(payload.contact_email),
            remembered_email=(
                str(payload.remembered_email) if payload.remembered_email is not None else None
            ),
            details=payload.details.strip(),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return AccountRecoveryResult(
            reference_code=record.reference_code,
            status=record.status,
            message="Recovery request received. Keep the reference code for support follow-up.",
        )


@app.get("/auth/account-recovery/{reference_code}", response_model=AccountRecoveryStatus)
async def get_account_recovery_status(
    reference_code: str,
    contact_email: str = Query(min_length=3, max_length=255),
) -> AccountRecoveryStatus:
    with SessionLocal() as session:
        record = session.scalar(
            select(AccountRecoveryRequestRecord).where(
                AccountRecoveryRequestRecord.reference_code == reference_code.upper(),
                func.lower(AccountRecoveryRequestRecord.contact_email) == contact_email.strip().lower(),
            )
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Recovery request not found.")
        return AccountRecoveryStatus(
            reference_code=record.reference_code,
            status=record.status,
            updated_at=record.updated_at,
        )

@app.post("/auth/register", status_code = 201,response_model = User)
async def register_user(user: UserCreate) -> User:
    with SessionLocal() as session:
        existing_user = session.scalar(
            select(UserRecord).where(func.lower(UserRecord.email) == str(user.email))
        )

        if existing_user:
            raise HTTPException(status_code=409,detail="Email already registered.")

        record = UserRecord(
            name=user.name,
            email=str(user.email),
            password_hash=hash_password(user.password),
        )

        session.add(record)
        session.commit()
        session.refresh(record)

        return User(
            id=record.id,
            name=record.name,
            email=record.email,
        )

@app.post("/auth/login", response_model=Token)
async def login_user(payload: UserLogin) -> Token:
    with SessionLocal() as session:
        record = session.scalar(
            select(UserRecord).where(func.lower(UserRecord.email) == str(payload.email))
        )

        if record is None or not verify_password(
            payload.password,
            record.password_hash,
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password.",
            )

        return Token(access_token=create_access_token(record.id, record.token_version))

@app.get("/auth/me", response_model=User)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),) -> User:
    return user_to_response(get_authenticated_user(credentials))
