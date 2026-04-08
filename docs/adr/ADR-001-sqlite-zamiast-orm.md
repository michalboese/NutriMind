# ADR-001: SQLite przez stdlib zamiast ORM

| Pole      | Wartość                |
|-----------|------------------------|
| Status    | **Accepted**           |
| Data      | 2026-01-15             |
| Autorzy   | Zespół NutriMind       |
| Dotyczy   | `app/database.py`      |

## Kontekst

Potrzebowaliśmy warstwy persystencji do przechowywania posiłków i podsumowań dziennych. Rozważane opcje:

1. **SQLAlchemy ORM** — pełen ORM z modelem deklaratywnym, migracjami (Alembic), session management
2. **SQLAlchemy Core** — warstwa SQL bez mapowania obiektowego
3. **SQLite przez stdlib `sqlite3`** — bezpośrednie zapytania SQL, zero zależności zewnętrznych
4. **Tortoise ORM / SQLModel** — async ORM-y dedykowane FastAPI

Projekt na etapie MVP operuje na jednej tabeli (`meals`) z prostymi zapytaniami CRUD. Schemat jest stabilny — nie przewidujemy częstych migracji. Aplikacja działa lokalnie, single-user, bez współbieżnych zapisów.

## Decyzja

Wybieramy **SQLite przez moduł `sqlite3` z biblioteki standardowej Pythona**, opakowując operacje synchroniczne w `asyncio.run_in_executor()` aby nie blokować event loop FastAPI.

Uzasadnienie:

- **Zero zależności** — `sqlite3` jest wbudowany w Python, brak dodatkowych pakietów do instalacji
- **Pełna kontrola nad SQL** — zapytania są krótkie i czytelne, ORM dodałby abstrakcję bez korzyści
- **Prostota debugowania** — można otworzyć `calorie_agent.db` w dowolnym kliencie SQLite
- **Brak migracji na start** — jedna tabela z `CREATE TABLE IF NOT EXISTS` wystarczy na etapie MVP
- **Niski narzut poznawczy** — nowy deweloper nie musi znać API żadnego ORM-a

## Konsekwencje

### Zalety

- Brak zależności zewnętrznych dla warstwy bazy danych
- Minimalna ilość kodu — `database.py` to ~80 linii z pełnym CRUD
- Łatwe testowanie — wystarczy `tmp_path` z nowym plikiem `.db` (bez kontenerów, bez mocków bazy)
- Szybki cold start — brak inicjalizacji ORM, connection pool, metadata reflection

### Ograniczenia

- Brak automatycznych migracji — zmiany schematu wymagają ręcznego `ALTER TABLE` lub skryptu
- Brak walidacji na poziomie modelu DB — polegamy na walidacji Pydantic w warstwie API
- `run_in_executor` dodaje minimalny narzut vs natywny async driver (pomijalny przy lokalnym SQLite)

### Trade-offy

- Jeśli projekt wyrośnie ponad 3-4 tabele z relacjami, warto rozważyć migrację do SQLAlchemy Core (nie ORM) z Alembic
- Przy przejściu na PostgreSQL (np. dla wersji SaaS) konieczna będzie wymiana warstwy dostępu — ale `database.py` jest na tyle mały, że przepisanie go to kwestia godzin, nie dni
- Brak connection pooling — dla single-user aplikacji lokalnej nie stanowi problemu
