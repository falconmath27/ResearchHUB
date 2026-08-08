from fastapi import FastAPI, HTTPException
from .schemas import ProjectTitle, ProjectCreate, Project, ProjectUpdate
from typing import Literal
from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import ProjectRecord
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ResearchHub API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)

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

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "researchhub-api"}

## response_model = project tells FastAPI that this route must return data matching Porject schema
@app.post("/projects", status_code = 201, response_model = Project) 
async def create_project(payload: ProjectCreate) -> Project:
    record = ProjectRecord(
        title=payload.title,
        summary=payload.summary,
        field=payload.field,
        tags=payload.tags,
        visibility=payload.visibility,
    )

    with SessionLocal() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return project_to_response(record)


@app.get("/projects", response_model=list[Project])
async def list_projects(visibility: Literal["private", "public"] | None = None, tag: str | None = None) -> list[Project]:
    statement = select(ProjectRecord)

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
async def get_project(project_id: int) -> Project:
    with SessionLocal() as session:
        record = session.get(ProjectRecord, project_id)

        if record is not None:
            return project_to_response(record)

    raise HTTPException(status_code=404, detail="Project not found")


@app.put("/projects/{project_id}", response_model=Project)
async def update_project(project_id: int, payload: ProjectUpdate) -> Project:
    with SessionLocal() as session:
        record = session.get(ProjectRecord, project_id)

        if record is not None:
            record.title = payload.title
            record.summary = payload.summary
            record.field = payload.field
            record.tags = payload.tags
            record.visibility = payload.visibility
            session.commit()
            session.refresh(record)
            return project_to_response(record)

    raise HTTPException(status_code=404, detail="Project not found")


@app.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: int) -> None:
    with SessionLocal() as session:
        record = session.get(ProjectRecord, project_id)

        if record is not None:
            session.delete(record)
            session.commit()
            return

    raise HTTPException(status_code=404, detail="Project not found")
