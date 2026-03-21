import asyncio
import json
import os
import re
import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
OLLAMA_RETRIES = int(os.environ.get("OLLAMA_RETRIES", "3"))
OLLAMA_RETRY_DELAY = float(os.environ.get("OLLAMA_RETRY_DELAY", "1.0"))
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "60.0"))

SYSTEM_PROMPT = """\
You are a nutrition analysis assistant. Your only job is to analyze meal descriptions and return nutritional data.

RULES:
- Respond ONLY with a valid JSON object. No explanations, no markdown, no extra text.
- Always estimate values even if the description is vague.
- Use realistic average values for common foods and typical portion sizes.

Required JSON format:
{
  "meal_name": "string (short, descriptive name)",
  "calories": integer (kcal),
  "protein": float (grams),
  "carbs": float (grams),
  "fat": float (grams)
}"""


async def analyze_meal(description: str) -> dict:
    """Send a meal description to Ollama and return parsed nutritional data."""
    payload = {
        "model": MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description},
        ],
    }

    last_exc: Exception = RuntimeError("No attempts made")
    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        for attempt in range(OLLAMA_RETRIES):
            try:
                response = await client.post(OLLAMA_URL, json=payload)
                response.raise_for_status()
                break
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < OLLAMA_RETRIES - 1:
                    await asyncio.sleep(OLLAMA_RETRY_DELAY * (2 ** attempt))
        else:
            raise last_exc

    raw = response.json()
    content = raw["message"]["content"].strip()

    # Strip markdown code fences if the model wraps the JSON anyway
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if match:
        content = match.group(1).strip()

    data = json.loads(content)

    meal_name = str(data["meal_name"]).strip()
    calories = int(data["calories"])
    protein = float(data["protein"])
    carbs = float(data["carbs"])
    fat = float(data["fat"])

    if not meal_name:
        raise ValueError("Model returned an empty meal name")
    if calories < 0:
        raise ValueError(f"Model returned negative calories: {calories}")
    if protein < 0:
        raise ValueError(f"Model returned negative protein: {protein}")
    if carbs < 0:
        raise ValueError(f"Model returned negative carbs: {carbs}")
    if fat < 0:
        raise ValueError(f"Model returned negative fat: {fat}")
    if calories > 10000:
        raise ValueError(f"Model returned unrealistic calorie value: {calories}")

    return {
        "meal_name": meal_name,
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
    }
