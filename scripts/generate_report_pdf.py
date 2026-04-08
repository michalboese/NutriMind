# -*- coding: utf-8 -*-
"""Generates NutriMind_Agent_Opis_Projektu_Czesc2.pdf"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from pathlib import Path

OUTPUT = Path(r"C:\Users\boese\Downloads\NutriMind_Agent_Opis_Projektu_Czesc2.pdf")

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
GREEN   = colors.HexColor("#2ecc71")
DARK    = colors.HexColor("#1a1a2e")
PANEL   = colors.HexColor("#f4f6f9")
CODE_BG = colors.HexColor("#1e1e2e")
CODE_FG = colors.HexColor("#cdd6f4")
ACCENT  = colors.HexColor("#3498db")
WARN    = colors.HexColor("#e74c3c")
MUTED   = colors.HexColor("#7f8c8d")
WHITE   = colors.white
BLACK   = colors.black

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
def S(name, **kw):
    return ParagraphStyle(name, **kw)

cover_title = S("CoverTitle", fontName="Helvetica-Bold", fontSize=28,
                textColor=WHITE, alignment=TA_CENTER, leading=36)
cover_sub   = S("CoverSub",   fontName="Helvetica",      fontSize=13,
                textColor=colors.HexColor("#aed6f1"), alignment=TA_CENTER, leading=20)
cover_date  = S("CoverDate",  fontName="Helvetica",      fontSize=10,
                textColor=colors.HexColor("#85c1e9"), alignment=TA_CENTER)

h1 = S("H1", fontName="Helvetica-Bold", fontSize=16,
        textColor=DARK, spaceBefore=18, spaceAfter=6, leading=22)
h2 = S("H2", fontName="Helvetica-Bold", fontSize=13,
        textColor=ACCENT, spaceBefore=12, spaceAfter=4, leading=18)
h3 = S("H3", fontName="Helvetica-Bold", fontSize=11,
        textColor=DARK, spaceBefore=8, spaceAfter=3, leading=15)

body = S("Body", fontName="Helvetica", fontSize=10,
         textColor=BLACK, leading=15, spaceAfter=4, alignment=TA_JUSTIFY)
body_left = S("BodyLeft", fontName="Helvetica", fontSize=10,
              textColor=BLACK, leading=15, spaceAfter=4)
bullet = S("Bullet", fontName="Helvetica", fontSize=10,
           textColor=BLACK, leading=14, spaceAfter=3,
           leftIndent=16, bulletIndent=4)
code_style = S("Code", fontName="Courier", fontSize=8.5,
               textColor=CODE_FG, leading=13, spaceAfter=0)

# ---------------------------------------------------------------------------
# Helper flowables
# ---------------------------------------------------------------------------

def code_block(lines):
    """Renders a dark-background monospace code block."""
    rows = []
    for ln in lines:
        safe = ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace(" ", "&nbsp;")
        rows.append([Paragraph(safe, code_style)])
    t = Table(rows, colWidths=[17.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CODE_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    return t


def info_table(rows, col_widths=None):
    col_widths = col_widths or [5 * cm, 12.5 * cm]
    data = [[Paragraph("<b>" + k + "</b>", body_left), Paragraph(v, body_left)]
            for k, v in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PANEL]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dce1e7")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def section_rule():
    return HRFlowable(width="100%", thickness=1.5, color=ACCENT,
                      spaceAfter=6, spaceBefore=2)


def sp(n=8):
    return Spacer(1, n)


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------

def cover_page():
    elems = []
    stripe = Table(
        [[Paragraph("NutriMind", cover_title)],
         [Paragraph("Asystent sledzenia kalorii z AI", cover_sub)],
         [sp(6)],
         [Paragraph("Opis projektu - Czesc 2", cover_sub)],
         [sp(4)],
         [Paragraph("Dokumentacja postepu prac · 2026", cover_date)]],
        colWidths=[17.5 * cm],
    )
    stripe.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 22),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 22),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
    ]))
    elems.append(stripe)
    elems.append(sp(18))

    meta = [
        ("Przedmiot",         "Agenty AI"),
        ("Autorzy",           "Michal Boese (102218)  ·  Adam Rekruciak (102487)"),
        ("Data",              "2 kwietnia 2026"),
        ("Wersja dokumentu",  "2.0 - Raport z postepu prac"),
        ("Repozytorium",      "github.com/michalboese/calorie-agent"),
    ]
    elems.append(info_table(meta, col_widths=[4.5 * cm, 13 * cm]))
    elems.append(sp(14))

    badges = [
        ["OK  Backend API",     "OK  Interfejs Gradio",  "OK  Testy (24/24)"],
        ["OK  Baza danych",     "OK  Integracja Ollama", "OK  Dokumentacja"],
    ]
    bt = Table(badges, colWidths=[5.8 * cm, 5.8 * cm, 5.8 * cm])
    bt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#eafaf1")),
        ("TEXTCOLOR",     (0, 0), (-1, -1), colors.HexColor("#1e8449")),
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#a9dfbf")),
    ]))
    elems.append(bt)
    elems.append(PageBreak())
    return elems


# ---------------------------------------------------------------------------
# Section 1
# ---------------------------------------------------------------------------

def section_temat():
    elems = []
    elems.append(Paragraph("1. Temat i cel projektu", h1))
    elems.append(section_rule())
    elems.append(Paragraph(
        "Projekt NutriMind to aplikacja do sledzenia kalorii i makroskladnikow "
        "odzywiania, ktora przyjmuje opis posilku w jezyku naturalnym (polskim lub "
        "angielskim) i automatycznie szacuje jego wartosc energetyczna oraz zawartosc "
        "bialka, weglowodanow i tluszczow bez koniecznosci recznego wyszukiwania "
        "produktow w bazie danych.",
        body))
    elems.append(Paragraph(
        "Kluczowym elementem jest <b>lokalny model jezykowy</b> (Ollama + llama3.2) "
        "uruchamiany bezposrednio na komputerze uzytkownika. Dzieki temu zadne dane "
        "nie opuszczaja lokalnego srodowiska, a aplikacja dziala bez dostepu do "
        "Internetu i jest calkowicie bezplatna w uzyciu.",
        body))

    elems.append(Paragraph("Zakres funkcjonalny", h2))
    features = [
        ("Analiza posilku",
         "Uzytkownik wpisuje swobodny opis (np. owsianka z bananem i lyzka masla orzechowego), "
         "a agent zwraca szacunkowe wartosci odzywcze w formacie JSON."),
        ("Historia posilkow",
         "Przegladanie wszystkich zapisanych posilkow z filtrowaniem po dacie; "
         "mozliwosc usuwania wpisow."),
        ("Podsumowanie dzienne",
         "Zsumowane makroskladniki i kalorie dla wybranego dnia wraz "
         "z wizualnym porownaniem do celow uzytkownika (wykresy SVG)."),
        ("Cele makroskladnikow",
         "Uzytkownik moze ustawic wlasne dzienne limity kalorii, "
         "bialka, weglowodanow i tluszczow persystowane w settings.json."),
        ("REST API",
         "FastAPI udostepnia endpointy umozliwiajace integracje "
         "z dowolnym frontendem lub narzedziem zewnetrznym."),
        ("Odpornosc na bledy",
         "Automatyczne ponowne proby polaczenia z modelem (exponential backoff), "
         "walidacja odpowiedzi LLM, czytelne kody HTTP w przypadku bledow."),
    ]
    elems.append(info_table(features, col_widths=[4.5 * cm, 13 * cm]))
    elems.append(sp())
    return elems


# ---------------------------------------------------------------------------
# Section 2
# ---------------------------------------------------------------------------

def section_arch():
    elems = []
    elems.append(Paragraph("2. Architektura techniczna", h1))
    elems.append(section_rule())
    elems.append(Paragraph(
        "Aplikacja sklada sie z dwoch niezaleznych punktow wejscia korzystajacych "
        "ze wspolnej warstwy logiki biznesowej:",
        body))
    elems.append(sp(4))

    arch = [
        ["Modul",          "Plik",              "Opis"],
        ["Gradio UI",      "ui/gradio_app.py",  "3-zakladkowy interfejs webowy; importuje app/ bezposrednio"],
        ["FastAPI App",    "app/main.py",        "REST API; 5 endpointow; lifespan init_db()"],
        ["Agent AI",       "app/agent.py",       "analyze_meal() -> Ollama; retry; JSON parse + walidacja"],
        ["Baza danych",    "app/database.py",    "SQLite przez run_in_executor (non-blocking)"],
        ["Modele",         "app/models.py",      "Pydantic v2: MealRequest, MealRecord, DailySummary"],
    ]
    at = Table(arch, colWidths=[3.5 * cm, 4.5 * cm, 9.5 * cm])
    at.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR",      (0, 0), (-1, 0), WHITE),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#dce1e7")),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    elems.append(at)

    elems.append(Paragraph("Endpointy REST API", h2))
    api_rows = [
        ["Metoda", "Sciezka",       "Opis",                                    "Kod"],
        ["POST",   "/meals",        "Analiza i zapis posilku -> MealRecord",   "201"],
        ["GET",    "/meals",        "Lista posilkow (?date=YYYY-MM-DD)",        "200"],
        ["GET",    "/meals/{id}",   "Pojedynczy posilek po ID",                "200/404"],
        ["GET",    "/summary",      "Agregowane makroskladniki dla dnia",      "200/404"],
        ["GET",    "/health",       "Health-check",                            "200"],
    ]
    api_t = Table(api_rows, colWidths=[2.0 * cm, 4.0 * cm, 9.0 * cm, 2.5 * cm])
    api_t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR",      (0, 0), (-1, 0), WHITE),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#dce1e7")),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 7),
        ("ALIGN",          (0, 0), (0, -1), "CENTER"),
        ("ALIGN",          (3, 0), (3, -1), "CENTER"),
    ]))
    elems.append(api_t)
    elems.append(sp())
    return elems


# ---------------------------------------------------------------------------
# Section 3
# ---------------------------------------------------------------------------

def section_tech():
    elems = []
    elems.append(Paragraph("3. Zastosowane technologie", h1))
    elems.append(section_rule())

    tech = [
        ["Warstwa",             "Technologia",          "Wersja",   "Rola"],
        ["Model AI",            "Ollama + llama3.2",    "3.2",      "Lokalny LLM; analiza opisow posilkow"],
        ["Backend API",         "FastAPI",              "0.135.1",  "REST API, walidacja, obsluga bledow"],
        ["Interfejs uzytk.",    "Gradio",               "6.9.0",    "3-zakladkowy interfejs webowy"],
        ["Baza danych",         "SQLite (stdlib)",      ">=3.12",   "Lokalne przechowywanie posilkow"],
        ["Walidacja danych",    "Pydantic v2",          "2.12.5",   "Modele wejscia/wyjscia, schematy API"],
        ["Klient HTTP",         "httpx",                "0.28.1",   "Komunikacja z Ollama (async, retry)"],
        ["ASGI server",         "Uvicorn",              "0.42.0",   "Serwer HTTP dla FastAPI"],
        ["Testy",               "pytest + asyncio",     "9.0.2",    "Testy jednostkowe i integracyjne"],
        ["Jezyk",               "Python",               "3.14",     "Caly stack backendowy"],
    ]
    tt = Table(tech, colWidths=[3.5 * cm, 4.2 * cm, 2.3 * cm, 7.5 * cm])
    tt.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR",      (0, 0), (-1, 0), WHITE),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#dce1e7")),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    elems.append(tt)
    elems.append(sp())
    return elems


# ---------------------------------------------------------------------------
# Section 4 – Raport z postepu
# ---------------------------------------------------------------------------

def section_progress():
    elems = []
    elems.append(Paragraph("4. Raport z postepu prac", h1))
    elems.append(section_rule())

    elems.append(Paragraph("4.1  Co sie udalo", h2))
    done = [
        ("OK  Pelna implementacja backendu",
         "FastAPI + SQLite + agent Ollama z retry logic i walidacja JSON."),
        ("OK  Interfejs Gradio — wersja NutriMind",
         "Przeprojektowany UI z ciemnym/jasnym motywem, wykresy SVG "
         "pierścieniowe dla celow makroskladnikow, przewijalna historia posilkow."),
        ("OK  Zestaw testow automatycznych",
         "24 testy (test_api.py, test_agent.py, test_database.py) — "
         "wszystkie przechodza; izolacja przez tmp_path SQLite."),
        ("OK  System celow uzytkownika",
         "Dzienne limity kalorii / bialka / weglowodanow / tluszczow "
         "persystowane w settings.json."),
        ("OK  Dokumentacja",
         "CLAUDE.md z mapa architektury i komendami dewelopera; "
         "README.md z instrukcja uruchomienia."),
        ("OK  Skrypty startowe",
         "Katalog scripts/ z dedykowanymi skryptami uruchomienia API i UI."),
    ]
    for title, desc in done:
        elems.append(Paragraph("<b>" + title + "</b> — " + desc, bullet))
    elems.append(sp(6))

    elems.append(Paragraph("4.2  Co jest jeszcze w planach", h2))
    todo = [
        ("O  Usuwanie posilkow przez API",
         "Funkcja delete_meal() istnieje w database.py, ale endpoint "
         "DELETE /meals/{id} nie zostal jeszcze dodany do FastAPI."),
        ("O  Edycja wartosci odzywczych",
         "Brak mozliwosci recznej korekty wartosci zwroconych przez LLM."),
        ("O  Eksport danych",
         "Planowany eksport historii do CSV/PDF."),
        ("O  Wykresy tygodniowe/miesieczne",
         "Trendy kalorii w czasie — pomysl na rozszerzenie UI."),
    ]
    for title, desc in todo:
        elems.append(Paragraph("<b>" + title + "</b> — " + desc, bullet))
    elems.append(sp(6))

    elems.append(Paragraph("4.3  Zmiany wzgledem wstepnej koncepcji", h2))
    changes = [
        ("Zmiana",    "UI",
         "Wstepnie planowano prosta 3-zakladkowa aplikacje Gradio. W trakcie "
         "implementacji UI zostalo calkowicie przeprojektowane — dodano motyw "
         "NutriMind z ciemnym/jasnym trybem, wykresy SVG pierścieniowe, "
         "konfiguracje celow oraz usunieto sztuczne ograniczenie 6 posilkow "
         "na liscie."),
        ("Zmiana",    "Obsluga bledow",
         "Dodano znacznie bardziej rozbudowana obsluge bledow niz planowano: "
         "exponential backoff przy retry, walidacja wartosci ujemnych i "
         "nierealistycznych (ponad 10 000 kcal), weryfikacja pustej nazwy posilku."),
        ("Dodane",    "Prompt inzynieryjny",
         "System prompt wzbogacono o tablice referencyjną porcji, przyklady "
         "wejscie/wyjscie (PL i EN) oraz instrukcje cross-check kalorii "
         "wzgledem makroskladnikow (wzor: kcal = P*4 + W*4 + T*9)."),
        ("Bez zmian", "Stack technologiczny",
         "Wszystkie technologie z wstepnego opisu zostaly zachowane "
         "(FastAPI, Gradio, Ollama, SQLite, Pydantic v2, httpx, pytest)."),
    ]
    ch_data = [[Paragraph("<b>" + t + "</b>", body_left),
                Paragraph("<b>" + n + "</b>", body_left),
                Paragraph(d, body)]
               for t, n, d in changes]
    ch_t = Table(ch_data, colWidths=[2.5 * cm, 3.2 * cm, 11.8 * cm])
    ch_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PANEL]),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#dce1e7")),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    elems.append(ch_t)
    elems.append(sp(6))

    elems.append(Paragraph("4.4  Napotkane problemy i ich rozwiazania", h2))

    problems = [
        (
            "Problem z asyncio w Gradio",
            "Gradio 6.x nie obsluguje bezposrednio natywnych async def handlerow — "
            "wywolanie asyncio.run() wewnatrz handlera powodowalo nieskonczoný spinner. "
            "<b>Rozwiazanie:</b> zadeklarowanie handlerow jako async def "
            "(Gradio sam zarzadza petla zdarzen).",
        ),
        (
            "Model owijal JSON w znaczniki Markdown",
            "llama3.2 sporadycznie zwaraca odpowiedz w blokach ```json ... ``` zamiast "
            "czystego JSON. <b>Rozwiazanie:</b> regex stripujacy code fences przed parsowaniem.",
        ),
        (
            "Blokowanie event loop FastAPI przez SQLite",
            "Synchroniczne API sqlite3 blokowaloby asyncio event loop. "
            "<b>Rozwiazanie:</b> wszystkie operacje DB owieto w loop.run_in_executor(None, ...).",
        ),
        (
            "Izolacja testow — wspolna baza danych",
            "Testy bez izolacji nadpisywaly sie wzajemnie. "
            "<b>Rozwiazanie:</b> unittest.mock.patch('app.database.DB_PATH', tmp_path/'test.db') "
            "w kazdym tescie.",
        ),
    ]
    for title, desc in problems:
        elems.append(KeepTogether([
            Paragraph("<b>" + title + "</b>", h3),
            Paragraph(desc, body),
        ]))

    elems.append(Paragraph("4.5  Organizacja pracy w zespole", h2))
    elems.append(Paragraph(
        "Projekt realizowany jest przez dwie osoby. Wspolpraca opiera sie na "
        "repozytorium GitHub z modelem feature-branch + Pull Request:",
        body))
    collab = [
        ("Michal Boese (102218)",
         "Architektura backendu (app/), integracja z Ollama, system testow, "
         "skrypty startowe, dokumentacja CLAUDE.md i README."),
        ("Adam Rekruciak (102487)",
         "Interfejs uzytkownika Gradio (ui/gradio_app.py), projekt graficzny "
         "UI, system celow makroskladnikow, wykresy SVG."),
    ]
    elems.append(info_table(collab, col_widths=[4.5 * cm, 13 * cm]))
    elems.append(sp(4))
    git_stats = [
        ("Galaz glowna",           "main"),
        ("Lacznie commitow",       "11  (od 89bdfee do 23aa66d)"),
        ("Merge PR",               "#1 — scalenie galezi claude/kind-lovelace do main"),
        ("Strategia",              "Feature branches -> Pull Request -> code review -> merge"),
    ]
    elems.append(info_table(git_stats, col_widths=[4.5 * cm, 13 * cm]))
    elems.append(sp())
    return elems


# ---------------------------------------------------------------------------
# Section 5 – Fragmenty kodu / zrzuty ekranu
# ---------------------------------------------------------------------------

def section_code():
    elems = []
    elems.append(Paragraph("5. Fragmenty kodu i odpowiedz z API", h1))
    elems.append(section_rule())

    # 5.1 System prompt
    elems.append(Paragraph("5.1  System prompt agenta (app/agent.py)", h2))
    elems.append(Paragraph(
        "Prompt instruuje model do zwracania wylacznie czystego JSON, "
        "zawiera tabele referencyjną typowych porcji oraz wymog weryfikacji "
        "krzyzowej kalorii wzgledem makroskladnikow:",
        body))
    elems.append(sp(4))
    elems.append(code_block([
        'SYSTEM_PROMPT = """',
        'You are a precise nutrition analysis assistant.',
        '',
        'RULES:',
        '- Respond ONLY with a valid JSON object.',
        '- If a weight is specified, use it. Otherwise assume a standard adult serving.',
        '- meal_name MUST be in the SAME LANGUAGE as the user input.',
        '',
        'PORTION REFERENCE:',
        '- plate of pasta  = ~250g cooked (~350 kcal)',
        '- chicken breast  = ~150g (~165 kcal, 31g protein)',
        '- egg             = ~50g  (~70 kcal, 6g protein, 5g fat)',
        '',
        'CROSS-CHECK: calories = (protein*4) + (carbs*4) + (fat*9). Adjust if >15%.',
        '',
        'Required JSON format:',
        '  {"meal_name": "...", "calories": int, "protein": float,',
        '   "carbs": float, "fat": float}',
        '"""',
    ]))
    elems.append(sp(10))

    # 5.2 Retry logic
    elems.append(Paragraph("5.2  Mechanizm retry z exponential backoff (app/agent.py)", h2))
    elems.append(code_block([
        'async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:',
        '    for attempt in range(OLLAMA_RETRIES):',
        '        try:',
        '            response = await client.post(OLLAMA_URL, json=payload)',
        '            response.raise_for_status()',
        '            break',
        '        except (httpx.ConnectError, httpx.TimeoutException) as exc:',
        '            last_exc = exc',
        '            if attempt < OLLAMA_RETRIES - 1:',
        '                await asyncio.sleep(OLLAMA_RETRY_DELAY * (2 ** attempt))',
        '    else:',
        '        raise last_exc   # wszystkie proby wyczerpane',
    ]))
    elems.append(sp(10))

    # 5.3 Przykladowa odpowiedz API
    elems.append(Paragraph("5.3  Przykladowa odpowiedz POST /meals", h2))
    elems.append(Paragraph(
        "Zapytanie: POST /meals  "
        "body: {description: owsianka z bananem i lyzka masla orzechowego}",
        body))
    elems.append(sp(4))
    elems.append(code_block([
        'HTTP/1.1 201 Created',
        'Content-Type: application/json',
        '',
        '{',
        '  "id": 42,',
        '  "description": "owsianka z bananem i lyzka masla orzechowego",',
        '  "meal_name": "Owsianka z bananem i maslem orzechowym",',
        '  "calories": 420,',
        '  "protein": 12.5,',
        '  "carbs": 62.0,',
        '  "fat": 13.0,',
        '  "created_at": "2026-04-02T09:15:03"',
        '}',
    ]))
    elems.append(sp(10))

    # 5.4 Schemat bazy
    elems.append(Paragraph("5.4  Schemat bazy danych SQLite (app/database.py)", h2))
    elems.append(code_block([
        'CREATE TABLE IF NOT EXISTS meals (',
        '    id          INTEGER PRIMARY KEY AUTOINCREMENT,',
        '    description TEXT    NOT NULL,   -- oryginalny opis uzytkownika',
        '    meal_name   TEXT    NOT NULL,   -- nazwa z modelu LLM',
        '    calories    INTEGER NOT NULL,',
        '    protein     REAL    NOT NULL,',
        '    carbs       REAL    NOT NULL,',
        '    fat         REAL    NOT NULL,',
        '    created_at  TEXT    NOT NULL    -- ISO 8601 UTC',
        ')',
    ]))
    elems.append(sp(10))

    # 5.5 Git log
    elems.append(Paragraph("5.5  Historia commitow repozytorium (git log --oneline)", h2))
    elems.append(code_block([
        '$ git log --oneline',
        '23aa66d fix(ui): show all meals with scrollable list, remove 6-item cap',
        '3a65d80 fix(ui): replace asyncio.run() with async handlers',
        '77135cd feat(ui): add macro goals with SVG ring charts',
        '537c40f feat(ui): rebuild frontend as NutriMind with dark/light theme',
        '356858a feat: add startup scripts for API and UI',
        '0d1b069 docs: add README with setup and run instructions',
        '67a7a6a Merge pull request #1 from michalboese/claude/kind-lovelace',
        '5a254cf fix: harden error handling, validation, and resilience',
        'd5e7c19 chore: add pytest-asyncio==1.3.0 to requirements.txt',
        'a898943 docs: add CLAUDE.md with architecture and dev commands',
        '89bdfee feat: initial implementation of calorie agent',
    ]))
    elems.append(sp(10))

    # 5.6 Testy
    elems.append(Paragraph("5.6  Wyniki testow automatycznych (pytest)", h2))
    elems.append(code_block([
        '$ pytest --tb=no -q',
        '........................                              [100%]',
        '24 passed in 0.67s',
        '',
        '# Pokrycie plikow testami:',
        '#   tests/test_api.py       -- endpointy FastAPI (mock Ollama)',
        '#   tests/test_agent.py     -- parsowanie JSON, walidacja wartosci',
        '#   tests/test_database.py  -- CRUD SQLite (izolacja tmp_path)',
    ]))
    elems.append(sp())
    return elems


