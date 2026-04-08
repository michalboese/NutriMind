# ADR-003: FastAPI i Gradio jako osobne entry pointy

| Pole      | Wartość                              |
|-----------|--------------------------------------|
| Status    | **Accepted**                         |
| Data      | 2026-01-15                           |
| Autorzy   | Zespół NutriMind                     |
| Dotyczy   | `app/main.py`, `ui/gradio_app.py`    |

## Kontekst

Gradio oferuje dwa tryby integracji z FastAPI:

1. **Mounted** — `gr.mount_gradio_app(fastapi_app, gradio_app, path="/ui")` — Gradio jako sub-application wewnątrz FastAPI
2. **Standalone** — Gradio i FastAPI jako osobne procesy, oba importują wspólną warstwę `app/`

W naszym przypadku:

- UI (Gradio) i API (FastAPI) operują na tej samej bazie SQLite i tym samym agencie
- Użytkownik końcowy korzysta z Gradio, deweloper/integracja korzysta z REST API
- Deployment docelowy to lokalna maszyna (laptop), nie klaster

## Decyzja

Wybieramy **osobne entry pointy** — Gradio i FastAPI uruchamiane jako niezależne procesy:

```
python ui/gradio_app.py          # Gradio UI  → localhost:7860
uvicorn app.main:app --reload    # FastAPI    → localhost:8000
```

Oba importują bezpośrednio z `app/`:

```
ui/gradio_app.py  ──import──►  app/agent.py
                  ──import──►  app/database.py

app/main.py       ──import──►  app/agent.py
                  ──import──►  app/database.py
```

Nie komunikują się ze sobą przez HTTP. Gradio **nie** wywołuje FastAPI — obie warstwy sięgają bezpośrednio do `app/`.

## Konsekwencje

### Zalety

- **Prostota** — użytkownik może uruchomić samo Gradio UI bez FastAPI (wystarczy `python ui/gradio_app.py`)
- **Niezależne skalowanie** — API może działać bez UI i odwrotnie
- **Brak zbędnych zależności** — Gradio nie wymaga FastAPI, FastAPI nie wymaga Gradio
- **Łatwiejszy debugging** — crash UI nie zabija API, crash API nie zabija UI
- **Czyste testy** — testy API testują FastAPI w izolacji, testy UI mogą testować Gradio w izolacji

### Ograniczenia

- Brak współdzielonego stanu w pamięci — oba procesy mają osobne instancje połączeń SQLite (ale SQLite obsługuje wielu czytelników, a zapisy przez WAL journal są bezpieczne)
- Zmiana w `app/` wymaga restartu obu procesów (ale `--reload` w uvicorn i hot-reload w Gradio minimalizują to)

### Trade-offy

- Mounted Gradio dałby jeden proces i jeden port — prostszy deployment, ale tighter coupling i trudniejsze testowanie
- Przy przejściu na deployment produkcyjny (Docker) dwa kontenery zamiast jednego — ale to jest standardowy wzorzec microservices
- Jeśli w przyszłości Gradio UI będzie potrzebowało danych z endpointów niedostępnych w `app/` (np. autentykacja), trzeba będzie albo rozszerzyć `app/`, albo przejść na komunikację HTTP między UI a API
