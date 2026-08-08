from app.main import app, validate_project_title
import pytest
from fastapi.testclient import TestClient
from app.schemas import ProjectCreate

from sqlalchemy import text,inspect,delete
from app.database import engine, SessionLocal
from app.models import ProjectRecord


client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_projects() -> None:
    with SessionLocal() as session:
        session.execute(delete(ProjectRecord))
        session.commit()

def create_test_project() -> None:
    response = client.post(
        "/projects",
        json={
            "title": "Text2SQL",
            "summary": "A workspace for collaborating on Text2SQL research projects.",
            "field": "AI",
        },
    )
    assert response.status_code == 201

def test_project_create_accepts_valid_input()->None:
    project = ProjectCreate(
        title ="Climate-resilient cities",
        summary = "A shared workspace for studying climate resilience in growing cities.",
        field = "Urban studies"
    )
    assert project.title == "Climate-resilient cities"
    assert project.field == "Urban studies"

def test_valid_project_title_is_trimmed() -> None:
    assert validate_project_title("  ResearchHub  ") == "ResearchHub"


@pytest.mark.parametrize("title", ["", "  ", "AI", "Hi"])
def test_short_project_titles_are_rejected(title: str) -> None:
    with pytest.raises(ValueError):
        validate_project_title(title)

def test_validate_project_title_api_accepts_valid_title() -> None:
    response = client.post(
        "/learning/validate-project-title",
        json={"title": "  ResearchHub  "},
    )

    assert response.status_code == 200
    assert response.json() == {"title": "ResearchHub"}


def test_validate_project_title_api_rejects_blank_title() -> None:
    response = client.post(
        "/learning/validate-project-title",
        json={"title": "   "},
    )

    assert response.status_code == 422

def test_health_check_api() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "researchhub-api"}

def test_create_project_api() -> None:
    payload = {
        "title": "Text2SQL",
        "summary": "A workspace for collaborating on Text2SQL research projects.",
        "field": "AI",
    }
    expected_project = {
        "id": 1,
        **payload,
        "tags": [],
        "visibility": "private",
    }
    response = client.post("/projects", json=payload)

    assert response.status_code == 201
    assert response.json() == expected_project

def test_create_public_project_api() -> None:
    payload = {
        "title": "AI database systems",
        "summary": "A public project exploring databases designed for AI workloads.",
        "field": "Computer science",
        "tags": ["ai", "databases"],
        "visibility": "public",
    }

    response = client.post("/projects", json=payload)

    assert response.status_code == 201
    assert response.json()["tags"] == ["ai", "databases"]
    assert response.json()["visibility"] == "public"

def test_create_project_api_rejects_invalid_summary() -> None:
    payload = {
        "title": "Text2SQL",
        "summary": "Short",
        "field": "AI",
    }

    response = client.post("/projects", json=payload)

    assert response.status_code == 422


def test_list_projects_api() -> None:
    create_test_project()
    response = client.get("/projects")

    assert response.status_code == 200

    projects = response.json()

    assert isinstance(projects, list)
    assert projects[0]["title"] == "Text2SQL"


def test_get_project_api_returns_project() -> None:
    create_test_project()
    response = client.get("/projects/1")

    assert response.status_code == 200

    project = response.json()

    assert project["title"] == "Text2SQL"


def test_get_project_api_returns_404_for_missing_project() -> None:
    response = client.get("/projects/999")

    assert response.status_code == 404


def test_update_project_api() -> None:
    create_test_project()
    payload = {
        "title": "Updated Text2SQL",
        "summary": "An updated workspace for Text2SQL research.",
        "field": "AI",
        "tags": ["ai", "research"],
        "visibility": "public",
    }

    response = client.put("/projects/1", json=payload)

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Text2SQL"
    assert response.json()["tags"] == ["ai", "research"]
    assert response.json()["visibility"] == "public"

def test_update_project_api_returns_404_for_missing_project() -> None:
    payload = {
        "title": "Updated Text2SQL",
        "summary": "An updated workspace for Text2SQL research.",
        "field": "AI",
    }

    response = client.put("/projects/999", json=payload)

    assert response.status_code == 404


def test_delete_project()->None:
    create_test_project()
    response = client.delete("/projects/1")
    assert response.status_code == 204

def test_delete_project_api_returns_404_for_missing_project()->None:
    response = client.delete("/projects/999")
    assert response.status_code == 404



def test_list_public_projects_api() -> None:
    create_test_project()

    payload = {
        "title": "AI database systems",
        "summary": "A public project exploring databases designed for AI workloads.",
        "field": "Computer science",
        "tags": ["ai", "databases"],
        "visibility": "public",
    }

    create_response = client.post("/projects", json=payload)
    assert create_response.status_code == 201

    response = client.get("/projects?visibility=public")

    assert response.status_code == 200

    projects = response.json()

    assert len(projects) == 1
    assert projects[0]["visibility"] == "public"

def test_list_projects_api_rejects_invalid_visibility()->None:
    response = client.get("/projects?visibility=team-only")
    assert response.status_code == 422

def test_list_projects_by_tag_api()->None:
    create_test_project()

    public_payload = {
        "title": "AI database systems",
        "summary": "A public project exploring databases designed for AI workloads.",
        "field": "Computer science",
        "tags": ["ai", "databases"],
        "visibility": "public",
    }

    create_response = client.post("/projects", json=public_payload)
    assert create_response.status_code == 201

    response = client.get("/projects?tag=databases")

    assert response.status_code == 200

    projects = response.json()

    assert len(projects) == 1
    assert projects[0]["title"] == "AI database systems"

def test_list_public_projects_by_tag_api() -> None:
    create_test_project()

    public_payload = {
        "title": "AI database systems",
        "summary": "A public project exploring databases designed for AI workloads.",
        "field": "Computer science",
        "tags": ["ai", "databases"],
        "visibility": "public",
    }

    client.post("/projects", json=public_payload)

    response = client.get("/projects?visibility=public&tag=ai")

    assert response.status_code == 200

    projects = response.json()

    assert len(projects) == 1
    assert projects[0]["visibility"] == "public"
    assert "ai" in projects[0]["tags"]

def test_database_connection() -> None:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))

    assert result.scalar_one() == 1

# database specific tests
def test_projects_table_exists() -> None:
    table_names = inspect(engine).get_table_names()

    assert "projects" in table_names

def test_database_session_connection() -> None:
    with SessionLocal() as session:
        result = session.execute(text("SELECT 1"))

    assert result.scalar_one() == 1
