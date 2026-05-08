"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health endpoint."""

    def test_health_check(self, client):
        """Test health check returns success."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


class TestSafetyScoreEndpoint:
    """Tests for safety score endpoint."""

    def test_missing_address(self, client):
        """Test request without address."""
        response = client.post("/api/v1/safety-score", json={})
        assert response.status_code == 422  # Validation error

    def test_empty_address(self, client):
        """Test request with empty address."""
        response = client.post(
            "/api/v1/safety-score",
            json={"address": ""}
        )
        # Should fail validation or return error
        assert response.status_code in [400, 422, 500]

    # Note: Full integration tests require API keys and data files
    # These should be run separately with proper setup
