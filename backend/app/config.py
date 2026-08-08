import os
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
LOCAL_DATABASE_PATH = Path(__file__).resolve().parents[1] / "researchhub.db"

load_dotenv(ENV_FILE)

DATABASE_MODE = os.getenv("DATABASE_MODE", "sqlite")

if DATABASE_MODE == "sqlite":
    DATABASE_URL = f"sqlite:///{LOCAL_DATABASE_PATH.as_posix()}"
else:
    DATABASE_URL = os.environ["DATABASE_URL"]
