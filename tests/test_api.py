import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import app.database as db_module
from app.main import app


SAMPLE_ANALYSIS = {
    "meal_name": "Makaron z sosem",
    "calories": 550,
    "protein": 20.0,
    "carbs": 80.0,
    "fat": 12.0,
}


@pytest.fixture(autouse=True)
def tmp_db(tmp_path):
    """Each test gets a fresh in-memory-like DB."""
    db_file = tmp_path / "test.db"
    with patch.object(db_module, "DB_PATH", db_file):
        asyncio.run(db_module.init_db())
        yield


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_meal_success(client):
    with patch("app.main.analyze_meal", new=AsyncMock(return_value=SAMPLE_ANALYSIS)):
        response = client.post("/meals", json={"description": "makaron z sosem pomidorowym"})

    assert response.status_code == 201
    data = response.json()
    assert data["meal_name"] == "Makaron z sosem"
    assert data["calories"] == 550
    assert "id" in data
    assert "created_at" in data


def test_create_meal_empty_description(client):
    response = client.post("/meals", json={"description": ""})
    assert response.status_code == 422


def test_create_meal_ollama_unavailable(client):
    import httpx
    with patch("app.main.analyze_meal", side_effect=httpx.ConnectError("refused")):
        response = client.post("/meals", json={"description": "zupa pomidorowa"})
    assert response.status_code == 503


def test_list_meals_empty(client):
    response = client.get("/meals")
    assert response.status_code == 200
    assert response.json() == []


def test_list_meals_returns_saved(client):
    with patch("app.main.analyze_meal", new=AsyncMock(return_value=SAMPLE_ANALYSIS)):
        client.post("/meals", json={"description": "obiad"})

    response = client.get("/meals")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_meal_not_found(client):
    response = client.get("/meals/9999")
    assert response.status_code == 404


def test_summary_no_meals(client):
    response = client.get("/summary?date=2000-01-01")
    assert response.status_code == 404


def test_summary_with_meals(client):
    with patch("app.main.analyze_meal", new=AsyncMock(return_value=SAMPLE_ANALYSIS)):
        client.post("/meals", json={"description": "obiad"})
        client.post("/meals", json={"description": "kolacja"})

    from datetime import date
    response = client.get(f"/summary?date={date.today().isoformat()}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_calories"] == 1100
    assert data["meal_count"] == 2
