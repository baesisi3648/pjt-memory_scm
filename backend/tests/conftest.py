import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.core.cache import clear_cache
from app.core.database import get_session
from app.main import app

# Ensure all models are registered with SQLModel metadata before create_all
from app.models import *  # noqa: F401, F403

TEST_DATABASE_URL = "sqlite://"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    clear_cache()  # Reset in-memory TTL cache between tests
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    clear_cache()
