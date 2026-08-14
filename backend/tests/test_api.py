import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "SLAYERS"

def test_create_and_get_project():
    # 1. Create project
    payload = {
        "name": "Test AI Script Project",
        "source_type": "script",
        "source_text": "This is a test script for automated visual research."
    }
    res = client.post("/api/projects", json=payload)
    assert res.status_code == 201
    proj_data = res.json()
    assert "id" in proj_data
    assert proj_data["name"] == payload["name"]

    # 2. Retrieve project
    proj_id = proj_data["id"]
    get_res = client.get(f"/api/projects/{proj_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == proj_id

def test_create_demo_project():
    res = client.post("/api/projects/demo")
    assert res.status_code == 201
    data = res.json()
    assert "Demo Project" in data["name"]
