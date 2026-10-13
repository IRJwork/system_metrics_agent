
"""Tests des endpoints de l'API FastAPI."""

import pytest
from fastapi.testclient import TestClient

from app.api import app, received_metrics

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_metrics():
    """Réinitialise les métriques avant et après chaque test."""
    received_metrics.clear()
    yield
    received_metrics.clear()


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_metrics_when_empty():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "metrics": [],
    }


def test_receive_metrics_success():
    payload = {
        "agent": "agent-test",
        "event_type": "system_metrics",
        "data": {
            "cpu_percent": 25.5,
            "memory_percent": 60.0,
        },
    }

    response = client.post("/metrics", json=payload)

    assert response.status_code == 201

    result = response.json()
    assert result["status"] == "received"
    assert result["total_received"] == 1

    assert len(received_metrics) == 1
    stored = received_metrics[0]
    assert stored["agent"] == "agent-test"
    assert stored["event_type"] == "system_metrics"
    assert stored["data"] == payload["data"]
    assert "received_at" in stored


def test_receive_metrics_rejects_empty_agent():
    payload = {
        "agent": "",
        "event_type": "system_metrics",
        "data": {},
    }

    response = client.post("/metrics", json=payload)

    assert response.status_code == 422
    assert received_metrics == []


def test_receive_metrics_rejects_missing_data():
    payload = {
        "agent": "agent-test",
        "event_type": "system_metrics",
    }

    response = client.post("/metrics", json=payload)

    assert response.status_code == 422
    assert received_metrics == []


def test_get_latest_metrics_when_empty():
    response = client.get("/metrics/latest")

    assert response.status_code == 404
    assert response.json()["detail"] == "Aucune métrique disponible."


def test_get_latest_metrics_returns_last_received():
    first_payload = {
        "agent": "agent-1",
        "event_type": "system_metrics",
        "data": {"cpu_percent": 10},
    }
    second_payload = {
        "agent": "agent-2",
        "event_type": "system_metrics",
        "data": {"cpu_percent": 80},
    }

    first_response = client.post("/metrics", json=first_payload)
    second_response = client.post("/metrics", json=second_payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = client.get("/metrics/latest")

    assert response.status_code == 200
    assert response.json()["agent"] == "agent-2"
    assert response.json()["data"]["cpu_percent"] == 80


def test_get_metrics_returns_all_received_metrics():
    payloads = [
        {
            "agent": "agent-1",
            "event_type": "system_metrics",
            "data": {"cpu_percent": 10},
        },
        {
            "agent": "agent-2",
            "event_type": "system_metrics",
            "data": {"cpu_percent": 50},
        },
    ]

    for payload in payloads:
        response = client.post("/metrics", json=payload)
        assert response.status_code == 201

    response = client.get("/metrics")

    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 2
    assert len(result["metrics"]) == 2
    assert result["metrics"][0]["agent"] == "agent-1"
    assert result["metrics"][1]["agent"] == "agent-2"
