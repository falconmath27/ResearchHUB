import os
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_LOCAL_DATABASE_PATH = Path(__file__).resolve().parents[1] / "researchhub.db"

load_dotenv(ENV_FILE)

DATABASE_MODE = os.getenv("DATABASE_MODE", "sqlite")
LOCAL_DATABASE_PATH = Path(
    os.getenv("SQLITE_DATABASE_PATH", str(DEFAULT_LOCAL_DATABASE_PATH))
).resolve()

if DATABASE_MODE == "sqlite":
    DATABASE_URL = f"sqlite:///{LOCAL_DATABASE_PATH.as_posix()}"
else:
    DATABASE_URL = os.environ["DATABASE_URL"]


JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "development-secret-change-before-production",
)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
PASSWORD_RESET_EXPIRE_MINUTES = 30
PASSWORD_RESET_MAX_REQUESTS_PER_HOUR = 3
PASSWORD_RESET_DELIVERY_MODE = os.getenv("PASSWORD_RESET_DELIVERY_MODE", "development")
if PASSWORD_RESET_DELIVERY_MODE not in {"development", "email"}:
    raise ValueError("PASSWORD_RESET_DELIVERY_MODE must be 'development' or 'email'.")

UPLOAD_DIRECTORY = Path(
    os.getenv(
        "UPLOAD_DIRECTORY",
        str(Path(__file__).resolve().parents[1] / "uploads"),
    )
).resolve()
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
AI_DAILY_PROJECT_JOB_LIMIT = int(os.getenv("AI_DAILY_PROJECT_JOB_LIMIT", "5"))
if AI_DAILY_PROJECT_JOB_LIMIT < 1:
    raise ValueError("AI_DAILY_PROJECT_JOB_LIMIT must be positive.")
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".csv", ".tsv", ".txt", ".docx", ".xlsx", ".json"}
