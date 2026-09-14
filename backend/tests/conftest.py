import os
from pathlib import Path


TEST_DATABASE_PATH = Path(__file__).resolve().parents[1] / "test_researchhub.db"
os.environ["SQLITE_DATABASE_PATH"] = str(TEST_DATABASE_PATH)

from app import models  # noqa: E402,F401
from app.database import Base, engine  # noqa: E402


def pytest_sessionstart() -> None:
    TEST_DATABASE_PATH.unlink(missing_ok=True)
    Base.metadata.create_all(engine)


def pytest_sessionfinish() -> None:
    engine.dispose()
    TEST_DATABASE_PATH.unlink(missing_ok=True)
