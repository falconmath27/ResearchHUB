from app.main import app, validate_project_title
import pytest
from fastapi.testclient import TestClient
from app.schemas import ProjectCreate, SourceCreate, UserCreate
from pydantic import ValidationError

from sqlalchemy import delete, func, inspect, select, text
from app.database import engine, SessionLocal
from app.models import AccountRecoveryRequestRecord, AttachmentRecord, MessageRecord, NoteRecord, NoteVersionRecord, PasswordResetAttemptRecord, PasswordResetTokenRecord, ProjectMemberRecord, ProjectRecord, SourceRecord, TaskRecord, UserRecord


from app.security import hash_password, verify_password


client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_projects() -> None:
    with SessionLocal() as session:
        session.execute(delete(AttachmentRecord))
        session.execute(delete(NoteVersionRecord))
        session.execute(delete(PasswordResetTokenRecord))
        session.execute(delete(PasswordResetAttemptRecord))
        session.execute(delete(AccountRecoveryRequestRecord))
        session.execute(delete(SourceRecord))
        session.execute(delete(MessageRecord))
        session.execute(delete(NoteRecord))
        session.execute(delete(TaskRecord))
        session.execute(delete(ProjectMemberRecord))
        session.execute(delete(ProjectRecord))
        session.execute(delete(UserRecord))
        session.commit()

    client.headers.pop("Authorization", None)
    client.post("/auth/register", json={
        "name": "Project Owner",
        "email": "owner@example.com",
        "password": "securepass123",
    })
    login_response = client.post("/auth/login", json={
        "email": "owner@example.com",
        "password": "securepass123",
    })
    client.headers["Authorization"] = f"Bearer {login_response.json()['access_token']}"

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

    with SessionLocal() as session:
        membership = session.scalar(select(ProjectMemberRecord))

    assert membership is not None
    assert membership.user_id == 1
    assert membership.role == "owner"

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
    assert "project_members" in table_names

def test_database_session_connection() -> None:
    with SessionLocal() as session:
        result = session.execute(text("SELECT 1"))

    assert result.scalar_one() == 1


#USER specific tests
def test_user_create_schema_accepts_valid_registration() -> None:
    user = UserCreate(
        name="Maya Chen",
        email="maya@example.com",
        password="securepass123",
    )

    assert user.name == "Maya Chen"
    assert user.email == "maya@example.com"


def test_user_create_schema_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(
            name="Maya Chen",
            email="maya@example.com",
            password="short",
        )

def test_register_user_api() -> None:
    payload = {
        "name": "Maya Chen",
        "email": "maya@example.com",
        "password": "securepass123",
    }

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 201
    assert response.json()["name"] == "Maya Chen"
    assert response.json()["email"] == "maya@example.com"


def test_register_user_api_rejects_duplicate_email() -> None:
    payload = {
        "name": "Maya Chen",
        "email": "maya@example.com",
        "password": "securepass123",
    }

    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 409


def test_project_note_crud_api() -> None:
    create_test_project()
    create_response = client.post("/projects/1/notes", json={
        "title": "Research direction",
        "content": "Compare policy effects across regions.",
    })
    note_id = create_response.json()["id"]

    list_response = client.get("/projects/1/notes")
    update_response = client.put(f"/projects/1/notes/{note_id}", json={
        "title": "Updated direction",
        "content": "Compare policy effects across regions and years.",
    })
    delete_response = client.delete(f"/projects/1/notes/{note_id}")

    assert create_response.status_code == 201
    assert create_response.json()["author_id"] == 1
    assert list_response.status_code == 200
    assert list_response.json()[0]["title"] == "Research direction"
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated direction"
    assert delete_response.status_code == 204


def test_viewer_cannot_create_project_note() -> None:
    create_test_project()
    client.post("/auth/register", json={
        "name": "Aisha Patel",
        "email": "aisha@example.com",
        "password": "securepass123",
    })
    client.post("/projects/1/members", json={
        "email": "aisha@example.com",
        "role": "viewer",
    })
    login_response = client.post("/auth/login", json={
        "email": "aisha@example.com",
        "password": "securepass123",
    })

    response = client.post(
        "/projects/1/notes",
        json={"title": "Viewer note", "content": "This should not be created."},
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )

    assert response.status_code == 403


