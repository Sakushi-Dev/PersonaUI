"""
Tests for the health check endpoint.
"""
import pytest
import json
from app import app, load_version


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    app.config['APP_VERSION'] = load_version()
    with app.test_client() as client:
        with app.app_context():
            yield client


def test_health_endpoint_reachable(client):
    """Test that the health endpoint is reachable and returns 200."""
    response = client.get('/api/health')
    assert response.status_code == 200


def test_health_endpoint_json_structure(client):
    """Test that the health endpoint returns the correct JSON structure."""
    response = client.get('/api/health')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data is not None
    assert 'success' in data
    assert 'status' in data
    assert 'version' in data
    assert data['success'] is True
    assert data['status'] == 'ok'


def test_health_endpoint_version_value(client):
    """Test that the health endpoint returns a valid version."""
    response = client.get('/api/health')
    assert response.status_code == 200
    
    data = response.get_json()
    version = data.get('version')
    assert version is not None
    assert version != 'unknown'
    assert len(version) > 0
    # Should match the actual version from version.json
    assert version == '0.3.2-alpha'
