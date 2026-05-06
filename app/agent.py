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
You are a precise nutrition analysis assistant. Estimate calories and macros from a meal description.

LANGUAGE — strict rules:
- Detect the input language and write `meal_name` in the SAME language.
- DO NOT translate. Polish input → Polish meal_name. English input → English meal_name.
- DO NOT drop, replace, rename, or invent ingredients. Every dish or ingredient named by the user must appear in `meal_name`.
  - "Kurczak curry z ryżem" → "Kurczak curry z ryżem" (NOT "Kurczak curry", NOT "Kotlet z ryżem").
  - "Chicken with rice and carrots" → "Chicken with rice and carrots" (NOT translated, NOT abbreviated).
- You may capitalize, normalize spelling, and append a portion size in parentheses. Nothing else.

WEIGHTS — strict rules:
- If the user gives explicit amounts (g, kg, dag, ml, l, oz, lb, or counts like "2 jajka"), use those EXACT amounts.
- Compute each ingredient separately from its given weight, then sum the totals. Do not substitute a "standard portion" when a weight is given.
- Only fall back to typical portions when NO weight or count is given.

PORTION REFERENCE (fallback only — ignore when weights are provided):
- chicken breast = ~150g (~165 kcal, 31g protein)
- bowl of rice = ~200g cooked (~260 kcal)
- plate of pasta = ~250g cooked (~350 kcal)
- glass of milk = ~250ml (~150 kcal)
- slice of bread = ~30g (~80 kcal)
- tbsp of oil/butter = ~15g (~120 kcal, 14g fat)
- egg = ~50g (~70 kcal, 6g protein, 5g fat)
- apple/banana = ~120g (~60-100 kcal)
- handful of nuts = ~30g (~180 kcal, 15g fat)

CROSS-CHECK: calories ≈ (protein × 4) + (carbs × 4) + (fat × 9). Adjust if mismatch > 15%.

Output ONLY a JSON object with these exact keys, no other text:
{"meal_name": str, "calories": int (kcal), "protein": float (g), "carbs": float (g), "fat": float (g)}"""


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