def test_note_versions_are_immutable_and_can_be_restored() -> None:
    create_test_project()
    create_response = client.post("/projects/1/notes", json={
        "title": "Initial research direction",
        "content": "Compare policy effects across regions.",
    })
    note_id = create_response.json()["id"]
    client.put(f"/projects/1/notes/{note_id}", json={
        "title": "Updated research direction",
        "content": "Compare policy effects across regions and years.",
    })

    versions_response = client.get(f"/projects/1/notes/{note_id}/versions")
    initial_version_id = versions_response.json()[1]["id"]
    restore_response = client.post(
        f"/projects/1/notes/{note_id}/versions/{initial_version_id}/restore"
    )
    restored_versions_response = client.get(
        f"/projects/1/notes/{note_id}/versions"
    )

    assert versions_response.status_code == 200
    assert [version["version"] for version in versions_response.json()] == [2, 1]
    assert versions_response.json()[1]["title"] == "Initial research direction"
    assert restore_response.status_code == 200
    assert restore_response.json()["title"] == "Initial research direction"
    assert [version["version"] for version in restored_versions_response.json()] == [3, 2, 1]


def test_project_task_crud_api() -> None:
    create_test_project()
    create_response = client.post("/projects/1/tasks", json={
        "title": "Review the literature",
        "description": "Read the latest policy evaluation studies.",
        "status": "backlog",
        "assignee_id": 1,
    })
    task_id = create_response.json()["id"]

    list_response = client.get("/projects/1/tasks?status=backlog")
    update_response = client.put(f"/projects/1/tasks/{task_id}", json={
        "title": "Review the literature",
        "description": "Read and summarize policy evaluation studies.",
        "status": "in_progress",
        "assignee_id": 1,
    })
    delete_response = client.delete(f"/projects/1/tasks/{task_id}")

    assert create_response.status_code == 201
    assert create_response.json()["creator_id"] == 1
    assert list_response.status_code == 200
    assert list_response.json()[0]["status"] == "backlog"
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_progress"
    assert delete_response.status_code == 204


def test_task_assignee_must_belong_to_project() -> None:
    create_test_project()
    client.post("/auth/register", json={
        "name": "Outside Researcher",
        "email": "outside@example.com",
        "password": "securepass123",
    })

    response = client.post("/projects/1/tasks", json={
        "title": "Review the literature",
        "description": "Read the latest policy evaluation studies.",
        "assignee_id": 2,
    })

    assert response.status_code == 422


def test_project_member_can_create_and_list_messages() -> None:
    create_test_project()
    create_response = client.post("/projects/1/messages", json={
        "content": "The preliminary results are ready for review.",
    })
    list_response = client.get("/projects/1/messages")

    assert create_response.status_code == 201
    assert create_response.json()["author_name"] == "Project Owner"
    assert create_response.json()["content"] == "The preliminary results are ready for review."
    assert list_response.status_code == 200
    assert list_response.json()[0]["author_name"] == "Project Owner"


def test_viewer_can_post_project_message() -> None:
    create_test_project()
    client.post("/auth/register", json={
        "name": "Aisha Patel",
        "email": "aisha@example.com",
        "password": "securepass123",
    })
    client.post("/projects/1/members", json={
        "email": "aisha@example.com",
        "role": "viewer",
    })
    login_response = client.post("/auth/login", json={
        "email": "aisha@example.com",
        "password": "securepass123",
    })

    response = client.post(
        "/projects/1/messages",
        json={"content": "I added my comments to the literature review."},
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )

    assert response.status_code == 201
    assert response.json()["author_name"] == "Aisha Patel"


def test_non_member_cannot_read_project_messages() -> None:
    create_test_project()
    client.post("/auth/register", json={
        "name": "Outside Researcher",
        "email": "outside@example.com",
        "password": "securepass123",
    })
    login_response = client.post("/auth/login", json={
        "email": "outside@example.com",
        "password": "securepass123",
    })

    response = client.get(
        "/projects/1/messages",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )

    assert response.status_code == 404


