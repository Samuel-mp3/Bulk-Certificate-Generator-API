import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as db_module
import app.services.job_processor as job_processor_module
from app.config import settings
from app.database import Base, get_db
from app.main import app

# Use in-memory SQLite with StaticPool so all background task sessions share the same database
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """
    Sets up a clean test database and temporary certificates directory before each test.
    Overrides SessionLocal in app.database and app.services.job_processor, get_db dependency, and settings.CERTIFICATES_DIR.
    """
    # Create tables on in-memory engine
    Base.metadata.create_all(bind=engine)

    # Patch SessionLocal so background tasks open sessions against the test engine
    orig_session_local_db = db_module.SessionLocal
    orig_session_local_jp = job_processor_module.SessionLocal
    db_module.SessionLocal = TestingSessionLocal
    job_processor_module.SessionLocal = TestingSessionLocal

    # Configure temporary certificate directory for the test
    orig_cert_dir = settings.CERTIFICATES_DIR
    settings.CERTIFICATES_DIR = str(tmp_path / "certificates")
    os.makedirs(settings.CERTIFICATES_DIR, exist_ok=True)

    # Override database session dependency for HTTP endpoints
    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    yield

    # Teardown database and restore settings
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()
    db_module.SessionLocal = orig_session_local_db
    job_processor_module.SessionLocal = orig_session_local_jp
    settings.CERTIFICATES_DIR = orig_cert_dir


@pytest.fixture
def client():
    """Returns FastAPI TestClient instance."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Returns a fresh database session for test assertions."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
