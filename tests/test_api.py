from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ask_basic():
    response = client.post(
        "/ask",
        json={"question": "Quel joueur a le plus de rebonds ?"}
    )
    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    assert "route_used" in data