def test_project_source_crud_and_filter_api() -> None:
    create_test_project()
    create_response = client.post("/projects/1/sources", json={
        "title": "Text-to-SQL Survey",
        "authors": "A. Researcher, B. Scientist",
        "publication_year": 2024,
        "source_type": "article",
        "url": "https://example.com/text-to-sql-survey",
        "doi": "https://doi.org/10.1000/Text2SQL.Survey",
    })
    source_id = create_response.json()["id"]

    list_response = client.get("/projects/1/sources?source_type=article")
    update_response = client.put(f"/projects/1/sources/{source_id}", json={
        "title": "Updated Text-to-SQL Survey",
        "authors": "A. Researcher, B. Scientist",
        "publication_year": 2025,
        "source_type": "report",
        "url": "https://example.com/updated-survey",
        "doi": "doi:10.1000/UPDATED.SURVEY",
    })
    delete_response = client.delete(f"/projects/1/sources/{source_id}")

    assert create_response.status_code == 201
    assert create_response.json()["creator_id"] == 1
    assert create_response.json()["source_type"] == "article"
    assert create_response.json()["doi"] == "10.1000/text2sql.survey"
    assert list_response.status_code == 200
    assert list_response.json()[0]["title"] == "Text-to-SQL Survey"
    assert update_response.status_code == 200
    assert update_response.json()["source_type"] == "report"
    assert update_response.json()["doi"] == "10.1000/updated.survey"
    assert delete_response.status_code == 204


def test_source_doi_validation_and_normalization() -> None:
    source = SourceCreate(
        title="Reliable Research Paper",
        source_type="article",
        doi=" HTTPS://DX.DOI.ORG/10.5555/ResearchHub.2026 ",
    )

    assert source.doi == "10.5555/researchhub.2026"

    with pytest.raises(ValidationError):
        SourceCreate(
            title="Invalid DOI Paper",
            source_type="article",
            doi="not-a-doi",
        )


def test_source_search_matches_title_authors_and_doi_with_type_filter() -> None:
    create_test_project()
    client.post("/projects/1/sources", json={
        "title": "Neural Retrieval Systems",
        "authors": "Mira Chen",
        "source_type": "article",
        "doi": "10.1234/neural.2026",
    })
    client.post("/projects/1/sources", json={
        "title": "Climate Evidence Archive",
        "authors": "Open Data Lab",
        "source_type": "dataset",
        "doi": "10.5678/climate-data",
    })

    title_response = client.get("/projects/1/sources?q=RETRIEVAL")
    author_response = client.get("/projects/1/sources?q=mira")
    doi_response = client.get("/projects/1/sources?q=5678/climate")
    combined_response = client.get("/projects/1/sources?q=climate&source_type=article")

    assert [source["title"] for source in title_response.json()] == ["Neural Retrieval Systems"]
    assert [source["title"] for source in author_response.json()] == ["Neural Retrieval Systems"]
    assert [source["title"] for source in doi_response.json()] == ["Climate Evidence Archive"]
    assert combined_response.json() == []


def test_duplicate_source_doi_is_rejected_within_project() -> None:
    create_test_project()
    first_response = client.post("/projects/1/sources", json={
        "title": "Original Citation",
        "source_type": "article",
        "doi": "10.1000/duplicate",
    })
    duplicate_response = client.post("/projects/1/sources", json={
        "title": "Duplicate Citation",
        "source_type": "report",
        "doi": "https://doi.org/10.1000/DUPLICATE",
    })

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == "A source with this DOI already exists in this project."


def test_viewer_cannot_manage_project_sources() -> None:
    create_test_project()
    client.post("/auth/register", json={
        "name": "Aisha Patel",
        "email": "aisha@example.com",
        "password": "securepass123",
    })
    client.post("/projects/1/members", json={
        "email": "aisha@example.com",
        "role": "viewer",
    })
    login_response = client.post("/auth/login", json={
        "email": "aisha@example.com",
        "password": "securepass123",
    })

    response = client.post(
        "/projects/1/sources",
        json={
            "title": "Viewer source",
            "source_type": "website",
            "url": "https://example.com",
        },
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )

    assert response.status_code == 403


def test_project_attachment_upload_list_download_and_delete_api() -> None:
    create_test_project()
    source_response = client.post("/projects/1/sources", json={
        "title": "Text-to-SQL Survey",
        "source_type": "article",
    })
    source_id = source_response.json()["id"]

    upload_response = client.post(
        "/projects/1/attachments",
        data={"source_id": str(source_id)},
        files={"file": ("findings.txt", b"ResearchHub attachment content", "text/plain")},
    )
    attachment_id = upload_response.json()["id"]

    list_response = client.get(f"/projects/1/attachments?source_id={source_id}")
    download_response = client.get(
        f"/projects/1/attachments/{attachment_id}/download"
    )
    delete_response = client.delete(f"/projects/1/attachments/{attachment_id}")

    assert upload_response.status_code == 201
    assert upload_response.json()["original_filename"] == "findings.txt"
    assert list_response.status_code == 200
    assert list_response.json()[0]["source_id"] == source_id
    assert download_response.status_code == 200
    assert download_response.content == b"ResearchHub attachment content"
    assert delete_response.status_code == 204


