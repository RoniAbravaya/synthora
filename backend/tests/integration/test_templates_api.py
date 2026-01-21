"""
Integration Tests for Templates API

Tests template CRUD operations through the API.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from unittest.mock import patch, MagicMock

from app.models.user import User
from app.models.template import Template


class TestTemplatesAPI:
    """Tests for the /templates endpoints."""
    
    @pytest.fixture
    def mock_current_user(self, test_user: User):
        """Mock the current user dependency."""
        return test_user
    
    # =========================================================================
    # List Templates Tests
    # =========================================================================
    
    @pytest.mark.integration
    def test_list_templates_unauthenticated(self, client: TestClient):
        """Test listing templates without authentication."""
        response = client.get("/api/v1/templates")
        
        # Should return 401 or 403
        assert response.status_code in [401, 403]
    
    @pytest.mark.integration
    def test_list_templates_empty(self, client: TestClient, db: Session, test_user: User):
        """Test listing templates when none exist."""
        # Mock authentication
        with patch("app.core.auth.get_current_user", return_value=test_user):
            response = client.get(
                "/api/v1/templates",
                headers={"Authorization": "Bearer mock_token"}
            )
        
        # Should return empty list or templates
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data or isinstance(data, list)
    
    @pytest.mark.integration
    def test_list_templates_with_system_templates(
        self, client: TestClient, db: Session, test_user: User, system_template: Template
    ):
        """Test listing templates includes system templates."""
        with patch("app.core.auth.get_current_user", return_value=test_user):
            response = client.get(
                "/api/v1/templates",
                headers={"Authorization": "Bearer mock_token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include the system template
        templates = data.get("templates", data)
        assert len(templates) >= 1
    
    # =========================================================================
    # Get Template Tests
    # =========================================================================
    
    @pytest.mark.integration
    def test_get_template_by_id(
        self, client: TestClient, db: Session, test_user: User, system_template: Template
    ):
        """Test getting a specific template by ID."""
        with patch("app.core.auth.get_current_user", return_value=test_user):
            response = client.get(
                f"/api/v1/templates/{system_template.id}",
                headers={"Authorization": "Bearer mock_token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(system_template.id)
        assert data["name"] == system_template.name
    
    @pytest.mark.integration
    def test_get_template_not_found(self, client: TestClient, db: Session, test_user: User):
        """Test getting a non-existent template."""
        fake_id = uuid4()
        
        with patch("app.core.auth.get_current_user", return_value=test_user):
            response = client.get(
                f"/api/v1/templates/{fake_id}",
                headers={"Authorization": "Bearer mock_token"}
            )
        
        assert response.status_code == 404
    
    # =========================================================================
    # Create Template Tests
    # =========================================================================
    
    @pytest.mark.integration
    def test_create_template_success(
        self, client: TestClient, db: Session, test_user: User, sample_template_config
    ):
        """Test creating a new template."""
        template_data = {
            "name": "My Custom Template",
            "description": "A custom template for testing",
            "category": "viral",
            "config": sample_template_config,
        }
        
        with patch("app.core.auth.get_current_user", return_value=test_user):
            response = client.post(
                "/api/v1/templates",
                json=template_data,
                headers={"Authorization": "Bearer mock_token"}
            )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "My Custom Template"
        assert data["user_id"] == str(test_user.id)
    
    @pytest.mark.integration
    def test_create_template_invalid_config(
        self, client: TestClient, db: Session, test_user: User
    ):
        """Test creating a template with invalid configuration."""
        template_data = {
            "name": "Invalid Template",
            "description": "This should fail",
            "category": "viral",
            "config": {
                "video_structure": {
                    "duration_seconds": 5,  # Too short
                    "aspect_ratio": "invalid",
                }
            },
        }
        
        with patch("app.core.auth.get_current_user", return_value=test_user):
            response = client.post(
                "/api/v1/templates",
                json=template_data,
                headers={"Authorization": "Bearer mock_token"}
            )
        
        # Should return validation error
        assert response.status_code in [400, 422]
    
    # =========================================================================
    # Update Template Tests
    # =========================================================================
    
    @pytest.mark.integration
    def test_update_own_template(
        self, client: TestClient, db: Session, test_user: User, user_template: Template
    ):
        """Test updating own template."""
        update_data = {
            "name": "Updated Template Name",
            "description": "Updated description",
        }
        
        with patch("app.core.auth.get_current_user", return_value=test_user):
            response = client.put(
                f"/api/v1/templates/{user_template.id}",
                json=update_data,
                headers={"Authorization": "Bearer mock_token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Template Name"
    
    @pytest.mark.integration
    def test_update_system_template_forbidden(
        self, client: TestClient, db: Session, test_user: User, system_template: Template
    ):
        """Test that regular users cannot update system templates."""
        update_data = {
            "name": "Hacked Template",
        }
        
        with patch("app.core.auth.get_current_user", return_value=test_user):
            response = client.put(
                f"/api/v1/templates/{system_template.id}",
                json=update_data,
                headers={"Authorization": "Bearer mock_token"}
            )
        
        # Should be forbidden for non-admin
        assert response.status_code in [403, 404]
    
    # =========================================================================
    # Delete Template Tests
    # =========================================================================
    
    @pytest.mark.integration
    def test_delete_own_template(
        self, client: TestClient, db: Session, test_user: User, user_template: Template
    ):
        """Test deleting own template."""
        template_id = user_template.id
        
        with patch("app.core.auth.get_current_user", return_value=test_user):
            response = client.delete(
                f"/api/v1/templates/{template_id}",
                headers={"Authorization": "Bearer mock_token"}
            )
        
        assert response.status_code in [200, 204]
        
        # Verify deletion
        deleted = db.query(Template).filter(Template.id == template_id).first()
        assert deleted is None
    
    @pytest.mark.integration
    def test_delete_system_template_forbidden(
        self, client: TestClient, db: Session, test_user: User, system_template: Template
    ):
        """Test that regular users cannot delete system templates."""
        with patch("app.core.auth.get_current_user", return_value=test_user):
            response = client.delete(
                f"/api/v1/templates/{system_template.id}",
                headers={"Authorization": "Bearer mock_token"}
            )
        
        # Should be forbidden for non-admin
        assert response.status_code in [403, 404]
    
    # =========================================================================
    # Duplicate Template Tests
    # =========================================================================
    
    @pytest.mark.integration
    def test_duplicate_template(
        self, client: TestClient, db: Session, test_user: User, system_template: Template
    ):
        """Test duplicating a template."""
        with patch("app.core.auth.get_current_user", return_value=test_user):
            response = client.post(
                f"/api/v1/templates/{system_template.id}/duplicate",
                headers={"Authorization": "Bearer mock_token"}
            )
        
        assert response.status_code in [200, 201]
        data = response.json()
        
        # Should be a new template owned by the user
        assert data["id"] != str(system_template.id)
        assert data["user_id"] == str(test_user.id)
        assert data["is_system"] is False
        assert "Copy" in data["name"] or system_template.name in data["name"]

