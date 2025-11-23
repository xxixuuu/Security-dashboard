"""
Tests for authentication API endpoints
"""

import pytest
from fastapi import status


@pytest.mark.api
class TestAuthRegister:
    """Test user registration"""

    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePass123!",
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "id" in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_user.email,
                "username": "differentuser",
                "password": "SecurePass123!",
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "different@example.com",
                "username": test_user.username,
                "password": "SecurePass123!",
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Test registration with invalid email format"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",
                "username": "newuser",
                "password": "SecurePass123!",
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "weak",
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.api
class TestAuthLogin:
    """Test user login"""

    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "testpass123",
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_with_username(self, client, test_user):
        """Test login with username instead of email"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.username,
                "password": "testpass123",
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword",
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "somepassword",
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, client, db_session, test_user):
        """Test login with inactive user"""
        test_user.is_active = False
        db_session.commit()

        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "testpass123",
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.api
class TestAuthToken:
    """Test token operations"""

    def test_refresh_token(self, client, test_user):
        """Test token refresh"""
        # First, login to get refresh token
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "testpass123",
            }
        )
        refresh_token = login_response.json()["refresh_token"]

        # Now refresh the token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token"""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user(self, client, auth_headers, test_user):
        """Test getting current user info"""
        response = client.get(
            "/api/auth/me",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without authentication"""
        response = client.get("/api/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestPasswordChange:
    """Test password change functionality"""

    def test_change_password_success(self, client, auth_headers, test_user):
        """Test successful password change"""
        response = client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpass123",
                "new_password": "NewSecurePass456!"
            }
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify can login with new password
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "NewSecurePass456!",
            }
        )
        assert login_response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_current(self, client, auth_headers):
        """Test password change with wrong current password"""
        response = client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "NewSecurePass456!"
            }
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_unauthorized(self, client):
        """Test password change without authentication"""
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "testpass123",
                "new_password": "NewSecurePass456!"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_change_password_weak_new_password(self, client, auth_headers):
        """Test password change with weak new password"""
        response = client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpass123",
                "new_password": "weak"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
