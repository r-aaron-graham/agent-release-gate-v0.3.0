from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _sqlite_connect_args(url: str) -> dict:
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


def _ensure_sqlite_dir(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    db_path = url.removeprefix("sqlite:///")
    if db_path.startswith("./"):
        db_path = db_path[2:]
    path = Path(db_path)
    if path.parent and str(path.parent) not in {"", "."}:
        path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)
engine = create_engine(settings.database_url, connect_args=_sqlite_connect_args(settings.database_url), future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def create_schema_for_local_dev() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def tables_exist() -> bool:
    inspector = inspect(engine)
    required = {"requests", "audit_events", "review_items"}
    return required.issubset(set(inspector.get_table_names()))
