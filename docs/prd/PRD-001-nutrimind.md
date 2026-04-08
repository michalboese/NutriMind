# PRD-001: NutriMind — Agent AI do śledzenia kalorii

| Pole             | Wartość                                  |
|------------------|------------------------------------------|
| Status           | **Active**                               |
| Wersja           | 1.0                                      |
| Data utworzenia   | 2026-01-10                               |
| Ostatnia zmiana  | 2026-04-08                               |
| Właściciel       | Zespół NutriMind                         |

---

## 1. Problem Statement

Istniejące aplikacje do śledzenia kalorii (MyFitnessPal, Yazio, FatSecret) wymagają od użytkownika ręcznego wyszukiwania produktów w bazie danych, ważenia porcji i ręcznego sumowania składników. Ten proces jest:

- **Czasochłonny** — dodanie jednego posiłku wymaga 1-3 minut klikania i scrollowania
- **Zniechęcający** — większość użytkowników porzuca tracking po 1-2 tygodniach
- **Niedokładny** — użytkownicy wybierają "najbliższy" produkt z bazy, pomijając sposób przygotowania
- **Zależny od internetu** — wymaga stałego połączenia z serwerami producenta

Użytkownicy chcą po prostu powiedzieć "zjadłem schabowego z ziemniakami i surówką" i dostać wynik.

## 2. Business Objective

Stworzyć lokalną, prywatną aplikację, w której **dodanie posiłku zajmuje < 10 sekund** — użytkownik opisuje posiłek w języku naturalnym, a agent AI automatycznie szacuje kalorie i makroskładniki.

### KPI

| Metryka                                  | Cel             | Termin     |
|------------------------------------------|-----------------|------------|
| Czas dodania posiłku (od opisu do zapisu) | < 10s           | MVP (v0.1) |
| Dokładność szacunku kalorii vs referencja | ±20%            | v0.2       |
| Liczba kroków do dodania posiłku          | 1 (opis + enter) | MVP (v0.1) |
| Czas odpowiedzi API (P95)                | < 15s           | MVP (v0.1) |

## 3. Personas

### Kasia — Użytkownik końcowy

- 28 lat, pracuje w biurze, chce schudnąć 5 kg
- Próbowała MyFitnessPal, porzuciła po tygodniu bo "za dużo klikania"
- Chce szybko wpisać co zjadła i zobaczyć czy mieści się w limicie
- Zależy jej na prywatności — nie chce wysyłać danych o jedzeniu do chmury
- Korzysta z laptopa, nie potrzebuje aplikacji mobilnej

### Marek — Deweloper / Integrator

- 32 lata, buduje własne narzędzia do quantified self
- Chce REST API żeby podpiąć tracking kalorii do swojego dashboardu
- Potrzebuje prostych endpointów, dobrze udokumentowanych (Swagger)
- Chce uruchomić projekt lokalnie w 5 minut

## 4. Features

| # | Feature                                        | Priorytet | Status   |
|---|------------------------------------------------|-----------|----------|
| 1 | Analiza posiłku z opisu w języku naturalnym    | **MUST**  | Done     |
| 2 | Zapis posiłków do lokalnej bazy danych         | **MUST**  | Done     |
| 3 | Podsumowanie dzienne (kalorie + makro)         | **MUST**  | Done     |
| 4 | REST API z dokumentacją Swagger                | **MUST**  | Done     |
| 5 | UI webowe (Gradio) z 3 zakładkami              | **MUST**  | Done     |
| 6 | Usuwanie posiłków                              | **MUST**  | Done     |
| 7 | Edytowalne cele dzienne (settings.json)        | **SHOULD**| Done     |
| 8 | Propozycje posiłków w limicie kalorii          | **SHOULD**| Backlog  |
| 9 | Eksport danych (CSV/PDF)                       | **SHOULD**| Backlog  |
| 10| Integracja z zewnętrznym API kalorii (USDA/OFF)| **WON'T** | —        |

### Dlaczego WON'T dla #10

Zewnętrzne API kalorii (USDA FoodData, Open Food Facts) wymagałyby połączenia z internetem, mapowania nazw produktów i obsługi rate limitów. LLM z dobrym promptem daje wystarczająco dobre szacunki dla potrzeb trackingu dziennego, a prywatność i offline-first to kluczowe wartości projektu.

## 5. Non-Functional Requirements

| Wymaganie             | Specyfikacja                                                      |
|-----------------------|-------------------------------------------------------------------|
| Czas odpowiedzi       | P95 < 15s (zależne od Ollama i sprzętu)                          |
| Prywatność danych     | Wszystkie dane lokalne — brak telemetrii, brak chmury             |
| Dostępność offline    | Pełna funkcjonalność bez internetu (Ollama działa lokalnie)       |
| Platforma             | Windows 10+, Linux, macOS — Python 3.10+                         |
| Zależności             | Minimalne — stdlib SQLite, httpx, FastAPI, Gradio, Pydantic      |
| Bezpieczeństwo        | Brak autentykacji (lokalna apka single-user), walidacja inputu   |
| Rozmiar bazy          | Bez limitu (SQLite obsługuje do 281 TB, praktycznie nieograniczone)|

## 6. Out of Scope

- Aplikacja mobilna (iOS/Android)
- Multi-user / autentykacja / autoryzacja
- Deployment chmurowy (AWS/GCP/Azure)
- Rozpoznawanie zdjęć posiłków
- Synchronizacja między urządzeniami
- Plany dietetyczne / automatyczne planowanie posiłków
- Integracja z urządzeniami fitness (Garmin, Fitbit)

## 7. Acceptance Criteria

- [x] Użytkownik wpisuje opis posiłku po polsku lub angielsku i otrzymuje szacunek kalorii + makro
- [x] Wynik jest zapisywany w lokalnej bazie SQLite
- [x] Dashboard pokazuje postęp dzienny z wykresami pierścieniowymi
- [x] Posiłki można przeglądać w historii i usuwać
- [x] Cele dzienne są edytowalne i persystowane między sesjami
- [x] REST API zwraca poprawne odpowiedzi JSON z kodami HTTP (201, 200, 404, 422, 503)
- [x] Swagger UI dostępny pod `/docs`
- [x] Agent obsługuje retry z exponential backoff gdy Ollama jest niedostępna
- [x] Agent odrzuca wartości ujemne i nierealistyczne (>10000 kcal)
- [x] Testy pokrywają agenta, bazę danych i endpointy API
- [ ] Dokładność szacunku kalorii ±20% vs referencja (do walidacji w v0.2)
