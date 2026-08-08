from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(String(1000))
    field: Mapped[str] = mapped_column(String(80))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    visibility: Mapped[str] = mapped_column(String(20), default="private")