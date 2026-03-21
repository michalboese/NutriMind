import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import app.database as db_module


@pytest.fixture
def tmp_db(tmp_path):
    """Redirect DB_PATH to a temp file for each test."""
    db_file = tmp_path / "test.db"
    with patch.object(db_module, "DB_PATH", db_file):
        asyncio.run(db_module.init_db())
        yield db_file


SAMPLE_ANALYSIS = {
    "meal_name": "Jajecznica",
    "calories": 320,
    "protein": 18.0,
    "carbs": 2.5,
    "fat": 26.0,
}


def test_save_and_get_meal(tmp_db):
    meal_id = asyncio.run(db_module.save_meal("jajecznica z dwóch jajek", SAMPLE_ANALYSIS))
    assert isinstance(meal_id, int) and meal_id > 0

    record = asyncio.run(db_module.get_meal(meal_id))
    assert record is not None
    assert record["meal_name"] == "Jajecznica"
    assert record["calories"] == 320
    assert record["description"] == "jajecznica z dwóch jajek"


def test_get_meal_not_found(tmp_db):
    record = asyncio.run(db_module.get_meal(9999))
    assert record is None


def test_get_meals_all(tmp_db):
    asyncio.run(db_module.save_meal("posiłek 1", SAMPLE_ANALYSIS))
    asyncio.run(db_module.save_meal("posiłek 2", SAMPLE_ANALYSIS))

    meals = asyncio.run(db_module.get_meals())
    assert len(meals) == 2


def test_get_meals_filter_by_date(tmp_db):
    asyncio.run(db_module.save_meal("śniadanie", SAMPLE_ANALYSIS))

    from datetime import date
    today = date.today().isoformat()
    yesterday = "2000-01-01"

    meals_today = asyncio.run(db_module.get_meals(for_date=today))
    meals_old = asyncio.run(db_module.get_meals(for_date=yesterday))

    assert len(meals_today) == 1
    assert len(meals_old) == 0


def test_daily_summary(tmp_db):
    asyncio.run(db_module.save_meal("posiłek 1", SAMPLE_ANALYSIS))
    asyncio.run(db_module.save_meal("posiłek 2", SAMPLE_ANALYSIS))

    from datetime import date
    summary = asyncio.run(db_module.get_daily_summary(for_date=date.today().isoformat()))

    assert summary is not None
    assert summary["meal_count"] == 2
    assert summary["total_calories"] == 640
    assert abs(summary["total_protein"] - 36.0) < 0.01


def test_daily_summary_empty_returns_none(tmp_db):
    summary = asyncio.run(db_module.get_daily_summary(for_date="2000-01-01"))
    assert summary is None
