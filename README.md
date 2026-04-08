# Calorie Agent

Aplikacja do śledzenia kalorii z agentem AI. Opisz posiłek po polsku lub angielsku — agent (Ollama + llama3.2) automatycznie wyliczy kalorie i makroskładniki.

## Funkcje

- Analiza posiłku z opisu w języku naturalnym (PL/EN)
- Dashboard z wykresami pierścieniowymi postępu dziennego
- Edytowalne cele makroskładników (zapisywane w `settings.json`)
- Historia posiłków w formie tabeli
- Usuwanie posiłków
- API REST (FastAPI) z dokumentacją Swagger

## Stack

- **Backend:** FastAPI + SQLite
- **UI:** Gradio
- **AI:** Ollama (llama3.2)

## Wymagania

- Python 3.10+
- [Ollama](https://ollama.com) zainstalowane lokalnie z modelem `llama3.2`

## Instalacja

```bash
# 1. Sklonuj repo i wejdź do katalogu
git clone <url>
cd calorie-agent

# 2. Utwórz i aktywuj środowisko wirtualne
python -m venv venv
source venv/Scripts/activate      # Windows
# source venv/bin/activate         # Linux/macOS

# 3. Zainstaluj zależności
pip install -r requirements.txt

# 4. Pobierz model AI
ollama pull llama3.2
```

## Uruchomienie

### Opcja A — samo Gradio UI (bez FastAPI)

UI komunikuje się bezpośrednio z bazą i agentem, FastAPI nie jest potrzebny.

```bash
# Terminal 1 — Ollama
ollama run llama3.2

# Terminal 2 — UI
source venv/Scripts/activate
python ui/gradio_app.py
```

Otwórz **http://localhost:7860**

---

### Opcja B — FastAPI + Gradio osobno

```bash
# Terminal 1 — Ollama
ollama run llama3.2

# Terminal 2 — backend API
source venv/Scripts/activate
uvicorn app.main:app --reload
# Swagger UI: http://localhost:8000/docs

# Terminal 3 — UI
source venv/Scripts/activate
python ui/gradio_app.py
# http://localhost:7860
```

## API (skrót)

| Metoda | Endpoint | Opis |
|---|---|---|
| `POST` | `/meals` | Analizuj i zapisz posiłek |
| `GET` | `/meals` | Lista posiłków (`?date=YYYY-MM-DD`) |
| `GET` | `/meals/{id}` | Jeden posiłek |
| `GET` | `/summary` | Suma kalorii/makro za dzień (`?date=`) |
| `GET` | `/health` | Health check |

Przykład:
```bash
curl -X POST http://localhost:8000/meals \
  -H "Content-Type: application/json" \
  -d '{"description": "owsianka z bananem i masłem orzechowym"}'
```

## Testy

```bash
pytest                                          # wszystkie
pytest tests/test_api.py -v                     # tylko API
pytest tests/test_agent.py::test_analyze_meal_strips_markdown_fences  # jeden test
```

Testy nie wymagają uruchomionej Ollamy — agent jest mockowany.

## Cele makro

Domyślne dzienne cele (edytowalne w UI → zakładka Ustawienia):

| Makro | Domyślnie |
|---|---|
| Kalorie | 2000 kcal |
| Białko | 150 g |
| Węglowodany | 250 g |
| Tłuszcze | 70 g |

Cele są zapisywane w pliku `settings.json` w katalogu projektu.

## Zmienne środowiskowe

Opcjonalna konfiguracja agenta (domyślne wartości poniżej):

```bash
OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=60.0
OLLAMA_RETRIES=3
OLLAMA_RETRY_DELAY=1.0
```
