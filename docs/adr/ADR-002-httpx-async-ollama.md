# ADR-002: httpx z async i exponential backoff do komunikacji z Ollama

| Pole      | Wartość                |
|-----------|------------------------|
| Status    | **Accepted**           |
| Data      | 2026-01-15             |
| Autorzy   | Zespół NutriMind       |
| Dotyczy   | `app/agent.py`         |

## Kontekst

Agent AI komunikuje się z Ollama przez HTTP (`POST /api/chat`). Charakterystyka tego połączenia:

- **Ollama może startować wolno** — model ładuje się do pamięci przy pierwszym zapytaniu (cold start 5-15s)
- **Odpowiedzi LLM są wolne** — generowanie trwa 2-30s w zależności od długości
- **Ollama może być niedostępna** — użytkownik nie uruchomił serwera, port zajęty, restart po aktualizacji
- **FastAPI jest async** — klient HTTP musi być nieblokujący, żeby nie zamrażać event loop

Rozważane opcje:

1. **`requests`** — synchroniczny, zablokuje event loop FastAPI
2. **`aiohttp`** — dojrzały async klient, ale cięższy API, wymaga ręcznego zarządzania sesją
3. **`httpx`** — natywny async/sync, API wzorowane na `requests`, wbudowany timeout management

## Decyzja

Wybieramy **`httpx.AsyncClient`** z ręcznym retry loop i exponential backoff:

```python
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
```

Parametry konfigurowane przez zmienne środowiskowe:

| Zmienna              | Domyślnie | Opis                            |
|----------------------|-----------|---------------------------------|
| `OLLAMA_RETRIES`     | `3`       | Liczba prób                     |
| `OLLAMA_RETRY_DELAY` | `1.0`     | Bazowe opóźnienie (sekundy)     |
| `OLLAMA_TIMEOUT`     | `60.0`    | Timeout pojedynczego requestu   |

## Konsekwencje

### Zalety

- FastAPI event loop nigdy nie jest blokowany — inne requesty są obsługiwane w trakcie oczekiwania na LLM
- Exponential backoff (1s, 2s, 4s) daje Ollamie czas na cold start bez zalewania retryami
- Konfigurowalność — w testach `OLLAMA_RETRIES=1` i `OLLAMA_TIMEOUT=5` przyspieszają feedback loop
- `httpx` ma API prawie identyczne z `requests` — niski próg wejścia dla nowych deweloperów
- Jawne łapanie `ConnectError` i `TimeoutException` pozwala FastAPI zwracać czytelne 503 zamiast 500

### Ograniczenia

- Retry dotyczy tylko błędów sieciowych (`ConnectError`, `TimeoutException`) — błąd 4xx/5xx z Ollama nie jest retryowany (celowe: jeśli model zwraca błąd, retry raczej nie pomoże)
- Brak circuit breaker — przy dłuższej niedostępności Ollamy każdy request czeka pełen cykl retry (max ~7s)

### Trade-offy

- `httpx` to dodatkowa zależność (vs `aiohttp` która też jest zewnętrzna) — ale jest lżejsza i bardziej pythonic
- Ręczny retry loop zamiast biblioteki typu `tenacity` — mniej kodu do utrzymania, pełna kontrola nad logiką, ale brak gotowych dekoratorów
