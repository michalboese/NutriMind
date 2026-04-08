import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
from datetime import date

import gradio as gr

from app.agent import analyze_meal
from app.database import delete_meal, get_daily_summary, get_meals, init_db, save_meal


# ---------------------------------------------------------------------------
# Settings persistence
# ---------------------------------------------------------------------------

SETTINGS_PATH = Path(__file__).parent.parent / "settings.json"
DEFAULT_GOALS = {"calories": 2000, "protein": 150, "carbs": 250, "fat": 70}


def load_goals():
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return {k: data.get(k, DEFAULT_GOALS[k]) for k in DEFAULT_GOALS}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return DEFAULT_GOALS.copy()


def save_goals_to_file(goals):
    SETTINGS_PATH.write_text(json.dumps(goals, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _meal_count_label(n):
    if n == 1:
        return "1 posi\u0142ek"
    if 2 <= n <= 4:
        return f"{n} posi\u0142ki"
    return f"{n} posi\u0142k\u00f3w"


def _meal_choices(meals):
    return [
        (f"{m['meal_name']}  \u2014  {m['calories']} kcal  ({m['created_at'][11:16]})", str(m['id']))
        for m in meals
    ]


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

def _ring(pct, color):
    r, sw = 28, 5
    circ = 2 * 3.14159 * r
    fill = min(pct / 100 * circ, circ)
    gap = circ - fill
    return (
        f'<svg width="68" height="68" viewBox="0 0 68 68">'
        f'<circle cx="34" cy="34" r="{r}" fill="none" stroke="var(--brd)" stroke-width="{sw}"/>'
        f'<circle cx="34" cy="34" r="{r}" fill="none" stroke="{color}" stroke-width="{sw}" '
        f'stroke-dasharray="{fill:.1f} {gap:.1f}" stroke-linecap="round" '
        f'transform="rotate(-90 34 34)"/>'
        f'<text x="34" y="38" text-anchor="middle" font-size="11" font-weight="700" '
        f'fill="{color}" font-family="inherit">{pct}%</text>'
        f'</svg>'
    )


def build_stats_html(summary, goals=None):
    goals = goals or load_goals()
    s = summary or {
        "total_calories": 0, "total_protein": 0.0,
        "total_carbs": 0.0, "total_fat": 0.0, "meal_count": 0,
    }
    today_str = date.today().strftime("%A, %d %B %Y")

    pct_cal  = min(100, round(s["total_calories"] / max(goals["calories"], 1) * 100))
    pct_pro  = min(100, round(s["total_protein"]  / max(goals["protein"], 1)  * 100))
    pct_carb = min(100, round(s["total_carbs"]    / max(goals["carbs"], 1)    * 100))
    pct_fat  = min(100, round(s["total_fat"]      / max(goals["fat"], 1)      * 100))

    def _card(cls, emoji, label, ring, val, unit, goal_val, goal_unit):
        return (
            f'<div class="nm-card {cls}">'
            f'<div class="nm-card-top">{emoji} {label}</div>'
            f'<div class="nm-card-body">{ring}'
            f'<div><div class="nm-card-val">{val}<span class="nm-unit"> {unit}</span></div>'
            f'<div class="nm-card-goal">cel: {goal_val} {goal_unit}</div></div>'
            f'</div></div>'
        )

    cards = (
        _card("nm-card-cal", "\U0001F525", "Kalorie",
              _ring(pct_cal, "#f97316"),
              s["total_calories"], "kcal", goals["calories"], "kcal")
        + _card("nm-card-pro", "\U0001F4AA", "Bia\u0142ko",
                _ring(pct_pro, "#3fb950"),
                f'{s["total_protein"]:.1f}', "g", goals["protein"], "g")
        + _card("nm-card-carb", "\U0001F33E", "W\u0119glowodany",
                _ring(pct_carb, "#58a6ff"),
                f'{s["total_carbs"]:.1f}', "g", goals["carbs"], "g")
        + _card("nm-card-fat", "\U0001F951", "T\u0142uszcze",
                _ring(pct_fat, "#f0c24b"),
                f'{s["total_fat"]:.1f}', "g", goals["fat"], "g")
    )

    return (
        f'<div class="nm-header">'
        f'<div class="nm-title">Dashboard</div>'
        f'<div class="nm-sub">{today_str} &middot; {_meal_count_label(s["meal_count"])}</div>'
        f'</div>'
        f'<div class="nm-stats">{cards}</div>'
    )


def build_recent_html(meals):
    if not meals:
        return '<div class="nm-empty">Brak posi\u0142k\u00f3w dzisiaj \u2014 dodaj pierwszy posi\u0142ek obok \u27a1</div>'
    rows = "".join(
        f'<div class="nm-row">'
        f'<div class="nm-row-left">'
        f'<div class="nm-row-name">{m["meal_name"]}</div>'
        f'<div class="nm-row-time">{m["created_at"][11:16]}</div>'
        f'</div>'
        f'<div class="nm-row-pills">'
        f'<span class="nm-pill nm-p-cal">{m["calories"]} kcal</span>'
        f'<span class="nm-pill nm-p-pro">B {m["protein"]:.0f}g</span>'
        f'<span class="nm-pill nm-p-carb">W {m["carbs"]:.0f}g</span>'
        f'<span class="nm-pill nm-p-fat">T {m["fat"]:.0f}g</span>'
        f'</div></div>'
        for m in meals
    )
    return f'<div class="nm-meal-list">{rows}</div>'


def build_history_html(meals):
    if not meals:
        return '<div class="nm-empty">Brak posi\u0142k\u00f3w.</div>'
    rows = ""
    for m in meals:
        desc = m["description"][:60] + ("\u2026" if len(m["description"]) > 60 else "")
        rows += (
            f'<tr>'
            f'<td class="nm-td">{m["created_at"][:16].replace("T", " ")}</td>'
            f'<td class="nm-td nm-td-name">{m["meal_name"]}</td>'
            f'<td class="nm-td nm-td-desc">{desc}</td>'
            f'<td class="nm-td nm-td-r">{m["calories"]}</td>'
            f'<td class="nm-td nm-td-r">{m["protein"]:.1f}</td>'
            f'<td class="nm-td nm-td-r">{m["carbs"]:.1f}</td>'
            f'<td class="nm-td nm-td-r">{m["fat"]:.1f}</td>'
            f'</tr>'
        )
    return (
        '<div class="nm-table-wrap">'
        '<table class="nm-table">'
        '<thead><tr>'
        '<th class="nm-th">Data</th>'
        '<th class="nm-th">Posi\u0142ek</th>'
        '<th class="nm-th">Opis</th>'
        '<th class="nm-th nm-th-r">kcal</th>'
        '<th class="nm-th nm-th-r">Bia\u0142ko</th>'
        '<th class="nm-th nm-th-r">W\u0119gle</th>'
        '<th class="nm-th nm-th-r">T\u0142uszcze</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody>'
        '</table></div>'
    )


def build_result_html(a):
    return (
        '<div class="nm-result">'
        f'<div class="nm-result-name">\u2705 {a["meal_name"]}</div>'
        '<div class="nm-result-grid">'
        f'<div class="nm-ri nm-ri-cal"><div class="nm-ri-v">{a["calories"]}</div><div class="nm-ri-l">kcal</div></div>'
        f'<div class="nm-ri nm-ri-pro"><div class="nm-ri-v">{a["protein"]:.1f}</div><div class="nm-ri-l">bia\u0142ko g</div></div>'
        f'<div class="nm-ri nm-ri-carb"><div class="nm-ri-v">{a["carbs"]:.1f}</div><div class="nm-ri-l">w\u0119gle g</div></div>'
        f'<div class="nm-ri nm-ri-fat"><div class="nm-ri-v">{a["fat"]:.1f}</div><div class="nm-ri-l">t\u0142uszcze g</div></div>'
        '</div></div>'
    )


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

async def handle_analyze(description):
    desc = description.strip()
    if not desc:
        return (
            gr.update(value='<div class="nm-err">\u26a0\ufe0f Wprowad\u017a opis posi\u0142ku.</div>', visible=True),
            gr.update(visible=False),
            gr.update(), gr.update(), gr.update(), gr.update(value=""),
        )
    try:
        analysis = await analyze_meal(desc)
        await save_meal(desc, analysis)
    except Exception as e:
        return (
            gr.update(value=f'<div class="nm-err">\u26a0\ufe0f B\u0142\u0105d: {e}</div>', visible=True),
            gr.update(visible=False),
            gr.update(), gr.update(), gr.update(), gr.update(),
        )
    goals = load_goals()
    today = date.today().isoformat()
    summary = await get_daily_summary(for_date=today)
    recent = await get_meals(for_date=today)
    return (
        gr.update(value="", visible=False),
        gr.update(value=build_result_html(analysis), visible=True),
        gr.update(value=build_stats_html(summary, goals)),
        gr.update(value=build_recent_html(recent)),
        gr.update(choices=_meal_choices(recent), value=None),
        gr.update(value=""),
    )


async def handle_history(filter_date):
    ds = filter_date.strip() if filter_date else None
    try:
        meals = await get_meals(for_date=ds or None)
    except Exception as e:
        return (
            f'<div class="nm-err">B\u0142\u0105d: {e}</div>',
            "",
            gr.update(choices=[], value=None),
        )
    n = len(meals)
    if n:
        label = f"dla {ds}" if ds else "\u0142\u0105cznie"
        status = f'<div class="nm-info">\U0001F4CB Znaleziono {n} posi\u0142k\u00f3w {label}</div>'
    else:
        status = ""
    return (
        build_history_html(meals),
        status,
        gr.update(choices=_meal_choices(meals), value=None),
    )


async def load_dashboard():
    goals = load_goals()
    today = date.today().isoformat()
    summary = await get_daily_summary(for_date=today)
    recent = await get_meals(for_date=today)
    return (
        build_stats_html(summary, goals),
        build_recent_html(recent),
        gr.update(choices=_meal_choices(recent), value=None),
    )


async def go_dash():
    stats, recent, dd = await load_dashboard()
    return (
        gr.update(visible=True), gr.update(visible=False), gr.update(visible=False),
        stats, recent, dd,
    )


async def go_hist():
    html, status, dd = await handle_history("")
    return (
        gr.update(visible=False), gr.update(visible=True), gr.update(visible=False),
        html, status, dd,
    )


async def go_settings():
    goals = load_goals()
    return (
        gr.update(visible=False), gr.update(visible=False), gr.update(visible=True),
        goals["calories"], goals["protein"], goals["carbs"], goals["fat"],
    )


async def handle_delete_dash(selected):
    if not selected:
        return (
            gr.update(), gr.update(), gr.update(),
            '<span class="nm-del-msg">Wybierz posi\u0142ek z listy.</span>',
        )
    mid = int(selected)
    deleted = await delete_meal(mid)
    if not deleted:
        return (
            gr.update(), gr.update(), gr.update(),
            '<span class="nm-del-msg nm-del-err">Nie znaleziono posi\u0142ku.</span>',
        )
    goals = load_goals()
    today = date.today().isoformat()
    summary = await get_daily_summary(for_date=today)
    recent = await get_meals(for_date=today)
    return (
        gr.update(value=build_stats_html(summary, goals)),
        gr.update(value=build_recent_html(recent)),
        gr.update(choices=_meal_choices(recent), value=None),
        '<span class="nm-del-msg nm-del-ok">\u2713 Usuni\u0119to posi\u0142ek.</span>',
    )


async def handle_delete_hist(selected, hist_date):
    if not selected:
        return (
            gr.update(), gr.update(), gr.update(),
            '<span class="nm-del-msg">Wybierz posi\u0142ek z listy.</span>',
        )
    mid = int(selected)
    deleted = await delete_meal(mid)
    if not deleted:
        return (
            gr.update(), gr.update(), gr.update(),
            '<span class="nm-del-msg nm-del-err">Nie znaleziono posi\u0142ku.</span>',
        )
    html, status, dd = await handle_history(hist_date or "")
    return (
        html, status, dd,
        '<span class="nm-del-msg nm-del-ok">\u2713 Usuni\u0119to posi\u0142ek.</span>',
    )


async def handle_save_goals(cal, pro, carb, fat):
    goals = {
        "calories": int(cal) if cal is not None else DEFAULT_GOALS["calories"],
        "protein": int(pro) if pro is not None else DEFAULT_GOALS["protein"],
        "carbs": int(carb) if carb is not None else DEFAULT_GOALS["carbs"],
        "fat": int(fat) if fat is not None else DEFAULT_GOALS["fat"],
    }
    save_goals_to_file(goals)
    return '<span class="nm-del-msg nm-del-ok">\u2713 Cele zapisane. Dashboard od\u015bwie\u017cy si\u0119 po przej\u015bciu.</span>'


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """
:root {
    --bg: #0d1117; --surf: #161b22; --card: #1c2333; --brd: #30363d;
    --acc: #3fb950; --acc2: #56d364; --txt: #e6edf3; --mut: #8b949e;
    --cal: #f97316; --pro: #3fb950; --carb: #58a6ff; --fat: #f0c24b;
    --r: 12px; --rs: 8px;
}
:root.nm-light {
    --bg: #f6f8fa; --surf: #ffffff; --card: #ffffff; --brd: #d0d7de;
    --acc: #1a7f37; --acc2: #2da44e; --txt: #1f2328; --mut: #656d76;
}

/* Base */
.gradio-container { background: var(--bg) !important; max-width: 100% !important; padding: 0 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif !important; }
footer { display: none !important; }
.app { background: var(--bg) !important; }

/* Sidebar */
aside, [class*="sidebar"] { background: var(--surf) !important; border-right: 1px solid var(--brd) !important; }
.nm-brand { padding: 18px 16px 14px; border-bottom: 1px solid var(--brd); }
.nm-brand-name { font-size: 20px; font-weight: 800;
    background: linear-gradient(135deg, var(--acc), var(--carb));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; letter-spacing: -0.3px; }
.nm-brand-tag { font-size: 11px; color: var(--mut); margin-top: 3px; }
.nm-nav { padding: 10px 8px !important; gap: 2px !important; }
.nm-nav button { width: 100% !important; text-align: left !important; background: transparent !important;
    border: none !important; border-left: 3px solid transparent !important;
    border-radius: 0 var(--rs) var(--rs) 0 !important; color: var(--mut) !important;
    font-size: 13px !important; font-weight: 500 !important; padding: 9px 12px !important;
    margin: 0 !important; box-shadow: none !important; transition: all .15s !important;
    cursor: pointer !important; justify-content: flex-start !important; }
.nm-nav button:hover { background: rgba(255,255,255,.04) !important; color: var(--txt) !important; }
.nm-nav-active button { background: rgba(63,185,80,.1) !important; color: var(--acc) !important;
    border-left-color: var(--acc) !important; font-weight: 600 !important; }
.nm-theme-wrap { border-top: 1px solid var(--brd); padding-top: 10px; margin-top: 6px; }
.nm-theme-wrap button { width: 100% !important; background: transparent !important;
    border: 1px solid var(--brd) !important; border-radius: var(--rs) !important;
    color: var(--mut) !important; font-size: 12px !important; padding: 7px !important;
    box-shadow: none !important; transition: all .15s !important; cursor: pointer !important; }
.nm-theme-wrap button:hover { border-color: var(--acc) !important; color: var(--acc) !important; }

/* Main */
.nm-main { padding: 18px 24px !important; background: var(--bg) !important; }
.nm-header { margin-bottom: 14px; }
.nm-title { font-size: 21px; font-weight: 700; color: var(--txt); line-height: 1; }
.nm-sub { font-size: 12px; color: var(--mut); margin-top: 4px; }

/* Stats */
.nm-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px; }
@media(max-width:960px) { .nm-stats { grid-template-columns: repeat(2,1fr); } }
.nm-card { background: var(--card); border: 1px solid var(--brd); border-radius: var(--r);
    padding: 12px 14px; position: relative; overflow: hidden; }
.nm-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
.nm-card-cal::before { background: var(--cal); }
.nm-card-pro::before { background: var(--pro); }
.nm-card-carb::before { background: var(--carb); }
.nm-card-fat::before { background: var(--fat); }
.nm-card-top { font-size: 10px; font-weight: 600; color: var(--mut);
    text-transform: uppercase; letter-spacing: .5px; margin-bottom: 8px; }
.nm-card-body { display: flex; align-items: center; gap: 10px; }
.nm-card-val { font-size: 22px; font-weight: 700; color: var(--txt); line-height: 1; }
.nm-unit { font-size: 12px; font-weight: 400; color: var(--mut); }
.nm-card-goal { font-size: 10px; color: var(--mut); margin-top: 3px; }

/* Sections */
.nm-section { background: var(--card) !important; border: 1px solid var(--brd) !important;
    border-radius: var(--r) !important; padding: 14px 16px !important; }
.nm-section-title { font-size: 11px; font-weight: 600; color: var(--mut);
    text-transform: uppercase; letter-spacing: .5px; margin-bottom: 10px; }

/* Form inputs */
.nm-section textarea, .nm-section input[type="text"], .nm-section input[type="number"] {
    background: var(--surf) !important; border: 1px solid var(--brd) !important;
    border-radius: var(--rs) !important; color: var(--txt) !important;
    font-size: 13px !important; transition: border-color .15s, box-shadow .15s !important; }
.nm-section textarea:focus, .nm-section input:focus {
    border-color: var(--acc) !important; box-shadow: 0 0 0 3px rgba(63,185,80,.12) !important;
    outline: none !important; }
.nm-section label, .nm-section .label-wrap span {
    color: var(--mut) !important; font-size: 11px !important; font-weight: 500 !important; }
.nm-section .wrap, .nm-section .block { background: transparent !important; border: none !important; }

/* Dashboard row */
.nm-dash-row { gap: 12px !important; align-items: flex-start !important; }
.nm-dash-row > div { min-width: 0; }

/* Buttons */
.nm-cta button { background: var(--acc) !important; color: #fff !important; border: none !important;
    border-radius: var(--rs) !important; font-weight: 600 !important; font-size: 13px !important;
    padding: 9px 22px !important; box-shadow: none !important; transition: background .15s !important;
    cursor: pointer !important; }
.nm-cta button:hover { background: var(--acc2) !important; }
.nm-sec button { background: var(--surf) !important; border: 1px solid var(--brd) !important;
    border-radius: var(--rs) !important; color: var(--txt) !important; font-size: 13px !important;
    padding: 8px 16px !important; box-shadow: none !important;
    transition: border-color .15s, color .15s !important; }
.nm-sec button:hover { border-color: var(--acc) !important; color: var(--acc) !important; }
.nm-del button { background: rgba(248,81,73,.1) !important; border: 1px solid rgba(248,81,73,.25) !important;
    border-radius: var(--rs) !important; color: #ff7b72 !important; font-size: 13px !important;
    font-weight: 600 !important; padding: 8px 14px !important; box-shadow: none !important;
    transition: background .15s, border-color .15s !important; cursor: pointer !important; }
.nm-del button:hover { background: rgba(248,81,73,.2) !important; border-color: rgba(248,81,73,.5) !important; }

/* Result */
.nm-result { border: 1px solid rgba(63,185,80,.3); background: rgba(63,185,80,.06);
    border-radius: var(--rs); padding: 12px 14px; margin-top: 8px; }
.nm-result-name { font-size: 14px; font-weight: 600; color: var(--acc); margin-bottom: 10px; }
.nm-result-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 6px; }
.nm-ri { text-align: center; padding: 8px 4px; background: var(--surf);
    border: 1px solid var(--brd); border-radius: var(--rs); }
.nm-ri-v { font-size: 16px; font-weight: 700; color: var(--txt); }
.nm-ri-l { font-size: 9px; color: var(--mut); margin-top: 2px; text-transform: uppercase; letter-spacing: .3px; }
.nm-ri-cal .nm-ri-v { color: var(--cal); }
.nm-ri-pro .nm-ri-v { color: var(--pro); }
.nm-ri-carb .nm-ri-v { color: var(--carb); }
.nm-ri-fat .nm-ri-v { color: var(--fat); }

/* Meal list */
.nm-meal-list { max-height: 280px; overflow-y: auto; scrollbar-width: thin;
    scrollbar-color: var(--brd) transparent; }
.nm-meal-list::-webkit-scrollbar { width: 4px; }
.nm-meal-list::-webkit-scrollbar-thumb { background: var(--brd); border-radius: 2px; }
.nm-row { display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0; border-bottom: 1px solid var(--brd); gap: 8px; }
.nm-row:last-child { border-bottom: none; }
.nm-row-left { flex: 1; min-width: 0; }
.nm-row-name { font-size: 13px; font-weight: 500; color: var(--txt);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nm-row-time { font-size: 11px; color: var(--mut); margin-top: 1px; }
.nm-row-pills { display: flex; gap: 4px; align-items: center; flex-shrink: 0; }
.nm-pill { font-size: 10px; padding: 2px 6px; border-radius: 20px; font-weight: 500; white-space: nowrap; }
.nm-p-cal { background: rgba(249,115,22,.12); color: var(--cal); }
.nm-p-pro { background: rgba(63,185,80,.12); color: var(--pro); }
.nm-p-carb { background: rgba(88,166,255,.12); color: var(--carb); }
.nm-p-fat { background: rgba(240,194,75,.12); color: var(--fat); }

/* Delete row */
.nm-del-row { padding-top: 10px; border-top: 1px solid var(--brd); margin-top: 6px;
    gap: 6px !important; align-items: flex-end !important; }
.nm-del-row .wrap, .nm-del-row .block { background: transparent !important; border: none !important; }
.nm-del-row label, .nm-del-row .label-wrap span {
    color: var(--mut) !important; font-size: 11px !important; font-weight: 500 !important; }
.nm-del-msg { font-size: 11px; color: var(--mut); display: block; min-height: 16px; }
.nm-del-ok { color: var(--acc); }
.nm-del-err { color: #ff7b72; }

/* Dropdown overrides */
.nm-dropdown input[type="text"] { background: var(--surf) !important;
    border: 1px solid var(--brd) !important; color: var(--txt) !important;
    font-size: 12px !important; border-radius: var(--rs) !important; }
.nm-dropdown ul { background: var(--card) !important; border: 1px solid var(--brd) !important;
    border-radius: var(--rs) !important; }
.nm-dropdown li { color: var(--txt) !important; font-size: 12px !important; }
.nm-dropdown li:hover, .nm-dropdown li[class*="active"], .nm-dropdown li[aria-selected="true"] {
    background: var(--surf) !important; }
.nm-dropdown .wrap, .nm-dropdown .block { background: transparent !important; border: none !important; }

/* History table */
.nm-table-wrap { max-height: 420px; overflow-y: auto; scrollbar-width: thin;
    scrollbar-color: var(--brd) transparent; }
.nm-table-wrap::-webkit-scrollbar { width: 4px; }
.nm-table-wrap::-webkit-scrollbar-thumb { background: var(--brd); border-radius: 2px; }
.nm-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.nm-th { text-align: left; padding: 7px 8px; color: var(--mut); font-size: 10px; font-weight: 600;
    text-transform: uppercase; letter-spacing: .4px; border-bottom: 2px solid var(--brd);
    white-space: nowrap; background: var(--card); position: sticky; top: 0; z-index: 1; }
.nm-th-r { text-align: right; }
.nm-td { padding: 8px 8px; border-bottom: 1px solid var(--brd); color: var(--txt); vertical-align: middle; }
.nm-td-name { font-weight: 500; }
.nm-td-desc { color: var(--mut); font-size: 11px; max-width: 220px; }
.nm-td-r { text-align: right; font-variant-numeric: tabular-nums; }
tr:last-child .nm-td { border-bottom: none; }
tr:hover .nm-td { background: rgba(255,255,255,.02); }

/* Settings */
.nm-goals-row { gap: 10px !important; }
.nm-goals-row .wrap, .nm-goals-row .block { background: transparent !important; border: none !important; }

/* Utils */
.nm-err { padding: 8px 12px; background: rgba(248,81,73,.08); border: 1px solid rgba(248,81,73,.25);
    border-radius: var(--rs); color: #ff7b72; font-size: 12px; margin-top: 6px; }
.nm-info { padding: 6px 12px; background: rgba(88,166,255,.08); border: 1px solid rgba(88,166,255,.2);
    border-radius: var(--rs); color: var(--carb); font-size: 11px; margin-bottom: 8px; }
.nm-empty { text-align: center; padding: 24px 12px; color: var(--mut); font-size: 13px; }
"""

JS = "function(){document.documentElement.style.colorScheme='dark';}"

THEME_JS = (
    "() => {"
    "document.documentElement.classList.toggle('nm-light');"
    "document.documentElement.style.colorScheme = "
    "  document.documentElement.classList.contains('nm-light') ? 'light' : 'dark';"
    "const btn = document.querySelector('#nm-theme-btn button');"
    "if (btn) btn.textContent = document.documentElement.classList.contains('nm-light')"
    "  ? '\U0001F319  Ciemny motyw'"
    "  : '\u2600\ufe0f  Jasny motyw';"
    "}"
)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

asyncio.run(init_db())

with gr.Blocks(title="NutriMind") as demo:

    with gr.Sidebar(open=True, width=210):
        gr.HTML(
            '<div class="nm-brand">'
            '<div class="nm-brand-name">\U0001F33F NutriMind</div>'
            '<div class="nm-brand-tag">Inteligentne \u015bledzenie kalorii</div>'
            '</div>'
        )
        with gr.Column(elem_classes=["nm-nav"]):
            btn_dash = gr.Button("\U0001F3E0  Dashboard", elem_classes=["nm-nav-active"])
            btn_hist = gr.Button("\U0001F4CB  Historia")
            btn_settings_nav = gr.Button("\u2699\ufe0f  Ustawienia")
        with gr.Column(elem_classes=["nm-theme-wrap"]):
            btn_theme = gr.Button("\u2600\ufe0f  Jasny motyw", elem_id="nm-theme-btn")

    # ── Dashboard ──────────────────────────────────────────────
    with gr.Column(visible=True, elem_classes=["nm-main"]) as page_dash:
        stats_out = gr.HTML(build_stats_html(None))

        with gr.Row(elem_classes=["nm-dash-row"]):
            with gr.Column(scale=3, elem_classes=["nm-section"]):
                gr.HTML('<div class="nm-section-title">\U0001F552 Dzisiejsze posi\u0142ki</div>')
                recent_out = gr.HTML(build_recent_html([]))
                with gr.Row(elem_classes=["nm-del-row"]):
                    del_dropdown_dash = gr.Dropdown(
                        label="Posi\u0142ek do usuni\u0119cia",
                        choices=[], interactive=True, scale=3,
                        elem_classes=["nm-dropdown"],
                    )
                    with gr.Column(scale=0, min_width=90, elem_classes=["nm-del"]):
                        btn_del_dash = gr.Button("\U0001F5D1\ufe0f Usu\u0144")
                del_status_dash = gr.HTML()

            with gr.Column(scale=2, elem_classes=["nm-section"]):
                gr.HTML('<div class="nm-section-title">\u2795 Dodaj posi\u0142ek</div>')
                meal_input = gr.Textbox(
                    label="Opis posi\u0142ku",
                    placeholder="np. owsianka z bananem i mas\u0142em orzechowym, 300g...",
                    lines=2,
                )
                with gr.Column(elem_classes=["nm-cta"]):
                    btn_analyze = gr.Button("Analizuj posi\u0142ek")
                error_out = gr.HTML(visible=False)
                result_out = gr.HTML(visible=False)

    # ── Historia ───────────────────────────────────────────────
    with gr.Column(visible=False, elem_classes=["nm-main"]) as page_hist:
        gr.HTML(
            '<div class="nm-header">'
            '<div class="nm-title">Historia</div>'
            '<div class="nm-sub">Przegl\u0105daj wszystkie zapisane posi\u0142ki</div>'
            '</div>'
        )
        with gr.Column(elem_classes=["nm-section"]):
            with gr.Row():
                hist_date = gr.Textbox(
                    label="Data (YYYY-MM-DD) \u2014 puste = wszystkie",
                    placeholder=date.today().isoformat(),
                    scale=3,
                )
                with gr.Column(scale=0, min_width=100, elem_classes=["nm-sec"]):
                    btn_filter = gr.Button("Filtruj")
            hist_status = gr.HTML()
            hist_out = gr.HTML()
            with gr.Row(elem_classes=["nm-del-row"]):
                del_dropdown_hist = gr.Dropdown(
                    label="Posi\u0142ek do usuni\u0119cia",
                    choices=[], interactive=True, scale=3,
                    elem_classes=["nm-dropdown"],
                )
                with gr.Column(scale=0, min_width=90, elem_classes=["nm-del"]):
                    btn_del_hist = gr.Button("\U0001F5D1\ufe0f Usu\u0144")
            del_status_hist = gr.HTML()

    # ── Ustawienia ─────────────────────────────────────────────
    with gr.Column(visible=False, elem_classes=["nm-main"]) as page_settings:
        gr.HTML(
            '<div class="nm-header">'
            '<div class="nm-title">Ustawienia</div>'
            '<div class="nm-sub">Dostosuj dzienne cele \u017cywieniowe</div>'
            '</div>'
        )
        with gr.Column(elem_classes=["nm-section"]):
            gr.HTML('<div class="nm-section-title">\U0001F3AF Dzienne cele</div>')
            _g = load_goals()
            with gr.Row(elem_classes=["nm-goals-row"]):
                goal_cal = gr.Number(
                    label="\U0001F525 Kalorie (kcal)", value=_g["calories"], precision=0, minimum=0
                )
                goal_pro = gr.Number(
                    label="\U0001F4AA Bia\u0142ko (g)", value=_g["protein"], precision=0, minimum=0
                )
                goal_carb = gr.Number(
                    label="\U0001F33E W\u0119glowodany (g)", value=_g["carbs"], precision=0, minimum=0
                )
                goal_fat = gr.Number(
                    label="\U0001F951 T\u0142uszcze (g)", value=_g["fat"], precision=0, minimum=0
                )
            with gr.Column(elem_classes=["nm-cta"]):
                btn_save = gr.Button("\U0001F4BE Zapisz zmiany")
            settings_status = gr.HTML()

    # ── Events ─────────────────────────────────────────────────
    btn_analyze.click(
        fn=handle_analyze,
        inputs=[meal_input],
        outputs=[error_out, result_out, stats_out, recent_out, del_dropdown_dash, meal_input],
    )
    btn_dash.click(
        fn=go_dash,
        outputs=[page_dash, page_hist, page_settings, stats_out, recent_out, del_dropdown_dash],
    )
    btn_hist.click(
        fn=go_hist,
        outputs=[page_dash, page_hist, page_settings, hist_out, hist_status, del_dropdown_hist],
    )
    btn_settings_nav.click(
        fn=go_settings,
        outputs=[page_dash, page_hist, page_settings, goal_cal, goal_pro, goal_carb, goal_fat],
    )
    btn_filter.click(
        fn=handle_history,
        inputs=[hist_date],
        outputs=[hist_out, hist_status, del_dropdown_hist],
    )
    btn_del_dash.click(
        fn=handle_delete_dash,
        inputs=[del_dropdown_dash],
        outputs=[stats_out, recent_out, del_dropdown_dash, del_status_dash],
    )
    btn_del_hist.click(
        fn=handle_delete_hist,
        inputs=[del_dropdown_hist, hist_date],
        outputs=[hist_out, hist_status, del_dropdown_hist, del_status_hist],
    )
    btn_save.click(
        fn=handle_save_goals,
        inputs=[goal_cal, goal_pro, goal_carb, goal_fat],
        outputs=[settings_status],
    )
    btn_theme.click(fn=None, js=THEME_JS)
    demo.load(fn=load_dashboard, outputs=[stats_out, recent_out, del_dropdown_dash])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Base(), css=CSS, js=JS)
