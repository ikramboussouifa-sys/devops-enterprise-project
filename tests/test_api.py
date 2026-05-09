from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "API is running"
    }


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy"
    }


def test_metrics_endpoint():
    response = client.get("/metrics")

    assert response.status_code == 200

    assert "http_requests_total" in response.text


def test_create_user_validation():
    response = client.post(
        "/users",
        json={
            "name": "Ikram"
        }
    )

    assert response.status_code == 422


def test_create_user_success():
    response = client.post(
        "/users",
        json={
            "name": "Ikram",
            "email": "ikram@example.com"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Ikram"

    assert data["email"] == "ikram@example.com"