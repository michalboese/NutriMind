import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent import analyze_meal


def _make_response(content: str):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"message": {"content": content}}
    return mock


VALID_JSON = json.dumps({
    "meal_name": "Owsianka z bananem",
    "calories": 380,
    "protein": 12.5,
    "carbs": 65.0,
    "fat": 7.2,
})


@pytest.mark.asyncio
async def test_analyze_meal_returns_correct_fields():
    with patch("app.agent.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_make_response(VALID_JSON))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await analyze_meal("owsianka z bananem")

    assert result["meal_name"] == "Owsianka z bananem"
    assert result["calories"] == 380
    assert isinstance(result["protein"], float)
    assert isinstance(result["carbs"], float)
    assert isinstance(result["fat"], float)


@pytest.mark.asyncio
async def test_analyze_meal_strips_markdown_fences():
    wrapped = f"```json\n{VALID_JSON}\n```"
    with patch("app.agent.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_make_response(wrapped))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await analyze_meal("owsianka z bananem")

    assert result["calories"] == 380


@pytest.mark.asyncio
async def test_analyze_meal_raises_on_invalid_json():
    with patch("app.agent.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_make_response("to nie jest JSON"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(json.JSONDecodeError):
            await analyze_meal("cokolwiek")


def _make_client_mock(content: str):
    """Return a patched AsyncClient that yields *content* as the model reply."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=_make_response(content))
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


@pytest.mark.asyncio
async def test_analyze_meal_raises_on_negative_calories():
    bad = json.dumps({"meal_name": "Zupa", "calories": -10, "protein": 5.0, "carbs": 10.0, "fat": 2.0})
    with patch("app.agent.httpx.AsyncClient", return_value=_make_client_mock(bad)):
        with pytest.raises(ValueError, match="negative calories"):
            await analyze_meal("zupa")


@pytest.mark.asyncio
async def test_analyze_meal_raises_on_negative_protein():
    bad = json.dumps({"meal_name": "Sałatka", "calories": 200, "protein": -3.0, "carbs": 10.0, "fat": 2.0})
    with patch("app.agent.httpx.AsyncClient", return_value=_make_client_mock(bad)):
        with pytest.raises(ValueError, match="negative protein"):
            await analyze_meal("sałatka")


@pytest.mark.asyncio
async def test_analyze_meal_raises_on_negative_carbs():
    bad = json.dumps({"meal_name": "Omlet", "calories": 300, "protein": 15.0, "carbs": -5.0, "fat": 20.0})
    with patch("app.agent.httpx.AsyncClient", return_value=_make_client_mock(bad)):
        with pytest.raises(ValueError, match="negative carbs"):
            await analyze_meal("omlet")


@pytest.mark.asyncio
async def test_analyze_meal_raises_on_negative_fat():
    bad = json.dumps({"meal_name": "Ryż", "calories": 200, "protein": 4.0, "carbs": 45.0, "fat": -1.0})
    with patch("app.agent.httpx.AsyncClient", return_value=_make_client_mock(bad)):
        with pytest.raises(ValueError, match="negative fat"):
            await analyze_meal("ryż")


@pytest.mark.asyncio
async def test_analyze_meal_raises_on_unrealistic_calories():
    bad = json.dumps({"meal_name": "Coś", "calories": 99999, "protein": 10.0, "carbs": 10.0, "fat": 10.0})
    with patch("app.agent.httpx.AsyncClient", return_value=_make_client_mock(bad)):
        with pytest.raises(ValueError, match="unrealistic calorie"):
            await analyze_meal("coś")


@pytest.mark.asyncio
async def test_analyze_meal_raises_on_empty_meal_name():
    bad = json.dumps({"meal_name": "   ", "calories": 300, "protein": 10.0, "carbs": 20.0, "fat": 5.0})
    with patch("app.agent.httpx.AsyncClient", return_value=_make_client_mock(bad)):
        with pytest.raises(ValueError, match="empty meal name"):
            await analyze_meal("coś")
