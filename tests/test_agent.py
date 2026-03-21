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
