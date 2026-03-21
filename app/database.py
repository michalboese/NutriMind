import asyncio
import sqlite3
from datetime import date, datetime, timezone
from functools import partial
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "calorie_agent.db"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS meals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT    NOT NULL,
    meal_name   TEXT    NOT NULL,
    calories    INTEGER NOT NULL,
    protein     REAL    NOT NULL,
    carbs       REAL    NOT NULL,
    fat         REAL    NOT NULL,
    created_at  TEXT    NOT NULL
)
"""


def _init_db_sync() -> None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(CREATE_TABLE_SQL)
            conn.commit()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to initialize database: {exc}") from exc


async def init_db() -> None:
    """Create DB file and tables. Call once at app startup."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _init_db_sync)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def _save_meal_sync(description: str, analysis: dict) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    sql = """
        INSERT INTO meals (description, meal_name, calories, protein, carbs, fat, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                sql,
                (
                    description,
                    analysis["meal_name"],
                    analysis["calories"],
                    analysis["protein"],
                    analysis["carbs"],
                    analysis["fat"],
                    now,
                ),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to save meal: {exc}") from exc


async def save_meal(description: str, analysis: dict) -> int:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_save_meal_sync, description, analysis))


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def _row_to_dict(row: tuple) -> dict:
    keys = ("id", "description", "meal_name", "calories", "protein", "carbs", "fat", "created_at")
    return dict(zip(keys, row))


def _get_meals_sync(for_date: str | None) -> list[dict]:
    sql = "SELECT id, description, meal_name, calories, protein, carbs, fat, created_at FROM meals"
    params: tuple = ()
    if for_date:
        sql += " WHERE date(created_at) = ?"
        params = (for_date,)
    sql += " ORDER BY created_at DESC"
    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to retrieve meals: {exc}") from exc


async def get_meals(for_date: str | None = None) -> list[dict]:
    """Return all meals, optionally filtered by date (YYYY-MM-DD)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_get_meals_sync, for_date))


def _get_meal_sync(meal_id: int) -> dict | None:
    sql = "SELECT id, description, meal_name, calories, protein, carbs, fat, created_at FROM meals WHERE id = ?"
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(sql, (meal_id,)).fetchone()
        return _row_to_dict(row) if row else None
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to retrieve meal {meal_id}: {exc}") from exc


async def get_meal(meal_id: int) -> dict | None:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_get_meal_sync, meal_id))


def _get_daily_summary_sync(for_date: str) -> dict | None:
    sql = """
        SELECT
            date(created_at)    AS date,
            SUM(calories)       AS total_calories,
            SUM(protein)        AS total_protein,
            SUM(carbs)          AS total_carbs,
            SUM(fat)            AS total_fat,
            COUNT(*)            AS meal_count
        FROM meals
        WHERE date(created_at) = ?
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(sql, (for_date,)).fetchone()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to retrieve daily summary: {exc}") from exc
    if not row or row[0] is None:
        return None
    keys = ("date", "total_calories", "total_protein", "total_carbs", "total_fat", "meal_count")
    return dict(zip(keys, row))


async def get_daily_summary(for_date: str | None = None) -> dict | None:
    """Return aggregated nutritional totals for a given date (default: today)."""
    target = for_date or date.today().isoformat()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_get_daily_summary_sync, target))
