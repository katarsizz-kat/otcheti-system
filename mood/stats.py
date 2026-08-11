"""
Скрытая статистика за месяц.

Открывается кнопкой «Показать статистику»:
- карточки: частая эмоция, средняя интенсивность, записи, паузы
- «узор месяца» из цветных точек
- игровые достижения
- совместный блок пары
"""

import streamlit as st

from mood import db
from mood.config import PERSON_EMOJI, PERSONS, get_mood_data
from mood.calendar import _month_options, _parse_month


# ============================================================
# HTML-БЛОКИ
# ============================================================

def _stat_card(emoji: str, value, label: str) -> str:
    """Одна карточка показателя."""
    return (
        '<div class="mood-stat-card">'
        f'<div class="mood-stat-emoji">{emoji}</div>'
        f'<div class="mood-stat-value">{value}</div>'
        f'<div class="mood-stat-label">{label}</div>'
        '</div>'
    )


def _person_stats_html(year: int, month: int, person: str) -> str:
    """Сетка карточек статистики по одному человеку."""
    stats = db.get_month_stats(year, month, person)

    top = stats["top_mood"]
    top_html = f"{get_mood_data(top)['emoji']} {top}" if top else "—"

    cards = [
        _stat_card("🎭", top_html, "частая эмоция"),
        _stat_card(
            "🔥",
            f"{stats['avg_intensity']}/5",
            "средняя интенсивность",
        ),
        _stat_card("📝", stats["total_entries"], "записей"),
        _stat_card("🌫", stats["pause_days"], "пауз"),
    ]
    return f'<div class="mood-stats-grid">{"".join(cards)}</div>'


def _pattern_html(year: int, month: int, person: str) -> str:
    """«Узор месяца»: точка на каждый день."""
    pattern = db.get_month_pattern(year, month, person)

    dots = []
    for item in pattern:
        if item["pause"]:
            color = "#d0d0d0"
            label = "без ответа"
        elif item["mood"]:
            data = get_mood_data(item["mood"])
            color = data["color"]
            label = f"{data['emoji']} {item['mood']}"
        else:
            color = "rgba(0, 0, 0, 0.06)"
            label = "нет записей"

        dots.append(
            f'<span class="mood-pattern-dot" '
            f'style="background:{color}" '
            f'title="{item["date"]}: {label}"></span>'
        )

    return (
        f'<div class="mood-pattern-container">'
        f'{"".join(dots)}</div>'
    )


def _render_achievements(year: int, month: int, person: str) -> None:
    """Достижения человека за месяц."""
    earned = db.get_achievements(year, month, person)

    if not earned:
        st.caption("Пока без достижений — и это нормально 🌱")
        return

    for ach in earned:
        st.markdown(
            f"""
            <div class="mood-achievement">
                <div class="mood-achievement-emoji">
                    {ach['emoji']}
                </div>
                <div>
                    <div class="mood-achievement-title">
                        {ach['title']}
                    </div>
                    <div class="mood-achievement-desc">
                        {ach['description']}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def render_stats() -> None:
    """Рендерит блок статистики (скрыт до нажатия кнопки)."""
    st.markdown("### 📊 Статистика")

    # Кнопка-переключатель
    if st.button(
        "📊 Показать статистику за месяц",
        key="mood_stats_toggle",
    ):
        st.session_state["mood_stats_open"] = (
            not st.session_state.get("mood_stats_open", False)
        )

    if not st.session_state.get("mood_stats_open"):
        return

    # Выбор месяца
    options = _month_options()
    month_option = st.selectbox(
        "Месяц",
        options,
        index=len(options) - 1,
        key="mood_stats_month",
    )
    year, month = _parse_month(month_option)

    # Блоки по каждому человеку
    for person in PERSONS:
        emoji = PERSON_EMOJI[person]
        st.markdown(f"#### {emoji} {person}")

        st.markdown(
            _person_stats_html(year, month, person),
            unsafe_allow_html=True,
        )

        st.caption(f"Узор месяца — {person}:")
        st.markdown(
            _pattern_html(year, month, person),
            unsafe_allow_html=True,
        )

        st.caption("Достижения:")
        _render_achievements(year, month, person)
        st.markdown("---")

    # Совместный блок пары
    info = db.get_shared_info(year, month)
    st.markdown(
        f"""
        <div class="mood-card">
            💞 Дней, когда отмечали обе:
            <b>{len(info['both_days'])}</b><br>
            ✨ Из них с совпавшим настроением:
            <b>{len(info['matched_days'])}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )