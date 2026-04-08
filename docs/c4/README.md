# Diagramy C4 — NutriMind

## Co to C4?

[C4 Model](https://c4model.com) to sposób wizualizacji architektury oprogramowania na 4 poziomach szczegółowości:

1. **Context** — system i jego otoczenie (aktorzy, systemy zewnętrzne)
2. **Container** — główne jednostki deploymentu (aplikacje, bazy danych, serwery)
3. **Component** — wewnętrzne moduły jednego kontenera
4. **Code** — klasy i funkcje (zazwyczaj generowane z kodu)

W tym projekcie utrzymujemy diagramy na poziomie **Context** i **Container** — są wystarczające dla skali NutriMind.

## Pliki

| Plik                   | Poziom    | Opis                                                  |
|------------------------|-----------|-------------------------------------------------------|
| `context.mermaid`      | Context   | NutriMind jako system, aktorzy, systemy zewnętrzne    |
| `containers.mermaid`   | Container | FastAPI, Gradio, Agent, SQLite — relacje i protokoły  |

## Jak czytać

Diagramy są w formacie **Mermaid** — renderują się automatycznie na GitHubie, w VS Code (z rozszerzeniem Mermaid), lub na [mermaid.live](https://mermaid.live).

### Konwencje

- **Niebieskie prostokąty** — wewnętrzne kontenery NutriMind
- **Szare prostokąty** — systemy zewnętrzne (Ollama, SQLite)
- **Strzałki** — kierunek komunikacji z opisem protokołu
- **Person** — aktor ludzki (użytkownik, deweloper)

## Kiedy aktualizować

- Dodanie nowego kontenera (np. osobny serwis do OCR zdjęć)
- Zmiana protokołu komunikacji (np. przejście z httpx na gRPC)
- Dodanie nowego systemu zewnętrznego (np. USDA API)
- Zmiana granic systemu (np. wydzielenie agenta do osobnego procesu)

Nie aktualizuj diagramów przy zmianach wewnątrz istniejących kontenerów (nowy endpoint, nowa funkcja w database.py).
