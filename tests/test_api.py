from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_sql_mock(monkeypatch):
    def fake_poser_question(prompt, vector_store_manager):
        return {
            "question": prompt,
            "answer": "Le joueur ayant pris le plus de rebonds est Ivica Zubac avec 1008 rebonds.",
            "route_used": "SQL",
            "sql_success": True,
        }

    monkeypatch.setattr("api.main.poser_question", fake_poser_question)

    response = client.post(
        "/ask",
        json={"question": "Quel joueur a le plus de rebonds ?"}
    )

    assert response.status_code == 200

    data = response.json()
    assert data["question"] == "Quel joueur a le plus de rebonds ?"
    assert "Ivica Zubac" in data["answer"]
    assert data["route_used"] == "SQL"
    assert data["sql_success"] is True


def test_ask_rag_mock(monkeypatch):
    def fake_poser_question(prompt, vector_store_manager):
        return {
            "question": prompt,
            "answer": "Les fans décrivent Haliburton comme un joueur très vocal et impactant.",
            "route_used": "RAG",
            "sql_success": False,
        }

    monkeypatch.setattr("api.main.poser_question", fake_poser_question)

    response = client.post(
        "/ask",
        json={"question": "Que disent les fans sur Haliburton ?"}
    )

    assert response.status_code == 200

    data = response.json()
    assert data["question"] == "Que disent les fans sur Haliburton ?"
    assert "Haliburton" in data["answer"]
    assert data["route_used"] == "RAG"
    assert data["sql_success"] is False


def test_ask_refus_mock(monkeypatch):
    def fake_poser_question(prompt, vector_store_manager):
        return {
            "question": prompt,
            "answer": "Je ne dispose pas des données nécessaires pour répondre à cette question.",
            "route_used": "REFUS",
            "sql_success": False,
        }

    monkeypatch.setattr("api.main.poser_question", fake_poser_question)

    response = client.post(
        "/ask",
        json={"question": "Quel joueur a le meilleur pourcentage à 3 points sur les 5 derniers matchs ?"}
    )

    assert response.status_code == 200

    data = response.json()
    assert data["question"] == "Quel joueur a le meilleur pourcentage à 3 points sur les 5 derniers matchs ?"
    assert "Je ne dispose pas" in data["answer"]
    assert data["route_used"] == "REFUS"
    assert data["sql_success"] is False