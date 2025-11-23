"""
Tests for repository API endpoints
"""

import pytest
from fastapi import status


@pytest.mark.api
class TestRepositoryList:
    """Test repository listing"""

    def test_list_repositories_success(self, client, auth_headers, test_repository):
        """Test successful repository listing"""
        response = client.get(
            "/api/repositories/",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["full_name"] == test_repository.full_name

    def test_list_repositories_unauthorized(self, client):
        """Test repository listing without authentication"""
        response = client.get("/api/repositories/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_repositories_pagination(self, client, auth_headers, test_repository):
        """Test repository listing with pagination"""
        response = client.get(
            "/api/repositories/?skip=0&limit=10",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 10

    def test_list_repositories_filter_by_status(self, client, auth_headers, test_repository):
        """Test repository listing filtered by status"""
        response = client.get(
            "/api/repositories/?status=active",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for repo in data:
            assert repo["status"] == "active"


@pytest.mark.api
class TestRepositoryCreate:
    """Test repository creation"""

    def test_create_repository_success(self, client, auth_headers):
        """Test successful repository creation"""
        response = client.post(
            "/api/repositories/",
            headers=auth_headers,
            json={
                "name": "new-repo",
                "full_name": "testuser/new-repo",
                "description": "New test repository",
                "url": "https://github.com/testuser/new-repo",
                "clone_url": "https://github.com/testuser/new-repo.git",
                "provider": "github",
                "provider_id": "999999",
                "default_branch": "main",
                "is_private": False,
                "is_fork": False,
                "auto_scan": True,
                "scan_on_pr": True,
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["full_name"] == "testuser/new-repo"
        assert data["auto_scan"] is True

    def test_create_repository_duplicate(self, client, auth_headers, test_repository):
        """Test creating duplicate repository"""
        response = client.post(
            "/api/repositories/",
            headers=auth_headers,
            json={
                "name": test_repository.name,
                "full_name": test_repository.full_name,
                "description": "Duplicate",
                "url": test_repository.url,
                "clone_url": test_repository.clone_url,
                "provider": "github",
                "provider_id": test_repository.provider_id,
                "default_branch": "main",
                "is_private": False,
                "is_fork": False,
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"].lower()

    def test_create_repository_unauthorized(self, client):
        """Test repository creation without authentication"""
        response = client.post(
            "/api/repositories/",
            json={
                "name": "new-repo",
                "full_name": "testuser/new-repo",
                "url": "https://github.com/testuser/new-repo",
                "clone_url": "https://github.com/testuser/new-repo.git",
                "provider": "github",
                "provider_id": "999999",
                "default_branch": "main",
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestRepositoryGet:
    """Test repository retrieval"""

    def test_get_repository_success(self, client, auth_headers, test_repository):
        """Test successful repository retrieval"""
        response = client.get(
            f"/api/repositories/{test_repository.id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(test_repository.id)
        assert data["full_name"] == test_repository.full_name

    def test_get_repository_not_found(self, client, auth_headers):
        """Test getting non-existent repository"""
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/api/repositories/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_repository_unauthorized(self, client, test_repository):
        """Test getting repository without authentication"""
        response = client.get(f"/api/repositories/{test_repository.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestRepositoryUpdate:
    """Test repository update"""

    def test_update_repository_success(self, client, auth_headers, test_repository):
        """Test successful repository update"""
        response = client.put(
            f"/api/repositories/{test_repository.id}",
            headers=auth_headers,
            json={
                "description": "Updated description",
                "auto_scan": False,
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["auto_scan"] is False

    def test_update_repository_not_found(self, client, auth_headers):
        """Test updating non-existent repository"""
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.put(
            f"/api/repositories/{fake_id}",
            headers=auth_headers,
            json={"description": "Updated"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_repository_unauthorized(self, client, test_repository):
        """Test updating repository without authentication"""
        response = client.put(
            f"/api/repositories/{test_repository.id}",
            json={"description": "Updated"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestRepositoryDelete:
    """Test repository deletion"""

    def test_delete_repository_success(self, client, auth_headers, test_repository):
        """Test successful repository deletion"""
        response = client.delete(
            f"/api/repositories/{test_repository.id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify it's deleted
        get_response = client.get(
            f"/api/repositories/{test_repository.id}",
            headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_repository_not_found(self, client, auth_headers):
        """Test deleting non-existent repository"""
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/repositories/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_repository_unauthorized(self, client, test_repository):
        """Test deleting repository without authentication"""
        response = client.delete(f"/api/repositories/{test_repository.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestRepositoryImport:
    """Test repository import from GitHub/GitLab"""

    def test_import_github_repositories(self, client, auth_headers, mock_github_service):
        """Test importing repositories from GitHub"""
        response = client.post(
            "/api/repositories/import",
            headers=auth_headers,
            json={
                "provider": "github",
                "auto_scan": True
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["provider"] == "github"

    def test_import_specific_repositories(self, client, auth_headers, mock_github_service):
        """Test importing specific repositories"""
        response = client.post(
            "/api/repositories/import",
            headers=auth_headers,
            json={
                "provider": "github",
                "repository_names": ["testuser/test-repo"],
                "auto_scan": True
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1

    def test_import_repositories_unauthorized(self, client):
        """Test importing repositories without authentication"""
        response = client.post(
            "/api/repositories/import",
            json={"provider": "github"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestRepositorySync:
    """Test repository synchronization"""

    def test_sync_repository_success(self, client, auth_headers, test_repository, mock_github_service):
        """Test successful repository sync"""
        response = client.post(
            f"/api/repositories/{test_repository.id}/sync",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(test_repository.id)

    def test_sync_repository_not_found(self, client, auth_headers):
        """Test syncing non-existent repository"""
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/repositories/{fake_id}/sync",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_sync_repository_unauthorized(self, client, test_repository):
        """Test syncing repository without authentication"""
        response = client.post(f"/api/repositories/{test_repository.id}/sync")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
