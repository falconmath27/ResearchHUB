# ResearchHub

ResearchHub is a collaborative workspace where research teams can organize ideas, evidence, tasks, and discussion in one place. It is designed for research work, not code hosting.

## Current status

Phase 0 is in progress. The repository contains a working landing page and a minimal FastAPI learning API.

## Features planned

- [x] Landing page and project structure
- [x] Backend health endpoint and title-validation exercise
- [ ] Authentication and user profiles
- [ ] Private research projects and roles
- [ ] Notes, tasks, and chat
- [ ] Sources, version history, and AI analysis
- [ ] Public project discovery and collaboration requests

## Local setup

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

### Backend

```bash
cd backend
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

Run the Phase 0 validation exercise with:

```bash
pytest
```

## Screenshots

_Landing-page screenshot will be added after the first local run._

## Repository map

```text
frontend/  Next.js + TypeScript landing page
backend/   FastAPI learning API
docs/      Architecture decisions and project notes
```
