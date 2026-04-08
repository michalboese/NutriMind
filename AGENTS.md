# AGENTS.md — Instrukcje dla agentów AI

## Projekt

NutriMind — lokalna aplikacja do śledzenia kalorii z agentem AI. Użytkownik opisuje posiłek w języku naturalnym (PL/EN), a model LLM (Ollama/llama3.2) szacuje kalorie i makroskładniki.

## Stack

- **Python 3.10+**
- **FastAPI** — REST API backend (`app/main.py`)
- **Gradio** — UI webowe (`ui/gradio_app.py`)
- **httpx** — async HTTP client do komunikacji z Ollama
- **SQLite** — baza danych przez stdlib `sqlite3` (bez ORM)
- **Pydantic v2** — walidacja danych
- **Ollama + llama3.2** — lokalny LLM
- **pytest** — testy z `asyncio_mode = auto`

## Uruchomienie

```bash
source venv/Scripts/activate       # Windows
# source venv/bin/activate          # Linux/macOS
pip install -r requirements.txt

# Ollama musi być uruchomiona
ollama run llama3.2

# UI (standalone, bez FastAPI)
python ui/gradio_app.py            # http://localhost:7860

# API
uvicorn app.main:app --reload      # http://localhost:8000
```

## Testy

```bash
pytest                              # wszystkie testy
pytest tests/test_api.py -v         # jeden plik
pytest tests/test_agent.py::test_analyze_meal_strips_markdown_fences  # jeden test
```

Testy **nie wymagają** uruchomionej Ollamy — `httpx` i `DB_PATH` są mockowane.

## Kluczowe pliki

| Plik                | Rola                                                      |
|---------------------|-----------------------------------------------------------|
| `app/main.py`       | FastAPI app, endpointy REST, obsługa błędów               |
| `app/agent.py`      | `analyze_meal()` — prompt do Ollama, retry, walidacja     |
| `app/database.py`   | SQLite CRUD owinięty w `run_in_executor` (async)          |
| `app/models.py`     | Pydantic v2: `MealRequest`, `MealRecord`, `DailySummary`  |
| `ui/gradio_app.py`  | Gradio UI — dashboard, historia, ustawienia               |
| `settings.json`     | Cele dzienne makroskładników (persystowane z UI)          |

## Konwencje

- **Async everywhere** — FastAPI i Gradio są async, SQLite jest wrapowane przez `run_in_executor`
- **Dwa entry pointy** — FastAPI i Gradio to osobne procesy, oba importują z `app/`
- **Baza w katalogu projektu** — `calorie_agent.db` w root (gitignored)
- **Testy izolowane** — każdy test tworzy własną bazę SQLite w `tmp_path`
- **Commit messages** — format Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`
- **Język UI** — polski
- **Zmienne środowiskowe** — konfiguracja agenta przez `OLLAMA_*` env vars

## Czego NIE robić

- **Nie dodawaj ORM-a** (SQLAlchemy, Tortoise) — świadoma decyzja, patrz `docs/adr/ADR-001`
- **Nie zmieniaj schematu DB bez migracji** — jeśli zmieniasz tabelę `meals`, dodaj skrypt migracji
- **Nie montuj Gradio w FastAPI** — to osobne entry pointy, patrz `docs/adr/ADR-003`
- **Nie zastępuj httpx innym klientem HTTP** bez aktualizacji retry logic
- **Nie dodawaj zależności od internetu** — Ollama działa lokalnie, prywatność jest kluczowa
- **Nie modyfikuj `SYSTEM_PROMPT` bez testowania** — prompt jest precyzyjnie skalibrowany pod llama3.2
- **Nie commituj `calorie_agent.db`** ani `__pycache__/` — są w `.gitignore`
- **Nie usuwaj walidacji odpowiedzi LLM** w `agent.py` (wartości ujemne, >10000 kcal)
