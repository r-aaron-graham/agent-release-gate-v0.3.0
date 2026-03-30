import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DB = Path("/tmp/test_agent_release_gate_v3.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["ADMIN_API_KEY"] = "test-admin-key"
os.environ["SESSION_SECRET_KEY"] = "test-session-secret"
os.environ["AUTO_CREATE_SQLITE_SCHEMA"] = "true"

from app.db.session import Base, engine, SessionLocal, create_schema_for_local_dev  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    engine.dispose()
    if TEST_DB.exists():
        TEST_DB.unlink()
    create_schema_for_local_dev()
    yield
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
