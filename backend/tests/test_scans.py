"""
Tests for scan API endpoints
"""

import pytest
from fastapi import status


@pytest.mark.api
class TestScanOperations:
    """Test scan CRUD operations"""

    def test_list_scans_success(self, client, auth_headers, test_scan):
        """Test successful scan listing"""
        response = client.get(
            "/api/scans/",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_create_scan_success(self, client, auth_headers, test_repository):
        """Test successful scan creation"""
        response = client.post(
            f"/api/repositories/{test_repository.id}/scans",
            headers=auth_headers,
            json={
                "branch": "main",
                "scanners_used": ["semgrep", "trivy"]
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "pending"
        assert "id" in data

    def test_get_scan_success(self, client, auth_headers, test_scan):
        """Test successful scan retrieval"""
        response = client.get(
            f"/api/scans/{test_scan.id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(test_scan.id)

    def test_get_scan_statistics(self, client, auth_headers, completed_scan):
        """Test getting scan statistics"""
        response = client.get(
            "/api/scans/statistics",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_scans" in data
        assert "completed_scans" in data

    def test_scan_unauthorized(self, client):
        """Test scan operations without authentication"""
        response = client.get("/api/scans/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
