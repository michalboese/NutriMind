import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import date

import gradio as gr

from app.agent import analyze_meal
from app.database import get_daily_summary, get_meals, init_db, save_meal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _meal_count_label(n):
    if n == 1:      return "1 posiłek"
    if 2 <= n <= 4: return f"{n} posiłki"
    return f"{n} posiłków"


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

GOALS = {"calories": 2000, "protein": 150, "carbs": 250, "fat": 70}


def _ring(pct: int, hex_color: str) -> str:
    """SVG donut ring showing percentage of daily goal."""
    r, sw = 34, 7
    circ = 2 * 3.14159 * r
    fill = min(pct / 100 * circ, circ)
    gap  = circ - fill
    return (
        f'<svg width="86" height="86" viewBox="0 0 86 86" style="display:block;flex-shrink:0">'
        f'<circle cx="43" cy="43" r="{r}" fill="none" stroke="var(--brd)" stroke-width="{sw}"/>'
        f'<circle cx="43" cy="43" r="{r}" fill="none" stroke="{hex_color}" stroke-width="{sw}" '
        f'stroke-dasharray="{fill:.1f} {gap:.1f}" stroke-linecap="round" '
        f'transform="rotate(-90 43 43)"/>'
        f'<text x="43" y="47" text-anchor="middle" font-size="13" font-weight="700" '
        f'fill="{hex_color}" font-family="sans-serif">{pct}%</text>'
        f'</svg>'
    )


def build_stats_html(summary):
    s = summary or {
        "total_calories": 0, "total_protein": 0.0,
        "total_carbs": 0.0, "total_fat": 0.0, "meal_count": 0,
    }
    today_str = date.today().strftime("%A, %d %B %Y")

    pct_cal  = min(100, round(s["total_calories"]       / GOALS["calories"] * 100))
    pct_pro  = min(100, round(s["total_protein"]        / GOALS["protein"]  * 100))
    pct_carb = min(100, round(s["total_carbs"]          / GOALS["carbs"]    * 100))
    pct_fat  = min(100, round(s["total_fat"]            / GOALS["fat"]      * 100))

    ring_cal  = _ring(pct_cal,  "#f97316")
    ring_pro  = _ring(pct_pro,  "#3fb950")
    ring_carb = _ring(pct_carb, "#58a6ff")
    ring_fat  = _ring(pct_fat,  "#f0c24b")

    return f"""
<div class="nm-page-header">
    <div class="nm-page-title">Dashboard</div>
    <div class="nm-page-sub">{today_str} &nbsp;&middot;&nbsp; {_meal_count_label(s['meal_count'])}</div>
</div>
<div class="nm-stats">
    <div class="nm-card nm-card-cal">
        <div class="nm-card-head">🔥 Kalorie</div>
        <div class="nm-card-body">
            {ring_cal}
            <div>
                <div class="nm-card-val">{s['total_calories']}<span class="nm-card-unit"> kcal</span></div>
                <div class="nm-card-goal">cel: {GOALS['calories']} kcal</div>
            </div>
        </div>
    </div>
    <div class="nm-card nm-card-pro">
        <div class="nm-card-head">💪 Białko</div>
        <div class="nm-card-body">
            {ring_pro}
            <div>
                <div class="nm-card-val">{s['total_protein']:.1f}<span class="nm-card-unit"> g</span></div>
                <div class="nm-card-goal">cel: {GOALS['protein']} g</div>
            </div>
        </div>
    </div>
    <div class="nm-card nm-card-carb">
        <div class="nm-card-head">🌾 Węglowodany</div>
        <div class="nm-card-body">
            {ring_carb}
            <div>
                <div class="nm-card-val">{s['total_carbs']:.1f}<span class="nm-card-unit"> g</span></div>
                <div class="nm-card-goal">cel: {GOALS['carbs']} g</div>
            </div>
        </div>
    </div>
    <div class="nm-card nm-card-fat">
        <div class="nm-card-head">🥑 Tłuszcze</div>
        <div class="nm-card-body">
            {ring_fat}
            <div>
                <div class="nm-card-val">{s['total_fat']:.1f}<span class="nm-card-unit"> g</span></div>
                <div class="nm-card-goal">cel: {GOALS['fat']} g</div>
            </div>
        </div>
    </div>
</div>"""


