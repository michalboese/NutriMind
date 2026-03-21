from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.agent import analyze_meal
from app.database import get_daily_summary, get_meal, get_meals, init_db, save_meal
from app.models import DailySummary, MealRecord, MealRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Calorie Agent", version="0.1.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/meals", response_model=MealRecord, status_code=201)
async def create_meal(request: MealRequest):
    """Analyze a meal description and persist the result."""
    try:
        analysis = await analyze_meal(request.description)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama. Is it running?")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e.response.status_code}")
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse model response: {e}")

    meal_id = await save_meal(request.description, analysis)
    record = await get_meal(meal_id)
    return record


@app.get("/meals", response_model=list[MealRecord])
async def list_meals(date: str | None = None):
    """Return all meals, optionally filtered by date (YYYY-MM-DD)."""
    return await get_meals(for_date=date)


@app.get("/meals/{meal_id}", response_model=MealRecord)
async def read_meal(meal_id: int):
    record = await get_meal(meal_id)
    if not record:
        raise HTTPException(status_code=404, detail="Meal not found")
    return record


@app.get("/summary", response_model=DailySummary)
async def daily_summary(date: str | None = None):
    """Return aggregated nutrition totals for a day (default: today)."""
    summary = await get_daily_summary(for_date=date)
    if not summary:
        raise HTTPException(status_code=404, detail="No meals logged for this date")
    return summary


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
