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
- If the input is mixed-language (e.g. "chicken z ryżem"), preserve the user's exact wording. Normalize only spelling and capitalization.
- You may append a portion size in parentheses. Nothing else.

WEIGHTS — strict rules:
- If the user gives explicit amounts (g, kg, dag, ml, l, oz, lb, or counts like "2 eggs"), use those EXACT amounts.
- Compute each ingredient separately from its given weight, then sum the totals. Do not substitute a "standard portion" when a weight is given.
- For counts of non-standardized items (e.g. "2 kotlety", "mała porcja"), use the portion reference below and append the assumed weight to `meal_name` in parentheses.
- Only fall back to typical portions when NO weight or count is given.

PORTION REFERENCE (fallback only — ignore when weights are provided):
- chicken breast = ~150g (165 kcal, 31g protein, 0g carbs, 3.5g fat)
- cooked rice = ~200g (260 kcal, 5g protein, 57g carbs, 0.5g fat)
- cooked pasta = ~250g (350 kcal, 12g protein, 70g carbs, 1.5g fat)
- glass of milk = ~250ml (150 kcal, 8g protein, 12g carbs, 8g fat)
- slice of bread = ~30g (80 kcal, 2.5g protein, 15g carbs, 1g fat)
- tbsp of oil/butter = ~15g (120 kcal, 0g protein, 0g carbs, 14g fat)
- egg = ~50g (70 kcal, 6g protein, 0.5g carbs, 5g fat)
- apple = ~120g (63 kcal, 0.3g protein, 16g carbs, 0.2g fat)
- banana = ~120g (107 kcal, 1.3g protein, 27g carbs, 0.4g fat)
- handful of nuts = ~30g (180 kcal, 5g protein, 6g carbs, 15g fat)

CROSS-CHECK — mandatory before output:
- Compute: estimated_kcal = (protein × 4) + (carbs × 4) + (fat × 9)
- If `calories` deviates more than 15% from `estimated_kcal`, re-derive: adjust fat first, then protein, until the values are consistent.
- Never output a calories value that fails this check.

ERROR CASE:
- If the meal cannot be estimated (too vague, non-food input, or unrecognizable description), do NOT guess.
- Return exactly: {"error": "insufficient description"}

OUTPUT FORMAT:
- Round macros to 1 decimal place. Round calories to the nearest integer.
- Output ONLY a JSON object with these exact keys, no other text:
  {"meal_name": str, "calories": int (kcal), "protein": float (g), "carbs": float (g), "fat": float (g)}
"""


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