def build_recent_html(meals):
    if not meals:
        return '<div class="nm-empty">Brak posiłków dzisiaj &mdash; dodaj pierwszy posiłek poniżej &#128070;</div>'
    rows = "".join(f"""
<div class="nm-row">
    <div class="nm-row-left">
        <div class="nm-row-name">{m['meal_name']}</div>
        <div class="nm-row-time">{m['created_at'][11:16]}</div>
    </div>
    <div class="nm-row-right">
        <span class="nm-pill nm-pill-cal">{m['calories']} kcal</span>
        <span class="nm-pill nm-pill-pro">B {m['protein']:.0f}g</span>
        <span class="nm-pill nm-pill-carb">W {m['carbs']:.0f}g</span>
        <span class="nm-pill nm-pill-fat">T {m['fat']:.0f}g</span>
    </div>
</div>""" for m in meals)
    return f'<div class="nm-meal-list">{rows}</div>'


def build_result_html(a):
    return f"""
<div class="nm-result">
    <div class="nm-result-name">&#9989; {a['meal_name']}</div>
    <div class="nm-result-grid">
        <div class="nm-ri cal"><div class="nm-ri-v">{a['calories']}</div><div class="nm-ri-l">kcal</div></div>
        <div class="nm-ri pro"><div class="nm-ri-v">{a['protein']:.1f}</div><div class="nm-ri-l">białko g</div></div>
        <div class="nm-ri carb"><div class="nm-ri-v">{a['carbs']:.1f}</div><div class="nm-ri-l">węgle g</div></div>
        <div class="nm-ri fat"><div class="nm-ri-v">{a['fat']:.1f}</div><div class="nm-ri-l">tłuszcze g</div></div>
    </div>
</div>"""


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

async def handle_analyze(description):
    desc = description.strip()
    if not desc:
        return (
            gr.update(value='<div class="nm-error">⚠️ Wprowadź opis posiłku.</div>', visible=True),
            gr.update(visible=False),
            gr.update(), gr.update(),
        )
    try:
        analysis = await analyze_meal(desc)
        await save_meal(desc, analysis)
    except Exception as e:
        return (
            gr.update(value=f'<div class="nm-error">⚠️ Błąd: {e}</div>', visible=True),
            gr.update(visible=False),
            gr.update(), gr.update(),
        )
    today = date.today().isoformat()
    summary = await get_daily_summary(for_date=today)
    recent  = await get_meals(for_date=today)
    return (
        gr.update(value="", visible=False),
        gr.update(value=build_result_html(analysis), visible=True),
        gr.update(value=build_stats_html(summary)),
        gr.update(value=build_recent_html(recent)),
    )


async def handle_history(filter_date):
    ds = filter_date.strip() or None
    try:
        meals = await get_meals(for_date=ds)
    except Exception as e:
        return [], f'<div class="nm-error">Błąd: {e}</div>'
    rows = [
        [m["id"], m["created_at"][:16].replace("T", " "), m["meal_name"],
         m["description"][:55] + ("\u2026" if len(m["description"]) > 55 else ""),
         m["calories"], f'{m["protein"]:.1f}', f'{m["carbs"]:.1f}', f'{m["fat"]:.1f}']
        for m in meals
    ]
    count = len(meals)
    if count:
        label = f"dla {ds}" if ds else "łącznie"
        status = f'<div class="nm-info">📋 Znaleziono {count} posiłków {label}</div>'
    else:
        status = '<div class="nm-empty-inline">Brak posiłków dla podanej daty.</div>'
    return rows, status


async def load_dashboard():
    today = date.today().isoformat()
    summary = await get_daily_summary(for_date=today)
    recent  = await get_meals(for_date=today)
    return build_stats_html(summary), build_recent_html(recent)


async def go_dash():
    s, r = await load_dashboard()
    return gr.update(visible=True), gr.update(visible=False), s, r


