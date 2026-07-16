from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="ResearchHub API", version="0.1.0")


class ProjectTitle(BaseModel):
    """The first small validation exercise from Phase 0."""

    title: str = Field(min_length=3, max_length=120)


def validate_project_title(title: str) -> str:
    cleaned_title = title.strip()
    if len(cleaned_title) < 3:
        raise ValueError("A project title needs at least 3 characters.")
    return cleaned_title


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "researchhub-api"}


@app.post("/learning/validate-project-title")
async def validate_title(payload: ProjectTitle) -> dict[str, str]:
    try:
        return {"title": validate_project_title(payload.title)}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
