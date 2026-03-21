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

def run(coro):
    return asyncio.run(coro)


def format_meals_table(meals: list[dict]) -> list[list]:
    rows = []
    for m in meals:
        rows.append([
            m["id"],
            m["created_at"][:16].replace("T", " "),
            m["meal_name"],
            m["description"][:60] + ("…" if len(m["description"]) > 60 else ""),
            m["calories"],
            f'{m["protein"]:.1f}',
            f'{m["carbs"]:.1f}',
            f'{m["fat"]:.1f}',
        ])
    return rows


# ---------------------------------------------------------------------------
# Tab: Log meal
# ---------------------------------------------------------------------------

def handle_analyze(description: str):
    description = description.strip()
    if not description:
        return (
            gr.update(value="Wprowadź opis posiłku. / Please enter a meal description.", visible=True),
            gr.update(visible=False),
        )
    try:
        analysis = run(analyze_meal(description))
        run(save_meal(description, analysis))
    except Exception as e:
        return (
            gr.update(value=f"Błąd / Error: {e}", visible=True),
            gr.update(visible=False),
        )

    result_md = f"""
### {analysis['meal_name']}

| | |
|---|---|
| Kalorie | **{analysis['calories']} kcal** |
| Białko  | {analysis['protein']:.1f} g |
| Węglowodany | {analysis['carbs']:.1f} g |
| Tłuszcze | {analysis['fat']:.1f} g |
"""
    return (
        gr.update(value="", visible=False),
        gr.update(value=result_md, visible=True),
    )


# ---------------------------------------------------------------------------
# Tab: History
# ---------------------------------------------------------------------------

def handle_load_history(filter_date: str):
    date_str = filter_date.strip() or None
    try:
        meals = run(get_meals(for_date=date_str))
    except Exception as e:
        return [], f"Błąd / Error: {e}"
    return format_meals_table(meals), f"{len(meals)} posiłk{'ów' if len(meals) != 1 else ''} znaleziono."


# ---------------------------------------------------------------------------
# Tab: Daily summary
# ---------------------------------------------------------------------------

def handle_summary(summary_date: str):
    date_str = summary_date.strip() or None
    try:
        s = run(get_daily_summary(for_date=date_str))
    except Exception as e:
        return f"Błąd / Error: {e}"
    if not s:
        label = date_str or date.today().isoformat()
        return f"Brak posiłków dla {label}. / No meals found for {label}."

    return f"""
## Podsumowanie: {s['date']}

| | |
|---|---|
| Posiłki | {s['meal_count']} |
| Kalorie | **{s['total_calories']} kcal** |
| Białko  | {s['total_protein']:.1f} g |
| Węglowodany | {s['total_carbs']:.1f} g |
| Tłuszcze | {s['total_fat']:.1f} g |
"""


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

with gr.Blocks(title="Calorie Agent") as demo:
    gr.Markdown("# 🥗 Calorie Agent\nOpisz posiłek po polsku lub angielsku — agent wyliczy kalorie i makroskładniki.")

    with gr.Tab("Dodaj posiłek"):
        with gr.Row():
            with gr.Column(scale=2):
                description_input = gr.Textbox(
                    label="Opis posiłku",
                    placeholder="np. owsianka z bananem i łyżką masła orzechowego",
                    lines=3,
                )
                analyze_btn = gr.Button("Analizuj", variant="primary")
            with gr.Column(scale=2):
                error_box = gr.Markdown(visible=False)
                result_box = gr.Markdown(visible=False)

        analyze_btn.click(
            fn=handle_analyze,
            inputs=description_input,
            outputs=[error_box, result_box],
        )

    with gr.Tab("Historia"):
        with gr.Row():
            history_date = gr.Textbox(
                label="Filtruj po dacie (YYYY-MM-DD, opcjonalnie)",
                placeholder=date.today().isoformat(),
                scale=2,
            )
            load_btn = gr.Button("Wczytaj", scale=1)
        history_status = gr.Markdown()
        history_table = gr.Dataframe(
            headers=["ID", "Data", "Posiłek", "Opis", "kcal", "Białko g", "Węgl. g", "Tłuszcz g"],
            datatype=["number", "str", "str", "str", "number", "str", "str", "str"],
            interactive=False,
        )

        load_btn.click(
            fn=handle_load_history,
            inputs=history_date,
            outputs=[history_table, history_status],
        )

    with gr.Tab("Podsumowanie dnia"):
        with gr.Row():
            summary_date = gr.Textbox(
                label="Data (YYYY-MM-DD, domyślnie dziś)",
                placeholder=date.today().isoformat(),
                scale=2,
            )
            summary_btn = gr.Button("Sprawdź", scale=1)
        summary_output = gr.Markdown()

        summary_btn.click(
            fn=handle_summary,
            inputs=summary_date,
            outputs=summary_output,
        )


if __name__ == "__main__":
    asyncio.run(init_db())
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())
