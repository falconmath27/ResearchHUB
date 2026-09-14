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

UPLOAD_DIRECTORY = Path(
    os.getenv(
        "UPLOAD_DIRECTORY",
        str(Path(__file__).resolve().parents[1] / "uploads"),
    )
).resolve()
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".csv", ".tsv", ".txt", ".docx", ".xlsx", ".json"}