# ---------------------------------------------------------------------------
# Section 6 – Integracja zewnetrzna
# ---------------------------------------------------------------------------

def section_integration():
    elems = []
    elems.append(Paragraph("6. Integracja z systemami zewnetrznymi", h1))
    elems.append(section_rule())

    elems.append(Paragraph(
        "NutriMind korzysta wylacznie z <b>lokalnego modelu jezykowego</b> — "
        "nie integruje sie z zadna platna usluga API w chmurze.",
        body))

    elems.append(Paragraph("6.1  Ollama (lokalny runtime LLM)", h2))
    ollama = [
        ("Typ integracji",       "Lokalny serwer HTTP na porcie 11434 (localhost)"),
        ("Endpoint",             "POST http://localhost:11434/api/chat"),
        ("Model",                "llama3.2 (pobierany jednorazowo: ollama pull llama3.2)"),
        ("Koszt",                "Bezplatny — oprogramowanie open-source (MIT). Brak limitow zapytan."),
        ("Wymagania sprzet.",    "Min. 8 GB RAM; dziala na CPU (bez GPU). Zalecane 16 GB."),
        ("Prywatnosc",           "Wszystkie dane przetwarzane lokalnie — zaden opis posilku "
                                 "nie opuszcza komputera uzytkownika."),
        ("Dostep do Internetu",  "Wymagany jednorazowo do pobrania modelu (~2 GB). "
                                 "Pozniejsze dzialanie — w pelni offline."),
    ]
    elems.append(info_table(ollama, col_widths=[4.5 * cm, 13 * cm]))

    elems.append(Paragraph("6.2  Konfiguracja zmiennych srodowiskowych", h2))
    elems.append(Paragraph(
        "Wszystkie parametry integracji mozna nadpisac przez zmienne srodowiskowe "
        "(wartosci domyslne w nawiasach):",
        body))
    elems.append(sp(4))
    elems.append(code_block([
        'OLLAMA_URL          # adres API Ollama    (http://localhost:11434/api/chat)',
        'OLLAMA_MODEL        # nazwa modelu        (llama3.2)',
        'OLLAMA_RETRIES      # liczba prob retry   (3)',
        'OLLAMA_RETRY_DELAY  # opoznienie bazowe   (1.0 s, wykladnicze)',
        'OLLAMA_TIMEOUT      # timeout zapytania   (60.0 s)',
    ]))

    elems.append(Paragraph("6.3  Brak zewnetrznych uslug platnych", h2))
    elems.append(Paragraph(
        "Projekt celowo rezygnuje z komercyjnych API (OpenAI, Anthropic, Google) "
        "na rzecz lokalnego modelu, co eliminuje koszty operacyjne, limity zapytan "
        "oraz potrzebe zarzadzania kluczami API. "
        "Jedynym wymaganym zasobem zewnetrznym jest jednorazowe pobranie pliku "
        "modelu (~2 GB dla llama3.2) przez narzedzie Ollama.",
        body))

    elems.append(sp())
    return elems


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build():
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="NutriMind - Opis projektu cz. 2",
        author="Michal Boese, Adam Rekruciak",
    )
    story = []
    story += cover_page()
    story += section_temat()
    story += section_arch()
    story += section_tech()
    story += section_progress()
    story += section_code()
    story += section_integration()
    doc.build(story)
    print("PDF saved:", OUTPUT)


if __name__ == "__main__":
    build()