async def go_hist():
    rows, status = await handle_history("")
    return gr.update(visible=False), gr.update(visible=True), rows, status


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = (
    ":root {"
    "--bg:#0d1117;--surf:#161b22;--card:#1c2333;--brd:#30363d;"
    "--acc:#3fb950;--acc2:#56d364;--txt:#e6edf3;--mut:#8b949e;"
    "--cal:#f97316;--pro:#3fb950;--carb:#58a6ff;--fat:#f0c24b;"
    "--r:12px;--rs:8px;"
    "}"
    ".nm-light{"
    "--bg:#f6f8fa;--surf:#fff;--card:#fff;--brd:#d0d7de;"
    "--acc:#1a7f37;--acc2:#2da44e;--txt:#1f2328;--mut:#656d76;"
    "}"
    ".gradio-container{background:var(--bg)!important;max-width:100%!important;padding:0!important;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif!important;}"
    "footer{display:none!important;}"
    ".app{background:var(--bg)!important;}"

    # Sidebar
    ".sidebar-wrap{background:var(--surf)!important;border-right:1px solid var(--brd)!important;}"
    ".nm-brand{padding:22px 18px 16px;border-bottom:1px solid var(--brd);margin-bottom:8px;}"
    ".nm-brand-name{font-size:20px;font-weight:700;color:var(--acc);letter-spacing:-.3px;}"
    ".nm-brand-tag{font-size:11px;color:var(--mut);margin-top:3px;}"

    # Nav buttons
    ".nm-nav button{width:100%!important;text-align:left!important;background:transparent!important;"
    "border:none!important;border-radius:var(--rs)!important;color:var(--mut)!important;"
    "font-size:14px!important;font-weight:500!important;padding:9px 14px!important;"
    "margin:2px 0!important;box-shadow:none!important;transition:all .15s!important;"
    "cursor:pointer!important;justify-content:flex-start!important;}"
    ".nm-nav button:hover{background:var(--card)!important;color:var(--txt)!important;}"
    ".nm-nav-active button{background:rgba(63,185,80,.12)!important;color:var(--acc)!important;}"

    # Theme toggle
    ".nm-theme-wrap{border-top:1px solid var(--brd);padding-top:12px;margin-top:8px;}"
    ".nm-theme-wrap button{width:100%!important;background:transparent!important;"
    "border:1px solid var(--brd)!important;border-radius:var(--rs)!important;"
    "color:var(--mut)!important;font-size:12px!important;padding:8px!important;"
    "box-shadow:none!important;transition:all .15s!important;cursor:pointer!important;}"
    ".nm-theme-wrap button:hover{border-color:var(--acc)!important;color:var(--acc)!important;}"

    # Main
    ".nm-main{padding:28px 32px;background:var(--bg);min-height:100vh;}"
    ".nm-page-header{margin-bottom:22px;}"
    ".nm-page-title{font-size:24px;font-weight:700;color:var(--txt);line-height:1;}"
    ".nm-page-sub{font-size:13px;color:var(--mut);margin-top:6px;}"

    # Stats
    ".nm-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px;}"
    "@media(max-width:960px){.nm-stats{grid-template-columns:repeat(2,1fr);}}"
    "@media(max-width:520px){.nm-stats{grid-template-columns:1fr;}}"
    ".nm-card{background:var(--card);border:1px solid var(--brd);border-radius:var(--r);"
    "padding:16px 18px;position:relative;overflow:hidden;}"
    ".nm-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;}"
    ".nm-card-cal::before{background:var(--cal);}"
    ".nm-card-pro::before{background:var(--pro);}"
    ".nm-card-carb::before{background:var(--carb);}"
    ".nm-card-fat::before{background:var(--fat);}"
    ".nm-card-head{display:flex;align-items:center;gap:7px;font-size:11px;font-weight:600;"
    "color:var(--mut);text-transform:uppercase;letter-spacing:.6px;margin-bottom:12px;}"
    ".nm-card-body{display:flex;align-items:center;gap:14px;}"
    ".nm-card-val{font-size:26px;font-weight:700;color:var(--txt);line-height:1;}"
    ".nm-card-unit{font-size:13px;font-weight:400;color:var(--mut);}"
    ".nm-card-goal{font-size:11px;color:var(--mut);margin-top:5px;}"

    # Sections
    ".nm-section{background:var(--card);border:1px solid var(--brd);border-radius:var(--r);"
    "padding:20px 22px;margin-bottom:16px;}"
    ".nm-section-title{font-size:12px;font-weight:600;color:var(--mut);text-transform:uppercase;"
    "letter-spacing:.5px;margin-bottom:16px;display:flex;align-items:center;gap:7px;}"
    ".nm-section textarea,.nm-section input[type=text]{background:var(--surf)!important;"
    "border:1px solid var(--brd)!important;border-radius:var(--rs)!important;"
    "color:var(--txt)!important;font-size:14px!important;line-height:1.5!important;"
    "transition:border-color .15s,box-shadow .15s!important;}"
    ".nm-section textarea:focus,.nm-section input[type=text]:focus{"
    "border-color:var(--acc)!important;box-shadow:0 0 0 3px rgba(63,185,80,.15)!important;"
    "outline:none!important;}"
    ".nm-section label,.nm-section .label-wrap span{"
    "color:var(--mut)!important;font-size:12px!important;font-weight:500!important;}"
    ".nm-section .wrap,.nm-section .block{background:transparent!important;border:none!important;}"

    # CTA
    ".nm-cta button{background:var(--acc)!important;color:#fff!important;border:none!important;"
    "border-radius:var(--rs)!important;font-weight:600!important;font-size:14px!important;"
    "padding:11px 26px!important;box-shadow:none!important;transition:background .15s!important;"
    "cursor:pointer!important;}"
    ".nm-cta button:hover{background:var(--acc2)!important;}"

    # Secondary
    ".nm-sec button{background:var(--surf)!important;border:1px solid var(--brd)!important;"
    "border-radius:var(--rs)!important;color:var(--txt)!important;font-size:13px!important;"
    "padding:9px 18px!important;box-shadow:none!important;"
    "transition:border-color .15s,color .15s!important;}"
    ".nm-sec button:hover{border-color:var(--acc)!important;color:var(--acc)!important;}"

    # Result
    ".nm-result{border:1px solid rgba(63,185,80,.3);background:rgba(63,185,80,.07);"
    "border-radius:var(--rs);padding:16px 18px;margin-top:12px;}"
    ".nm-result-name{font-size:15px;font-weight:600;color:var(--acc);margin-bottom:14px;}"
    ".nm-result-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;}"
    ".nm-ri{text-align:center;padding:12px 6px;background:var(--surf);"
    "border:1px solid var(--brd);border-radius:var(--rs);}"
    ".nm-ri-v{font-size:20px;font-weight:700;color:var(--txt);}"
    ".nm-ri-l{font-size:10px;color:var(--mut);margin-top:3px;text-transform:uppercase;letter-spacing:.4px;}"
    ".nm-ri.cal .nm-ri-v{color:var(--cal);}"
    ".nm-ri.pro .nm-ri-v{color:var(--pro);}"
    ".nm-ri.carb .nm-ri-v{color:var(--carb);}"
    ".nm-ri.fat .nm-ri-v{color:var(--fat);}"

    # Recent meals
    ".nm-meal-list{max-height:340px;overflow-y:auto;scrollbar-width:thin;"
    "scrollbar-color:var(--brd) transparent;}"
    ".nm-meal-list::-webkit-scrollbar{width:4px;}"
    ".nm-meal-list::-webkit-scrollbar-track{background:transparent;}"
    ".nm-meal-list::-webkit-scrollbar-thumb{background:var(--brd);border-radius:2px;}"
    ".nm-row{display:flex;justify-content:space-between;align-items:center;"
    "padding:11px 0;border-bottom:1px solid var(--brd);gap:12px;}"
    ".nm-row:last-child{border-bottom:none;}"
    ".nm-row-name{font-size:14px;font-weight:500;color:var(--txt);}"
    ".nm-row-time{font-size:12px;color:var(--mut);margin-top:2px;}"
    ".nm-row-right{display:flex;flex-wrap:wrap;gap:5px;align-items:center;"
    "justify-content:flex-end;flex-shrink:0;}"
    ".nm-pill{font-size:12px;padding:3px 8px;border-radius:20px;font-weight:500;white-space:nowrap;}"
    ".nm-pill-cal{background:rgba(249,115,22,.15);color:var(--cal);}"
    ".nm-pill-pro{background:rgba(63,185,80,.15);color:var(--pro);}"
    ".nm-pill-carb{background:rgba(88,166,255,.15);color:var(--carb);}"
    ".nm-pill-fat{background:rgba(240,194,75,.15);color:var(--fat);}"

    # History table
    ".nm-section thead th{color:var(--mut)!important;font-size:11px!important;"
    "font-weight:600!important;text-transform:uppercase!important;letter-spacing:.5px!important;"
    "background:var(--surf)!important;border-color:var(--brd)!important;}"
    ".nm-section tbody td{color:var(--txt)!important;border-color:var(--brd)!important;"
    "background:var(--card)!important;}"
    ".nm-section tbody tr:hover td{background:var(--surf)!important;}"

    # Utilities
    ".nm-error{padding:12px 16px;background:rgba(248,81,73,.1);"
    "border:1px solid rgba(248,81,73,.3);border-radius:var(--rs);color:#ff7b72;"
    "font-size:14px;margin-top:8px;}"
    ".nm-info{padding:8px 14px;background:rgba(88,166,255,.1);"
    "border:1px solid rgba(88,166,255,.25);border-radius:var(--rs);"
    "color:var(--carb);font-size:13px;margin-bottom:12px;}"
    ".nm-empty{text-align:center;padding:36px 16px;color:var(--mut);font-size:14px;line-height:1.6;}"
    ".nm-empty-inline{padding:16px;color:var(--mut);font-size:14px;text-align:center;}"
)

