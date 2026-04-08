# Changelog

Wszystkie istotne zmiany w projekcie NutriMind są dokumentowane w tym pliku.

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/),
wersjonowanie zgodne z [Semantic Versioning](https://semver.org/lang/pl/).

## [Unreleased]

### Changed

- Przepisano diagramy C4 z `C4Context`/`C4Container` na standardowy `flowchart TB` Mermaid — poprawiona czytelność i kompatybilność z GitHubem

### Added

## [0.1.0] - 2026-04-08

### Added

- `POST /meals` — analiza posiłku przez Ollama llama3.2 i zapis do SQLite
- `GET /meals` — lista posiłków z filtrowaniem po dacie (`?date=YYYY-MM-DD`)
- `GET /meals/{id}` — pobranie pojedynczego posiłku
- `GET /summary` — dzienne podsumowanie makroskładników
- `GET /health` — health check endpoint
- Gradio UI z 3 zakładkami: Dodaj posiłek, Historia, Podsumowanie dnia
- Dashboard z wykresami pierścieniowymi postępu dziennego (kalorie, białko, węglowodany, tłuszcze)
- Edytowalne cele dzienne makroskładników (persystowane w `settings.json`)
- Usuwanie posiłków z poziomu UI
- Automatyczne ponowne próby połączenia z Ollama (exponential backoff, 3 próby)
- Walidacja odpowiedzi LLM: odrzucanie wartości ujemnych i nierealistycznych kalorii (>10000)
- System prompt z referencją porcji, cross-check makro vs kalorie, wsparcie PL/EN
- Testy jednostkowe: `test_agent.py` (8 testów), `test_database.py` (6 testów), `test_api.py` (9 testów)
- Konfiguracja przez zmienne środowiskowe: `OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`, `OLLAMA_RETRIES`, `OLLAMA_RETRY_DELAY`
- Swagger UI pod `http://localhost:8000/docs`
