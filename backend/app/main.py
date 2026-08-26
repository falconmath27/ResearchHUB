from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
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
)
from typing import Literal
from sqlalchemy import func, select

from .database import SessionLocal
from .models import AttachmentRecord, MessageRecord, NoteRecord, ProjectMemberRecord, ProjectRecord, SourceRecord, TaskRecord, UserRecord
from fastapi.middleware.cors import CORSMiddleware
from .security import hash_password,create_access_token,verify_password,get_user_id_from_token
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .storage import attachment_file_path, delete_upload, save_upload

app = FastAPI(title="ResearchHub API", version="0.1.0")
bearer_scheme = HTTPBearer()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
    user_id = get_user_id_from_token(credentials.credentials)

    with SessionLocal() as session:
        record = session.get(UserRecord, user_id)

        if record is None:
            raise HTTPException(status_code=401, detail="User no longer exists.")

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
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return source_to_response(record)


@app.get("/projects/{project_id}/sources", response_model=list[Source])
async def list_sources(
    project_id: int,
    source_type: SourceType | None = None,
    current_user: UserRecord = Depends(get_authenticated_user),
) -> list[Source]:
    with SessionLocal() as session:
        if session.get(ProjectRecord, project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

        get_project_membership(session, project_id, current_user.id)
        statement = select(SourceRecord).where(SourceRecord.project_id == project_id)
        if source_type is not None:
            statement = statement.where(SourceRecord.source_type == source_type)
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
        session.commit()
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

@app.post("/auth/register", status_code = 201,response_model = User)
async def register_user(user: UserCreate) -> User:
    with SessionLocal() as session:
        existing_user = session.scalar(
            select(UserRecord).where(UserRecord.email == str(user.email))
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
            select(UserRecord).where(UserRecord.email == str(payload.email))
        )

        if record is None or not verify_password(
            payload.password,
            record.password_hash,
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password.",
            )

        return Token(access_token=create_access_token(record.id))

@app.get("/auth/me", response_model=User)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),) -> User:
    return user_to_response(get_authenticated_user(credentials))
