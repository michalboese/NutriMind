# API Reference — NutriMind

Interaktywna dokumentacja (Swagger UI) jest automatycznie generowana przez FastAPI i dostępna pod:

> **http://localhost:8000/docs**

Poniżej opis kontraktu API w czytelnej formie.

---

## Endpointy

| Metoda | Ścieżka         | Opis                                    | Sukces | Błędy              |
|--------|------------------|-----------------------------------------|--------|---------------------|
| `POST` | `/meals`         | Analizuj opis posiłku i zapisz wynik    | `201`  | `422`, `502`, `503` |
| `GET`  | `/meals`         | Lista posiłków (opcjonalnie `?date=`)   | `200`  | `400`, `503`        |
| `GET`  | `/meals/{id}`    | Pojedynczy posiłek po ID                | `200`  | `404`, `503`        |
| `GET`  | `/summary`       | Podsumowanie dzienne (opcjonalnie `?date=`) | `200` | `400`, `404`, `503` |
| `GET`  | `/health`        | Health check                            | `200`  | —                   |

---

## POST /meals

Analizuje opis posiłku przez LLM (Ollama/llama3.2) i zapisuje wynik do bazy.

### Request

```json
{
  "description": "owsianka z bananem i masłem orzechowym"
}
```

**Walidacja wejścia** (`MealRequest`):
- `description` — wymagany string
- Minimalna długość: **3 znaki**
- Maksymalna długość: **500 znaków**
- Nie może być pusty ani składać się wyłącznie z białych znaków

### Response `201 Created`

```json
{
  "id": 1,
  "description": "owsianka z bananem i masłem orzechowym",
  "meal_name": "Owsianka z bananem i masłem orzechowym",
  "calories": 420,
  "protein": 14.5,
  "carbs": 58.0,
  "fat": 16.0,
  "created_at": "2026-04-08T12:30:00"
}
```

---

## GET /meals

Zwraca listę posiłków, opcjonalnie filtrowanych po dacie.

### Query Parameters

| Parametr | Typ    | Wymagany | Format       | Opis                        |
|----------|--------|----------|--------------|-----------------------------|
| `date`   | string | nie      | `YYYY-MM-DD` | Filtruj po dacie utworzenia  |

### Response `200 OK`

```json
[
  {
    "id": 2,
    "description": "schabowy z ziemniakami",
    "meal_name": "Schabowy z ziemniakami",
    "calories": 650,
    "protein": 35.0,
    "carbs": 45.0,
    "fat": 32.0,
    "created_at": "2026-04-08T13:00:00"
  }
]
```

---

## GET /summary

Zwraca zagregowane wartości żywieniowe za dany dzień.

### Query Parameters

| Parametr | Typ    | Wymagany | Format       | Opis                          |
|----------|--------|----------|--------------|-------------------------------|
| `date`   | string | nie      | `YYYY-MM-DD` | Dzień do podsumowania (domyślnie: dziś) |

### Response `200 OK`

```json
{
  "date": "2026-04-08",
  "total_calories": 1070,
  "total_protein": 49.5,
  "total_carbs": 103.0,
  "total_fat": 48.0,
  "meal_count": 2
}
```

---

## Obsługa błędów

| Kod  | Kiedy                                                              | Przykład `detail`                                |
|------|--------------------------------------------------------------------|--------------------------------------------------|
| `400`| Nieprawidłowy format daty w query parameter                        | `"Invalid date format — expected YYYY-MM-DD"`    |
| `404`| Posiłek o danym ID nie istnieje / brak posiłków dla danej daty    | `"Meal not found"`, `"No meals logged for this date"` |
| `422`| Walidacja Pydantic (za krótki opis) lub nieparsowalna odpowiedź LLM | `"Failed to parse model response: ..."`         |
| `502`| Ollama zwróciła błąd HTTP (np. model nie załadowany)              | `"Model service returned an error"`              |
| `503`| Ollama niedostępna lub timeout po wyczerpaniu retry               | `"Cannot connect to Ollama. Is it running?"`     |

### Format błędu

Wszystkie błędy zwracane są w formacie FastAPI:

```json
{
  "detail": "Cannot connect to Ollama. Is it running?"
}
```

---

## Modele danych

### MealRequest (input)

```python
class MealRequest(BaseModel):
    description: str = Field(..., min_length=3, max_length=500)
```

### MealRecord (output)

```python
class MealRecord(BaseModel):
    id: int
    description: str
    meal_name: str
    calories: int
    protein: float
    carbs: float
    fat: float
    created_at: datetime
```

### DailySummary (output)

```python
class DailySummary(BaseModel):
    date: str
    total_calories: int
    total_protein: float
    total_carbs: float
    total_fat: float
    meal_count: int
```