JS = "function(){ document.documentElement.style.colorScheme='dark'; }"

THEME_JS = (
    "() => {"
    "const c = document.querySelector('.gradio-container');"
    "c.classList.toggle('nm-light');"
    "const btn = document.querySelector('#nm-theme-btn button');"
    "if (btn) btn.textContent = c.classList.contains('nm-light')"
    "  ? '\U0001F319  Ciemny motyw'"
    "  : '\u2600\ufe0f  Jasny motyw';"
    "}"
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

asyncio.run(init_db())

with gr.Blocks(title="NutriMind") as demo:

    with gr.Sidebar(open=True, width=230):
        gr.HTML(
            '<div class="nm-brand">'
            '<div class="nm-brand-name">&#127957; NutriMind</div>'
            '<div class="nm-brand-tag">Inteligentne śledzenie kalorii</div>'
            '</div>'
        )
        with gr.Column(elem_classes=["nm-nav"]):
            btn_dash = gr.Button("🏠  Dashboard", elem_classes=["nm-nav-active"])
            btn_hist = gr.Button("📋  Historia")
        with gr.Column(elem_classes=["nm-theme-wrap"]):
            btn_theme = gr.Button("☀️  Jasny motyw", elem_id="nm-theme-btn")

    # ── Dashboard ─────────────────────────────────────────────────────────────
    with gr.Column(visible=True, elem_classes=["nm-main"]) as page_dash:

        stats_out = gr.HTML(build_stats_html(None))

        with gr.Column(elem_classes=["nm-section"]):
            gr.HTML('<div class="nm-section-title">🕐 Dzisiejsze posiłki</div>')
            recent_out = gr.HTML(build_recent_html([]))

        with gr.Column(elem_classes=["nm-section"]):
            gr.HTML('<div class="nm-section-title">➕ Dodaj posiłek</div>')
            meal_input = gr.Textbox(
                label="Opis posiłku",
                placeholder="np. owsianka z bananem i masłem orzechowym, 300g...",
                lines=3,
            )
            with gr.Row():
                with gr.Column(elem_classes=["nm-cta"], scale=0, min_width=170):
                    btn_analyze = gr.Button("Analizuj posiłek")
            error_out  = gr.HTML(visible=False)
            result_out = gr.HTML(visible=False)

    # ── Historia ──────────────────────────────────────────────────────────────
    with gr.Column(visible=False, elem_classes=["nm-main"]) as page_hist:
        gr.HTML(
            '<div class="nm-page-header">'
            '<div class="nm-page-title">Historia</div>'
            '<div class="nm-page-sub">Przeglądaj wszystkie zapisane posiłki</div>'
            '</div>'
        )
        with gr.Column(elem_classes=["nm-section"]):
            gr.HTML('<div class="nm-section-title">&#128269; Filtruj</div>')
            with gr.Row():
                hist_date = gr.Textbox(
                    label="Data (YYYY-MM-DD) — puste = wszystkie",
                    placeholder=date.today().isoformat(),
                    scale=3,
                )
                with gr.Column(scale=1, min_width=110, elem_classes=["nm-sec"]):
                    btn_filter = gr.Button("Filtruj")
            hist_status = gr.HTML()
            hist_table = gr.Dataframe(
                headers=["ID", "Data", "Posiłek", "Opis", "kcal", "Białko g", "Węgl. g", "Tłuszcz g"],
                datatype=["number", "str", "str", "str", "number", "str", "str", "str"],
                interactive=False,
                wrap=True,
            )

    # ── Events ────────────────────────────────────────────────────────────────
    btn_analyze.click(
        fn=handle_analyze,
        inputs=[meal_input],
        outputs=[error_out, result_out, stats_out, recent_out],
    )
    btn_dash.click(fn=go_dash,   outputs=[page_dash, page_hist, stats_out, recent_out])
    btn_hist.click(fn=go_hist,   outputs=[page_dash, page_hist, hist_table, hist_status])
    btn_filter.click(fn=handle_history, inputs=[hist_date], outputs=[hist_table, hist_status])
    btn_theme.click(fn=None, js=THEME_JS)

    demo.load(fn=load_dashboard, outputs=[stats_out, recent_out])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Base(), css=CSS, js=JS)
