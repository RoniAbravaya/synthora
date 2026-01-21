"""
Integration Tests for Health Endpoint

Tests the health check endpoint with database connection.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for the /health endpoint."""
    
    @pytest.mark.integration
    def test_health_check_returns_ok(self, client: TestClient):
        """Test health check returns OK status."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.integration
    def test_health_check_includes_database_status(self, client: TestClient):
        """Test health check includes database connection status."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include database status
        assert "database" in data or "db" in data or "components" in data
    
    @pytest.mark.integration
    def test_health_check_includes_version(self, client: TestClient):
        """Test health check includes version information."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include version
        assert "version" in data

