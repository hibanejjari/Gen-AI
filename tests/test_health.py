"""
Tests for health check functionality.

Run with: pytest tests/test_health.py -v
"""

import pytest
from fastapi.testclient import TestClient

# Import the apps
import sys
sys.path.insert(0, '.')

from council_node.main import app as council_app
from chairman.main import app as chairman_app
from orchestrator.main import app as orchestrator_app


class TestCouncilNodeHealth:
    """Tests for council node health endpoint."""
    
    @pytest.fixture
    def client(self):
        return TestClient(council_app)
    
    def test_health_endpoint_exists(self, client):
        """Health endpoint should exist and return 200."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_returns_required_fields(self, client):
        """Health response should contain required fields."""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "node_id" in data
        assert "model" in data
        assert "ollama_status" in data
    
    def test_info_endpoint(self, client):
        """Info endpoint should return node information."""
        response = client.get("/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "role" in data
        assert data["role"] == "council_member"


class TestChairmanHealth:
    """Tests for chairman health endpoint."""
    
    @pytest.fixture
    def client(self):
        return TestClient(chairman_app)
    
    def test_health_endpoint_exists(self, client):
        """Health endpoint should exist and return 200."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_returns_required_fields(self, client):
        """Health response should contain required fields."""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "chairman_id" in data
        assert "model" in data
        assert "ollama_status" in data
    
    def test_info_endpoint(self, client):
        """Info endpoint should return chairman information."""
        response = client.get("/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "role" in data
        assert data["role"] == "chairman"


class TestOrchestratorHealth:
    """Tests for orchestrator health endpoint."""
    
    @pytest.fixture
    def client(self):
        return TestClient(orchestrator_app)
    
    def test_health_endpoint_exists(self, client):
        """Health endpoint should exist and return 200."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_returns_system_status(self, client):
        """Health response should contain system status."""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "council_nodes" in data
        assert "healthy_nodes" in data
        assert "min_required" in data
        assert "can_process" in data
    
    def test_council_status_endpoint(self, client):
        """Council status endpoint should return detailed info."""
        response = client.get("/council/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "council_nodes" in data
        assert "summary" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
