import json
import re
import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

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

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OLLAMA_URL, json=payload)
        response.raise_for_status()

    raw = response.json()
    content = raw["message"]["content"].strip()

    # Strip markdown code fences if the model wraps the JSON anyway
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if match:
        content = match.group(1).strip()

    data = json.loads(content)

    return {
        "meal_name": str(data["meal_name"]),
        "calories": int(data["calories"]),
        "protein": float(data["protein"]),
        "carbs": float(data["carbs"]),
        "fat": float(data["fat"]),
    }