def test_project_attachment_rejects_unapproved_file_type() -> None:
    create_test_project()

    response = client.post(
        "/projects/1/attachments",
        files={"file": ("unsafe.exe", b"not allowed", "application/octet-stream")},
    )

    assert response.status_code == 422


def test_viewer_cannot_upload_project_attachments() -> None:
    create_test_project()
    client.post("/auth/register", json={
        "name": "Aisha Patel",
        "email": "aisha@example.com",
        "password": "anothersecurepass",
    })
    owner_login_response = client.post("/auth/login", json={
        "email": "owner@example.com",
        "password": "securepass123",
    })
    client.post(
        "/projects/1/members",
        json={"email": "aisha@example.com", "role": "viewer"},
        headers={"Authorization": f"Bearer {owner_login_response.json()['access_token']}"},
    )
    viewer_login_response = client.post("/auth/login", json={
        "email": "aisha@example.com",
        "password": "anothersecurepass",
    })

    response = client.post(
        "/projects/1/attachments",
        files={"file": ("findings.txt", b"viewer upload", "text/plain")},
        headers={"Authorization": f"Bearer {viewer_login_response.json()['access_token']}"},
    )

    assert response.status_code == 403

## test for password hashing 
def test_password_hashing() -> None:
    password = "securepass123"
    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password)
    assert not verify_password("wrong-password", hashed_password)

#test for login / token auth
def test_login_user_api() -> None:
    registration_payload = {
        "name": "Maya Chen",
        "email": "maya@example.com",
        "password": "securepass123",
    }
    client.post("/auth/register", json=registration_payload)

    response = client.post("/auth/login", json={
        "email": "maya@example.com",
        "password": "securepass123",
    })

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_login_user_api_ignores_email_case() -> None:
    client.post("/auth/register", json={
        "name": "Maya Chen",
        "email": "maya.chen@example.com",
        "password": "securepass123",
    })

    response = client.post("/auth/login", json={
        "email": "MAYA.CHEN@EXAMPLE.COM",
        "password": "securepass123",
    })

    assert response.status_code == 200
    assert isinstance(response.json()["access_token"], str)

# corresponding failure test
def test_login_user_api_rejects_wrong_password() -> None:
    client.post("/auth/register", json={
        "name": "Maya Chen",
        "email": "maya@example.com",
        "password": "securepass123",
    })

    response = client.post("/auth/login", json={
        "email": "maya@example.com",
        "password": "wrongpass123",
    })

    assert response.status_code == 401

def test_get_current_user_api() -> None:
    client.post("/auth/register", json={
        "name": "Maya Chen",
        "email": "maya@example.com",
        "password": "securepass123",
    })

    login_response = client.post("/auth/login", json={
        "email": "maya@example.com",
        "password": "securepass123",
    })
    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Maya Chen"
    assert response.json()["email"] == "maya@example.com"

def test_get_current_user_api_rejects_invalid_token() -> None:
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_password_reset_changes_password_revokes_sessions_and_consumes_token() -> None:
    client.post("/auth/register", json={
        "name": "Maya Chen",
        "email": "maya@example.com",
        "password": "securepass123",
    })
    login_response = client.post("/auth/login", json={
        "email": "maya@example.com",
        "password": "securepass123",
    })
    old_access_token = login_response.json()["access_token"]

    request_response = client.post("/auth/password-reset/request", json={
        "email": "MAYA@EXAMPLE.COM",
    })
    reset_token = request_response.json()["development_reset_url"].split("token=", 1)[1]
    confirm_response = client.post("/auth/password-reset/confirm", json={
        "token": reset_token,
        "new_password": "new-secure-password",
    })

    assert request_response.status_code == 202
    assert confirm_response.status_code == 204
    assert client.post("/auth/login", json={
        "email": "maya@example.com",
        "password": "securepass123",
    }).status_code == 401
    assert client.post("/auth/login", json={
        "email": "maya@example.com",
        "password": "new-secure-password",
    }).status_code == 200
    assert client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {old_access_token}"},
    ).status_code == 401
    assert client.post("/auth/password-reset/confirm", json={
        "token": reset_token,
        "new_password": "another-password",
    }).status_code == 400


