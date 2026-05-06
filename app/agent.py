import asyncio
import json
import os
import re
import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")
OLLAMA_RETRIES = int(os.environ.get("OLLAMA_RETRIES", "3"))
OLLAMA_RETRY_DELAY = float(os.environ.get("OLLAMA_RETRY_DELAY", "1.0"))
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120.0"))
OLLAMA_TEMPERATURE = float(os.environ.get("OLLAMA_TEMPERATURE", "0.2"))

SYSTEM_PROMPT = """\
You are a precise nutrition analysis assistant. Analyze meal descriptions and return accurate nutritional data.

RULES:
- Respond ONLY with a valid JSON object. No explanations, no markdown, no extra text.
- ALWAYS estimate realistic values based on typical serving sizes.
- If a weight or portion is specified, use it. Otherwise assume a standard adult serving.
- For complex meals, break down each ingredient mentally and sum the totals.
- meal_name MUST be in the SAME LANGUAGE as the user input.

PORTION REFERENCE (use when no amount is specified):
- plate of pasta = ~250g cooked (~350 kcal)
- bowl of rice = ~200g cooked (~260 kcal)
- chicken breast = ~150g (~165 kcal, 31g protein)
- glass of milk = ~250ml (~150 kcal)
- slice of bread = ~30g (~80 kcal)
- tablespoon of oil/butter = ~15g (~120 kcal, 14g fat)
- egg = ~50g (~70 kcal, 6g protein, 5g fat)
- apple/banana = ~120g (~60-100 kcal)
- handful of nuts = ~30g (~180 kcal, 15g fat)

CROSS-CHECK: After estimating, verify: calories ≈ (protein × 4) + (carbs × 4) + (fat × 9). Adjust if mismatch > 15%.

Required JSON format:
{
  "meal_name": "short descriptive name",
  "calories": integer (kcal),
  "protein": float (grams, 1 decimal),
  "carbs": float (grams, 1 decimal),
  "fat": float (grams, 1 decimal)
}

Example input: "2 jajka sadzone na maśle z 2 tostami"
Example output: {"meal_name": "Jajka sadzone z tostami", "calories": 390, "protein": 18.5, "carbs": 30.0, "fat": 22.0}

Example input: "large pepperoni pizza, 3 slices"
Example output: {"meal_name": "Pepperoni Pizza (3 slices)", "calories": 900, "protein": 36.0, "carbs": 99.0, "fat": 39.0}"""


async def analyze_meal(description: str) -> dict:
    """Send a meal description to Ollama and return parsed nutritional data."""
    payload = {
        "model": MODEL,
        "stream": False,
        "format": "json",
        "options": {"temperature": OLLAMA_TEMPERATURE},
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
