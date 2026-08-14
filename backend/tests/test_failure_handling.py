import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_empty_script_creation():
    payload = {
        "name": "Empty Script Test",
        "source_type": "script",
        "source_text": "   "
    }
    res = client.post("/api/projects", json=payload)
    assert res.status_code == 400
    assert "cannot be empty" in res.json()["detail"]

def test_invalid_project_id():
    res = client.get("/api/projects/non-existent-uuid-12345")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