def test_password_reset_request_does_not_reveal_whether_account_exists() -> None:
    existing_response = client.post("/auth/password-reset/request", json={
        "email": "owner@example.com",
    })
    missing_response = client.post("/auth/password-reset/request", json={
        "email": "missing@example.com",
    })

    assert existing_response.status_code == 202
    assert missing_response.status_code == 202
    assert existing_response.json()["message"] == missing_response.json()["message"]
    assert missing_response.json()["development_reset_url"] is not None


def test_password_reset_requests_are_rate_limited_without_revealing_it() -> None:
    responses = [
        client.post("/auth/password-reset/request", json={"email": "owner@example.com"})
        for _ in range(4)
    ]

    assert all(response.status_code == 202 for response in responses)
    with SessionLocal() as session:
        assert session.scalar(select(func.count(PasswordResetAttemptRecord.id))) == 4
        assert session.scalar(select(func.count(PasswordResetTokenRecord.id))) == 3


def test_manual_account_recovery_creates_trackable_request() -> None:
    create_response = client.post("/auth/account-recovery", json={
        "name": "Maya Chen",
        "contact_email": "maya.recovery@example.com",
        "remembered_email": "old.maya@example.com",
        "details": "I no longer have access to the email address used for my research workspace.",
    })
    reference_code = create_response.json()["reference_code"]
    status_response = client.get(
        f"/auth/account-recovery/{reference_code}",
        params={"contact_email": "MAYA.RECOVERY@EXAMPLE.COM"},
    )

    assert create_response.status_code == 202
    assert create_response.json()["status"] == "pending"
    assert reference_code.startswith("RH-")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "pending"


def test_project_api_hides_projects_from_non_members() -> None:
    create_test_project()
    client.post("/auth/register", json={
        "name": "Other Researcher",
        "email": "other@example.com",
        "password": "securepass123",
    })
    login_response = client.post("/auth/login", json={
        "email": "other@example.com",
        "password": "securepass123",
    })

    response = client.get(
        "/projects/1",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )

    assert response.status_code == 404


def test_owner_can_add_project_member() -> None:
    create_test_project()

    client.post("/auth/register", json={
        "name": "Aisha Patel",
        "email": "aisha@example.com",
        "password": "securepass123",
    })

    response = client.post("/projects/1/members", json={
        "email": "aisha@example.com",
        "role": "editor",
    })

    assert response.status_code == 201
    assert response.json()["name"] == "Aisha Patel"
    assert response.json()["email"] == "aisha@example.com"
    assert response.json()["role"] == "editor"


def test_non_owner_cannot_add_project_member() -> None:
    create_test_project()

    client.post("/auth/register", json={
        "name": "Aisha Patel",
        "email": "aisha@example.com",
        "password": "securepass123",
    })
    client.post("/projects/1/members", json={
        "email": "aisha@example.com",
        "role": "viewer",
    })
    login_response = client.post("/auth/login", json={
        "email": "aisha@example.com",
        "password": "securepass123",
    })
    other_user_headers = {
        "Authorization": f"Bearer {login_response.json()['access_token']}"
    }

    response = client.post(
        "/projects/1/members",
        json={"email": "owner@example.com", "role": "viewer"},
        headers=other_user_headers,
    )

    assert response.status_code == 403


def test_project_member_can_list_team() -> None:
    create_test_project()

    response = client.get("/projects/1/members")

    assert response.status_code == 200
    assert response.json()[0]["email"] == "owner@example.com"
    assert response.json()[0]["role"] == "owner"


def test_owner_can_update_and_remove_project_member() -> None:
    create_test_project()
    client.post("/auth/register", json={
        "name": "Aisha Patel",
        "email": "aisha@example.com",
        "password": "securepass123",
    })
    add_response = client.post("/projects/1/members", json={
        "email": "aisha@example.com",
        "role": "viewer",
    })
    aisha_id = add_response.json()["id"]

    update_response = client.put(
        f"/projects/1/members/{aisha_id}",
        json={"role": "editor"},
    )
    remove_response = client.delete(f"/projects/1/members/{aisha_id}")

    assert update_response.status_code == 200
    assert update_response.json()["role"] == "editor"
    assert remove_response.status_code == 204


def test_owner_cannot_remove_last_owner() -> None:
    create_test_project()

    response = client.delete("/projects/1/members/1")

    assert response.status_code == 409
