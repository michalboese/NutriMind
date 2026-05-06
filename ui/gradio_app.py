import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import functools
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


def _history_status_html(meals, ds):
    n = len(meals)
    if not n:
        return ""
    label = f"dla {ds}" if ds else "\u0142\u0105cznie"
    return f'<div class="nm-info">\U0001F4CB Znaleziono {n} posi\u0142k\u00f3w {label}</div>'


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


def _meal_row_inner_html(m):
    return (
        f'<div class="nm-row-content">'
        f'<div class="nm-row-left">'
        f'<div class="nm-row-name">{m["meal_name"]}</div>'
        f'<div class="nm-row-time">{m["created_at"][11:16]}</div>'
        f'</div>'
        f'<div class="nm-row-pills">'
        f'<span class="nm-pill nm-p-cal">{m["calories"]} kcal</span>'
        f'<span class="nm-pill nm-p-pro">B {m["protein"]:.0f}g</span>'
        f'<span class="nm-pill nm-p-carb">W {m["carbs"]:.0f}g</span>'
        f'<span class="nm-pill nm-p-fat">T {m["fat"]:.0f}g</span>'
        f'</div>'
        f'</div>'
    )


def _history_row_inner_html(m):
    desc = m["description"][:60] + ("\u2026" if len(m["description"]) > 60 else "")
    when = m["created_at"][:16].replace("T", " ")
    return (
        f'<div class="nm-row-content">'
        f'<div class="nm-row-left">'
        f'<div class="nm-row-name">{m["meal_name"]}</div>'
        f'<div class="nm-row-time">{when} \u00b7 {desc}</div>'
        f'</div>'
        f'<div class="nm-row-pills">'
        f'<span class="nm-pill nm-p-cal">{m["calories"]} kcal</span>'
        f'<span class="nm-pill nm-p-pro">B {m["protein"]:.0f}g</span>'
        f'<span class="nm-pill nm-p-carb">W {m["carbs"]:.0f}g</span>'
        f'<span class="nm-pill nm-p-fat">T {m["fat"]:.0f}g</span>'
        f'</div>'
        f'</div>'
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

async def handle_analyze(description, current_meals):
    desc = description.strip()
    if not desc:
        return (
            gr.update(value='<div class="nm-err">\u26a0\ufe0f Wprowad\u017a opis posi\u0142ku.</div>', visible=True),
            gr.update(visible=False),
            gr.update(),
            current_meals,
            gr.update(value=""),
        )
    try:
        analysis = await analyze_meal(desc)
        await save_meal(desc, analysis)
    except Exception as e:
        return (
            gr.update(value=f'<div class="nm-err">\u26a0\ufe0f B\u0142\u0105d: {e}</div>', visible=True),
            gr.update(visible=False),
            gr.update(),
            current_meals,
            gr.update(),
        )
    goals = load_goals()
    today = date.today().isoformat()
    summary = await get_daily_summary(for_date=today)
    recent = await get_meals(for_date=today)
    return (
        gr.update(value="", visible=False),
        gr.update(value=build_result_html(analysis), visible=True),
        gr.update(value=build_stats_html(summary, goals)),
        recent,
        gr.update(value=""),
    )


async def handle_history(filter_date):
    ds = filter_date.strip() if filter_date else None
    try:
        meals = await get_meals(for_date=ds or None)
    except Exception as e:
        return (
            [],
            f'<div class="nm-err">B\u0142\u0105d: {e}</div>',
        )
    return (
        meals,
        _history_status_html(meals, ds),
    )


async def load_dashboard():
    goals = load_goals()
    today = date.today().isoformat()
    summary = await get_daily_summary(for_date=today)
    recent = await get_meals(for_date=today)
    return (
        build_stats_html(summary, goals),
        recent,
    )


async def go_dash():
    stats, recent = await load_dashboard()
    return (
        gr.update(visible=True), gr.update(visible=False), gr.update(visible=False),
        stats, recent,
    )


async def go_hist():
    meals, status = await handle_history("")
    return (
        gr.update(visible=False), gr.update(visible=True), gr.update(visible=False),
        meals, status,
    )


async def go_settings():
    goals = load_goals()
    return (
        gr.update(visible=False), gr.update(visible=False), gr.update(visible=True),
        goals["calories"], goals["protein"], goals["carbs"], goals["fat"],
    )


async def handle_delete_meal(mid):
    await delete_meal(mid)
    goals = load_goals()
    today = date.today().isoformat()
    summary = await get_daily_summary(for_date=today)
    recent = await get_meals(for_date=today)
    return (
        build_stats_html(summary, goals),
        recent,
    )


async def handle_delete_history(mid, filter_date):
    await delete_meal(mid)
    ds = filter_date.strip() if filter_date else None
    meals = await get_meals(for_date=ds or None)
    today = date.today().isoformat()
    today_meals = await get_meals(for_date=today)
    summary = await get_daily_summary(for_date=today)
    goals = load_goals()
    return (
        meals,
        _history_status_html(meals, ds),
        today_meals,
        build_stats_html(summary, goals),
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
/* ─────────────────────────────────────────────────────────────
   Theme tokens — single source of truth for all colors.
   ───────────────────────────────────────────────────────────── */
:root {
    --bg:   #0d1117;
    --surf: #161b22;
    --card: #161b22;
    --elev: #1c2230;
    --brd:  #30363d;
    --hover: rgba(255,255,255,.05);
    --row-hover: rgba(255,255,255,.025);

    --txt: #e6edf3;
    --mut: #8b949e;

    --acc:  #3fb950;
    --acc2: #56d364;
    --cal:  #f97316;
    --pro:  #3fb950;
    --carb: #58a6ff;
    --fat:  #f0c24b;
    --err:  #ff7b72;

    --cal-bg:  rgba(249,115,22,.14);
    --pro-bg:  rgba(63,185,80,.14);
    --carb-bg: rgba(88,166,255,.14);
    --fat-bg:  rgba(240,194,75,.14);
    --acc-bg:  rgba(63,185,80,.10);
    --acc-ring:rgba(63,185,80,.18);
    --err-bg:  rgba(248,81,73,.10);
    --err-brd: rgba(248,81,73,.28);
    --info-bg: rgba(88,166,255,.08);
    --info-brd:rgba(88,166,255,.22);

    --r:  12px;
    --rs: 8px;
}

:root.nm-light {
    --bg:   #f6f8fa;
    --surf: #ffffff;
    --card: #ffffff;
    --elev: #f3f4f6;
    --brd:  #d0d7de;
    --hover: rgba(0,0,0,.06);
    --row-hover: rgba(0,0,0,.03);

    --txt: #1f2328;
    --mut: #4b5563;

    --acc:  #1a7f37;
    --acc2: #2da44e;
    --cal:  #b45309;
    --pro:  #1a7f37;
    --carb: #0552a0;
    --fat:  #92670a;
    --err:  #b91c1c;

    --cal-bg:  rgba(180,83,9,.12);
    --pro-bg:  rgba(26,127,55,.12);
    --carb-bg: rgba(5,82,160,.12);
    --fat-bg:  rgba(146,103,10,.14);
    --acc-bg:  rgba(26,127,55,.10);
    --acc-ring:rgba(26,127,55,.20);
    --err-bg:  rgba(185,28,28,.10);
    --err-brd: rgba(185,28,28,.28);
    --info-bg: rgba(5,82,160,.08);
    --info-brd:rgba(5,82,160,.24);
}

/* Override Gradio's internal theme variables so all built-in
   widgets inherit our palette automatically. */
:root, :root.nm-light {
    --body-background-fill: var(--bg);
    --background-fill-primary: var(--bg);
    --background-fill-secondary: var(--surf);
    --block-background-fill: transparent;
    --block-border-color: transparent;
    --block-border-width: 0;
    --panel-background-fill: transparent;
    --block-label-background-fill: transparent;
    --block-label-text-color: var(--mut);
    --block-title-text-color: var(--mut);
    --block-info-text-color: var(--mut);
    --input-background-fill: var(--surf);
    --input-background-fill-focus: var(--surf);
    --input-border-color: var(--brd);
    --input-border-color-focus: var(--acc);
    --input-text-size: 13px;
    --body-text-color: var(--txt);
    --body-text-color-subdued: var(--mut);
    --color-accent: var(--acc);
    --color-accent-soft: var(--acc-bg);
    --border-color-primary: var(--brd);
    --border-color-accent: var(--acc);
    --button-secondary-background-fill: var(--surf);
    --button-secondary-background-fill-hover: var(--elev);
    --button-secondary-text-color: var(--txt);
    --button-secondary-border-color: var(--brd);
    --neutral-50:  var(--surf);
    --neutral-100: var(--surf);
    --neutral-200: var(--brd);
    --shadow-drop: none;
    --shadow-drop-lg: none;
}

/* ─────────────────────────────────────────────────────────────
   Base layout — flatten Gradio wrappers, set one bg.
   ───────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
html, body { background: var(--bg); color: var(--txt); }

.gradio-container,
.gradio-container > .main,
.gradio-container .contain,
.app {
    background: var(--bg) !important;
    max-width: 100% !important;
    padding: 0 !important;
    color: var(--txt) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, "Helvetica Neue", sans-serif !important;
}
footer { display: none !important; }

/* Reset every Gradio block/form/wrap so they don't paint extra layers */
.gradio-container .block,
.gradio-container .form,
.gradio-container .wrap,
.gradio-container .panel,
.gradio-container [class*="block-"],
.gradio-container .gap {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* ─────────────────────────────────────────────────────────────
   Sidebar
   ───────────────────────────────────────────────────────────── */
aside, [class*="sidebar"] {
    background: var(--surf) !important;
    border-right: 1px solid var(--brd) !important;
}
.nm-brand { padding: 18px 16px 14px; border-bottom: 1px solid var(--brd); }
.nm-brand-row { display: flex; align-items: center; gap: 10px; }
.nm-brand-logo {
    flex-shrink: 0; border-radius: 10px;
    box-shadow: 0 2px 8px var(--acc-ring); display: block;
}
.nm-brand-name {
    font-size: 18px; font-weight: 800; letter-spacing: -.3px;
    color: var(--acc); line-height: 1.1; white-space: nowrap;
}
.nm-brand-tag {
    font-size: 11px; color: var(--mut); margin-top: 8px;
    line-height: 1.3; word-wrap: break-word;
}
@supports (-webkit-background-clip: text) or (background-clip: text) {
    .nm-brand-name {
        background-image: linear-gradient(135deg, var(--acc) 0%, var(--carb) 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }
}

.nm-nav { padding: 10px 8px !important; gap: 2px !important; }
.nm-nav button {
    width: 100% !important; text-align: left !important;
    background: transparent !important; border: none !important;
    border-left: 3px solid transparent !important;
    border-radius: 0 var(--rs) var(--rs) 0 !important;
    color: var(--mut) !important;
    font-size: 13px !important; font-weight: 500 !important;
    padding: 9px 12px !important; margin: 0 !important;
    box-shadow: none !important;
    transition: background .15s, color .15s, border-color .15s !important;
    cursor: pointer !important; justify-content: flex-start !important;
}
.nm-nav button:hover { background: var(--hover) !important; color: var(--txt) !important; }
.nm-nav-active button {
    background: var(--acc-bg) !important; color: var(--acc) !important;
    border-left-color: var(--acc) !important; font-weight: 600 !important;
}

.nm-theme-wrap { border-top: 1px solid var(--brd); padding: 10px 8px 12px; margin-top: 6px; }
.nm-theme-wrap button {
    width: 100% !important; background: transparent !important;
    border: 1px solid var(--brd) !important; border-radius: var(--rs) !important;
    color: var(--mut) !important; font-size: 12px !important; padding: 7px !important;
    box-shadow: none !important;
    transition: border-color .15s, color .15s, background .15s !important;
    cursor: pointer !important;
}
.nm-theme-wrap button:hover {
    border-color: var(--acc) !important; color: var(--acc) !important;
    background: var(--acc-bg) !important;
}

/* ─────────────────────────────────────────────────────────────
   Main area
   ───────────────────────────────────────────────────────────── */
.nm-main {
    padding: 20px 24px 28px !important;
    background: var(--bg) !important;
    min-height: 100vh;
}
.nm-header { margin-bottom: 16px; }
.nm-title { font-size: 22px; font-weight: 700; color: var(--txt); line-height: 1.1;
    letter-spacing: -.3px; }
.nm-sub { font-size: 12px; color: var(--mut); margin-top: 4px; }

/* ─────────────────────────────────────────────────────────────
   Stats cards
   ───────────────────────────────────────────────────────────── */
.nm-stats {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 14px; margin-bottom: 14px;
}
.nm-card {
    background: var(--card); border: 1px solid var(--brd);
    border-radius: var(--r); padding: 14px 16px;
    position: relative; overflow: hidden;
    transition: border-color .15s, transform .15s;
}
.nm-card:hover { border-color: var(--mut); }
.nm-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
.nm-card-cal::before  { background: var(--cal); }
.nm-card-pro::before  { background: var(--pro); }
.nm-card-carb::before { background: var(--carb); }
.nm-card-fat::before  { background: var(--fat); }
.nm-card-top {
    font-size: 10px; font-weight: 600; color: var(--mut);
    text-transform: uppercase; letter-spacing: .5px; margin-bottom: 10px;
}
.nm-card-body { display: flex; align-items: center; gap: 12px; }
.nm-card-val { font-size: 22px; font-weight: 700; color: var(--txt); line-height: 1; }
.nm-unit { font-size: 12px; font-weight: 400; color: var(--mut); }
.nm-card-goal { font-size: 10px; color: var(--mut); margin-top: 4px; }

/* ─────────────────────────────────────────────────────────────
   Sections (panels)
   ───────────────────────────────────────────────────────────── */
.nm-section {
    background: var(--card) !important;
    border: 1px solid var(--brd) !important;
    border-radius: var(--r) !important;
    padding: 16px !important;
}
.nm-section-title {
    font-size: 11px; font-weight: 600; color: var(--mut);
    text-transform: uppercase; letter-spacing: .5px; margin-bottom: 12px;
}

/* ─────────────────────────────────────────────────────────────
   Form inputs — defeat the browser-default greys & UA text colors.
   ───────────────────────────────────────────────────────────── */
.gradio-container input[type="text"],
.gradio-container input[type="number"],
.gradio-container input[type="search"],
.gradio-container textarea,
.gradio-container select {
    background: var(--surf) !important;
    background-color: var(--surf) !important;
    border: 1px solid var(--brd) !important;
    border-radius: var(--rs) !important;
    color: var(--txt) !important;
    -webkit-text-fill-color: var(--txt) !important;
    font-size: 13px !important;
    transition: border-color .15s, box-shadow .15s !important;
    color-scheme: inherit;
}
.gradio-container input:focus,
.gradio-container textarea:focus,
.gradio-container select:focus {
    border-color: var(--acc) !important;
    box-shadow: 0 0 0 3px var(--acc-ring) !important;
    outline: none !important;
}
.gradio-container input::placeholder,
.gradio-container textarea::placeholder {
    color: var(--mut) !important;
    -webkit-text-fill-color: var(--mut) !important;
    opacity: 1 !important;
}

/* Labels — force full text color so they're always legible. */
.gradio-container label,
.gradio-container label *,
.gradio-container .label-wrap,
.gradio-container .label-wrap *,
.gradio-container [class*="label-wrap"],
.gradio-container [class*="label-wrap"] *,
.gradio-container [data-testid*="label"],
.gradio-container [data-testid*="label"] * {
    color: var(--txt) !important;
    -webkit-text-fill-color: var(--txt) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}

/* ─────────────────────────────────────────────────────────────
   Dashboard row layout
   ───────────────────────────────────────────────────────────── */
.nm-dash-row { gap: 14px !important; align-items: stretch !important; }
.nm-dash-row > .nm-section {
    min-width: 0;
    display: flex !important;
    flex-direction: column !important;
    min-height: 360px;
}

/* ─────────────────────────────────────────────────────────────
   Buttons
   ───────────────────────────────────────────────────────────── */
.nm-cta button {
    background: var(--acc) !important; color: #fff !important;
    border: none !important; border-radius: var(--rs) !important;
    font-weight: 600 !important; font-size: 13px !important;
    padding: 10px 22px !important; box-shadow: none !important;
    transition: background .15s, transform .05s !important;
    cursor: pointer !important;
}
.nm-cta button:hover  { background: var(--acc2) !important; }
.nm-cta button:active { transform: translateY(1px); }

.nm-sec button {
    background: var(--surf) !important;
    border: 1px solid var(--brd) !important;
    border-radius: var(--rs) !important;
    color: var(--txt) !important;
    font-size: 13px !important; padding: 8px 16px !important;
    box-shadow: none !important;
    transition: border-color .15s, color .15s !important;
}
.nm-sec button:hover { border-color: var(--acc) !important; color: var(--acc) !important; }

/* ─────────────────────────────────────────────────────────────
   Result banner
   ───────────────────────────────────────────────────────────── */
.nm-result {
    border: 1px solid var(--acc-ring); background: var(--acc-bg);
    border-radius: var(--rs); padding: 12px 14px; margin-top: 10px;
}
.nm-result-name { font-size: 14px; font-weight: 600; color: var(--acc); margin-bottom: 10px; }
.nm-result-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 6px; }
.nm-ri { text-align: center; padding: 8px 4px;
    background: var(--surf); border: 1px solid var(--brd); border-radius: var(--rs); }
.nm-ri-v { font-size: 16px; font-weight: 700; color: var(--txt); }
.nm-ri-l { font-size: 9px; color: var(--mut); margin-top: 2px;
    text-transform: uppercase; letter-spacing: .3px; }
.nm-ri-cal  .nm-ri-v { color: var(--cal); }
.nm-ri-pro  .nm-ri-v { color: var(--pro); }
.nm-ri-carb .nm-ri-v { color: var(--carb); }
.nm-ri-fat  .nm-ri-v { color: var(--fat); }

/* ─────────────────────────────────────────────────────────────
   Meal list
   ───────────────────────────────────────────────────────────── */
.nm-meal-list {
    max-height: 320px !important;
    overflow-y: auto !important;
    scrollbar-width: thin;
    scrollbar-color: var(--brd) transparent;
    padding: 0 !important;
    gap: 0 !important;
}
.nm-meal-list::-webkit-scrollbar { width: 4px; }
.nm-meal-list::-webkit-scrollbar-thumb { background: var(--brd); border-radius: 2px; }
.nm-hist-list { max-height: 560px !important; }

.nm-meal-row {
    align-items: center !important;
    padding: 8px 0 !important;
    border-bottom: 1px solid var(--brd) !important;
    gap: 8px !important;
    flex-wrap: nowrap !important;
    margin: 0 !important;
}
.nm-meal-row:last-child { border-bottom: none !important; }
.nm-meal-row-html { flex: 1 !important; min-width: 0 !important; }

.nm-row-content {
    display: flex; justify-content: space-between; align-items: center;
    gap: 8px; min-width: 0;
}
.nm-row-left  { flex: 1; min-width: 0; }
.nm-row-name  { font-size: 13px; font-weight: 500; color: var(--txt);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nm-row-time  { font-size: 11px; color: var(--mut); margin-top: 2px; }
.nm-row-pills { display: flex; gap: 4px; align-items: center; flex-shrink: 0; flex-wrap: wrap;
    justify-content: flex-end; }
.nm-pill { font-size: 10px; padding: 2px 7px; border-radius: 20px;
    font-weight: 500; white-space: nowrap; }
.nm-p-cal  { background: var(--cal-bg);  color: var(--cal);  }
.nm-p-pro  { background: var(--pro-bg);  color: var(--pro);  }
.nm-p-carb { background: var(--carb-bg); color: var(--carb); }
.nm-p-fat  { background: var(--fat-bg);  color: var(--fat);  }

.nm-row-trash button {
    background: transparent !important;
    border: 1px solid var(--brd) !important;
    color: var(--mut) !important;
    font-size: 14px !important;
    line-height: 1 !important;
    padding: 0 !important;
    width: 36px !important;
    height: 32px !important;
    min-width: 36px !important;
    border-radius: var(--rs) !important;
    box-shadow: none !important;
    cursor: pointer !important;
    transition: border-color .15s, color .15s, background .15s !important;
    margin: 0 !important;
}
.nm-row-trash button:hover {
    border-color: var(--err) !important;
    color: var(--err) !important;
    background: var(--err-bg) !important;
}

/* ─────────────────────────────────────────────────────────────
   Settings status message (shared for "saved" confirmations)
   ───────────────────────────────────────────────────────────── */
.nm-del-msg { font-size: 11px; color: var(--mut); display: block; min-height: 16px; margin-top: 4px; }
.nm-del-ok  { color: var(--acc); }

/* ─────────────────────────────────────────────────────────────
   Settings
   ───────────────────────────────────────────────────────────── */
.nm-goals-row { gap: 12px !important; }

/* ─────────────────────────────────────────────────────────────
   Utility blocks
   ───────────────────────────────────────────────────────────── */
.nm-err {
    padding: 9px 12px; background: var(--err-bg);
    border: 1px solid var(--err-brd); border-radius: var(--rs);
    color: var(--err); font-size: 12px; margin-top: 8px;
}
.nm-info {
    padding: 7px 12px; background: var(--info-bg);
    border: 1px solid var(--info-brd); border-radius: var(--rs);
    color: var(--carb); font-size: 11px; margin-bottom: 8px;
}
.nm-empty { text-align: center; padding: 28px 12px; color: var(--mut); font-size: 13px; }

/* ─────────────────────────────────────────────────────────────
   Responsive
   ───────────────────────────────────────────────────────────── */
@media (max-width: 1100px) {
    .nm-stats { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 860px) {
    .nm-main { padding: 16px !important; }
    .nm-dash-row { flex-direction: column !important; }
    .nm-dash-row > div { width: 100% !important; }
    .nm-goals-row { flex-wrap: wrap !important; }
    .nm-goals-row > * { flex: 1 1 calc(50% - 6px) !important; min-width: 130px !important; }
}
@media (max-width: 560px) {
    .nm-stats { grid-template-columns: 1fr; }
    .nm-result-grid { grid-template-columns: repeat(2, 1fr); }
    .nm-row-content { flex-direction: column; align-items: flex-start; gap: 6px; }
    .nm-row-pills { width: 100%; justify-content: flex-start; }
}
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

    with gr.Sidebar(open=True, width=220):
        gr.HTML(
            '<div class="nm-brand">'
            '<div class="nm-brand-row">'
            '<svg class="nm-brand-logo" viewBox="0 0 40 40" width="36" height="36" aria-hidden="true">'
            '<defs><linearGradient id="nmg" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0%" stop-color="#3fb950"/>'
            '<stop offset="100%" stop-color="#58a6ff"/>'
            '</linearGradient></defs>'
            '<rect x="2" y="2" width="36" height="36" rx="10" fill="url(#nmg)"/>'
            '<path d="M13 26c0-7 4-12 14-13-1 9-6 13-13 13-1 0-1 0-1 0z" '
            'fill="#fff" opacity=".95"/>'
            '<path d="M13 27c2-4 5-7 11-9" stroke="#fff" stroke-width="1.4" '
            'stroke-linecap="round" fill="none" opacity=".55"/>'
            '</svg>'
            '<span class="nm-brand-name">NutriMind</span>'
            '</div>'
            '<div class="nm-brand-tag">\u015aledzenie kalorii AI</div>'
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
                meals_state_dash = gr.State([])

                @gr.render(inputs=[meals_state_dash])
                def render_dash_meals(meals):
                    if not meals:
                        gr.HTML(
                            '<div class="nm-empty">Brak posi\u0142k\u00f3w dzisiaj \u2014 '
                            'dodaj pierwszy posi\u0142ek obok \u27a1</div>'
                        )
                        return
                    with gr.Column(elem_classes=["nm-meal-list"]):
                        for m in meals:
                            with gr.Row(elem_classes=["nm-meal-row"]):
                                gr.HTML(
                                    _meal_row_inner_html(m),
                                    elem_classes=["nm-meal-row-html"],
                                )
                                with gr.Column(
                                    scale=0, min_width=44, elem_classes=["nm-row-trash"]
                                ):
                                    del_btn = gr.Button("\U0001F5D1\ufe0f")
                                del_btn.click(
                                    fn=functools.partial(handle_delete_meal, m["id"]),
                                    outputs=[stats_out, meals_state_dash],
                                )

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
            hist_state = gr.State([])

            @gr.render(inputs=[hist_state])
            def render_hist_meals(meals):
                if not meals:
                    gr.HTML('<div class="nm-empty">Brak posi\u0142k\u00f3w.</div>')
                    return
                with gr.Column(elem_classes=["nm-meal-list", "nm-hist-list"]):
                    for m in meals:
                        with gr.Row(elem_classes=["nm-meal-row"]):
                            gr.HTML(
                                _history_row_inner_html(m),
                                elem_classes=["nm-meal-row-html"],
                            )
                            with gr.Column(
                                scale=0, min_width=44, elem_classes=["nm-row-trash"]
                            ):
                                del_btn = gr.Button("\U0001F5D1\ufe0f")
                            del_btn.click(
                                fn=functools.partial(handle_delete_history, m["id"]),
                                inputs=[hist_date],
                                outputs=[hist_state, hist_status, meals_state_dash, stats_out],
                            )

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
        inputs=[meal_input, meals_state_dash],
        outputs=[error_out, result_out, stats_out, meals_state_dash, meal_input],
    )
    btn_dash.click(
        fn=go_dash,
        outputs=[page_dash, page_hist, page_settings, stats_out, meals_state_dash],
    )
    btn_hist.click(
        fn=go_hist,
        outputs=[page_dash, page_hist, page_settings, hist_state, hist_status],
    )
    btn_settings_nav.click(
        fn=go_settings,
        outputs=[page_dash, page_hist, page_settings, goal_cal, goal_pro, goal_carb, goal_fat],
    )
    btn_filter.click(
        fn=handle_history,
        inputs=[hist_date],
        outputs=[hist_state, hist_status],
    )
    btn_save.click(
        fn=handle_save_goals,
        inputs=[goal_cal, goal_pro, goal_carb, goal_fat],
        outputs=[settings_status],
    )
    btn_theme.click(fn=None, js=THEME_JS)
    demo.load(fn=load_dashboard, outputs=[stats_out, meals_state_dash])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Base(), css=CSS, js=JS)
