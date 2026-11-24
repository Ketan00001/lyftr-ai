import os

os.environ["LLM_API_KEYS"] = "test-key-one,test-key-two"
os.environ["DATABASE_URL"] = "sqlite:////tmp/lyftr-test.db"
os.environ["ENABLE_FAILURE_SIMULATION"] = "true"

from fastapi.testclient import TestClient
from app.main import app

def test_health_contract():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert {"status", "keys_configured", "cache_enabled"} <= response.json().keys()

def test_validation_contract():
    with TestClient(app) as client:
        response = client.post("/chat", json={"session_id": "s1", "message": " "})
        assert response.status_code == 422
        assert "detail" in response.json()

def test_unknown_session():
    with TestClient(app) as client:
        response = client.get("/sessions/definitely-unknown/messages")
        assert response.status_code == 404
        assert response.json()["detail"] == "session not found"
