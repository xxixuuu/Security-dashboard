"""
Pytest configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.models.repository import Repository, RepositoryProvider, RepositoryStatus
from app.models.scan import Scan, ScanStatus, ScanTrigger


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """Create test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create test database session"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session):
    """Create test user"""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpass123"),
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin(db_session):
    """Create test admin user"""
    admin = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash("adminpass123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def auth_token(test_user):
    """Create authentication token for test user"""
    token = create_access_token({"sub": str(test_user.id)})
    return token


@pytest.fixture(scope="function")
def admin_token(test_admin):
    """Create authentication token for admin user"""
    token = create_access_token({"sub": str(test_admin.id)})
    return token


@pytest.fixture(scope="function")
def auth_headers(auth_token):
    """Create authorization headers"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def admin_headers(admin_token):
    """Create admin authorization headers"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="function")
def test_repository(db_session, test_user):
    """Create test repository"""
    repository = Repository(
        id=uuid.uuid4(),
        owner_id=test_user.id,
        name="test-repo",
        full_name="testuser/test-repo",
        description="Test repository",
        url="https://github.com/testuser/test-repo",
        clone_url="https://github.com/testuser/test-repo.git",
        provider=RepositoryProvider.GITHUB,
        provider_id="123456",
        default_branch="main",
        is_private=False,
        is_fork=False,
        status=RepositoryStatus.ACTIVE,
        auto_scan=True,
        scan_on_pr=True,
    )
    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)
    return repository


@pytest.fixture(scope="function")
def test_scan(db_session, test_repository):
    """Create test scan"""
    scan = Scan(
        id=uuid.uuid4(),
        repository_id=test_repository.id,
        status=ScanStatus.PENDING,
        trigger=ScanTrigger.MANUAL,
        branch="main",
        scanners_used=["semgrep", "trivy", "gitleaks"],
    )
    db_session.add(scan)
    db_session.commit()
    db_session.refresh(scan)
    return scan


@pytest.fixture(scope="function")
def completed_scan(db_session, test_repository):
    """Create completed test scan with results"""
    scan = Scan(
        id=uuid.uuid4(),
        repository_id=test_repository.id,
        status=ScanStatus.COMPLETED,
        trigger=ScanTrigger.MANUAL,
        branch="main",
        scanners_used=["semgrep", "trivy", "gitleaks"],
        total_vulnerabilities=10,
        critical_count=2,
        high_count=3,
        medium_count=4,
        low_count=1,
    )
    db_session.add(scan)
    db_session.commit()
    db_session.refresh(scan)
    return scan


# Mock fixtures for external services
@pytest.fixture
def mock_ollama_service(monkeypatch):
    """Mock Ollama service"""
    async def mock_check_health():
        return True

    async def mock_summarize_vulnerability(*args, **kwargs):
        return "This is a test vulnerability summary"

    async def mock_suggest_fix(*args, **kwargs):
        return "This is a test fix suggestion"

    async def mock_analyze_impact(*args, **kwargs):
        return "This is a test impact analysis"

    from app.services import ollama_service
    monkeypatch.setattr(ollama_service, "check_health", mock_check_health)
    monkeypatch.setattr(ollama_service, "summarize_vulnerability", mock_summarize_vulnerability)
    monkeypatch.setattr(ollama_service, "suggest_fix", mock_suggest_fix)
    monkeypatch.setattr(ollama_service, "analyze_impact", mock_analyze_impact)


@pytest.fixture
def mock_notification_service(monkeypatch):
    """Mock notification service"""
    async def mock_send_slack(*args, **kwargs):
        return True

    async def mock_send_discord(*args, **kwargs):
        return True

    async def mock_send_email(*args, **kwargs):
        return True

    from app.services import notification_service
    monkeypatch.setattr(notification_service, "send_slack_notification", mock_send_slack)
    monkeypatch.setattr(notification_service, "send_discord_notification", mock_send_discord)
    monkeypatch.setattr(notification_service, "send_email_notification", mock_send_email)


@pytest.fixture
def mock_github_service(monkeypatch):
    """Mock GitHub service"""
    async def mock_list_repositories(*args, **kwargs):
        return [
            {
                "id": 123,
                "name": "test-repo",
                "full_name": "testuser/test-repo",
                "description": "Test repository",
                "html_url": "https://github.com/testuser/test-repo",
                "clone_url": "https://github.com/testuser/test-repo.git",
                "default_branch": "main",
                "private": False,
                "fork": False,
                "language": "Python",
            }
        ]

    async def mock_get_repository(*args, **kwargs):
        return {
            "id": 123,
            "name": "test-repo",
            "full_name": "testuser/test-repo",
            "description": "Test repository",
            "html_url": "https://github.com/testuser/test-repo",
            "clone_url": "https://github.com/testuser/test-repo.git",
            "default_branch": "main",
            "private": False,
            "fork": False,
            "language": "Python",
        }

    from app.services.github_service import GitHubService
    monkeypatch.setattr(GitHubService, "list_repositories", mock_list_repositories)
    monkeypatch.setattr(GitHubService, "get_repository", mock_get_repository)
