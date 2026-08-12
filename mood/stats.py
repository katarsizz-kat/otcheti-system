"""
Расширенный отчёт статистики за месяц.

Блоки:
1. Сводные карточки по каждой девушке
2. 🎨 Эмоциональная палитра (разнообразие)
3. 🌈 Баланс тепла (доли категорий)
4. 📅 Ритм недели (дни недели)
5. 🕰 Время суток (части дня)
6. 🤝 Вы вдвоём (синхронность, поддержка, ресурсные дни)
7. 💬 Мягкие инсайты
8. 🕯 Пятиминутка недели (узор + вопросы для диалога)
9. 🏆 Достижения
"""

import random

import streamlit as st

from mood import db
from mood.config import (
    DAYS_OF_WEEK,
    MOOD_CATEGORIES,
    PART_EMOJI,
    PARTS_OF_DAY,
    PERSON_EMOJI,
    PERSONS,
    RITUAL_QUESTIONS,
    RITUAL_SUBTITLE,
    RITUAL_TITLE,
    get_mood_data,
)
from mood.calendar import _month_options, _parse_month


# ============================================================
# КАРТОЧКИ И УЗОРЫ
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
    """Сетка сводных карточек по одной девушке."""
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


# ============================================================
# ПАЛИТРА, БАЛАНС, РИТМЫ
# ============================================================

def _palette_html(year: int, month: int, person: str) -> str:
    """🎨 Палитра: разнообразие эмоций."""
    diversity = db.get_mood_diversity(year, month, person)

    if not diversity["moods"]:
        return (
            '<div class="mood-insight">🎨 Палитра пока пустая — '
            'записей ещё нет 🌱</div>'
        )

    emojis = " ".join(
        get_mood_data(m)["emoji"] for m in diversity["moods"]
    )
    count = diversity["count"]

    if count >= 6:
        comment = "широкая палитра — вы чувствуете во всех красках 🌈"
    elif count >= 4:
        comment = "хорошее разнообразие эмоций 🌿"
    else:
        comment = (
            "палитра узкая — проверьте, есть ли время чувствовать 🌱"
        )

    return (
        f'<div class="mood-insight">🎨 {count} разных эмоций: '
        f'{emojis}<br><span style="font-size:.85rem;">{comment}'
        f'</span></div>'
    )


def _balance_html(year: int, month: int, person: str) -> str:
    """🌈 Баланс тепла: полоса из долей категорий."""
    balance = db.get_category_balance(year, month, person)

    if not balance["total"]:
        return ""

    segments = []
    legend = []
    for cat_id, cat in MOOD_CATEGORIES.items():
        pct = balance["percents"][cat_id]
        if pct > 0:
            segments.append(
                '<div class="mood-balance-segment" '
                f'style="width:{pct}%;background:{cat["color"]}" '
                f'title="{cat["label"]}: {pct}%"></div>'
            )
        legend.append(
            f'{cat["emoji"]} {cat["label"]} — '
            f'{balance["percents"][cat_id]}%'
        )

    return (
        f'<div class="mood-balance-bar">{"".join(segments)}</div>'
        f'<div class="mood-balance-legend">{" · ".join(legend)}</div>'
    )


def _rhythm_html(rhythm: dict, keys: list, labels: list,
                 css_extra: str = "") -> str:
    """📅/🕰 Ряд ячеек ритма (дни недели или части дня)."""
    cells = []
    for key, label in zip(keys, labels):
        data = rhythm[key]
        warm = data["warm"]
        tense = data["tense"]

        if warm == 0 and tense == 0:
            emoji = "·"
            cls = "mood-rhythm-cell"
        elif warm >= tense:
            emoji = "🌤"
            cls = "mood-rhythm-cell warm"
        else:
            emoji = "🌧"
            cls = "mood-rhythm-cell tense"

        cells.append(
            f'<div class="{cls}" '
            f'title="{label}: 🌤 {warm} · 🌧 {tense}">'
            f'<div class="mood-rhythm-label">{label}</div>'
            f'<div class="mood-rhythm-emoji">{emoji}</div></div>'
        )

    return (
        f'<div class="mood-rhythm-row {css_extra}">'
        f'{"".join(cells)}</div>'
    )


# ============================================================
# БЛОК КОЛЛЕГ
# ============================================================

def _render_pair_block(year: int, month: int) -> None:
    """🤝 Вы вдвоём: синхронность, поддержка, ресурсы."""
    st.markdown("#### 🤝 Вы вдвоём")

    pair = db.get_pair_stats(year, month)
    both = len(pair["both_days"])
    matched = len(pair["matched_days"])
    support = len(pair["support_days"])
    resource = pair["resource_days"]

    sync_pct = round(matched * 100 / both) if both else 0

    cards = [
        _stat_card("💫", f"{sync_pct}%", "синхронность"),
        _stat_card("🤝", support, "дней поддержки"),
        _stat_card("🌟", len(resource), "общих ресурсных дней"),
    ]
    st.markdown(
        f'<div class="mood-stats-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )

    if resource:
        dates = ", ".join(str(int(d[8:10])) for d in resource)
        st.markdown(
            f'<div class="mood-insight">🌟 Общие ресурсные дни: '
            f'{dates}. Вспомните, что сделало их такими хорошими, — '
            f'это ваш командный рецепт удачного дня!</div>',
            unsafe_allow_html=True,
        )

    if not both:
        st.caption(
            "В этом месяце пока не было дней, когда отмечали обе, "
            "— всё впереди 💚"
        )


# ============================================================
# ИНСАЙТЫ
# ============================================================

def _render_insights(year: int, month: int) -> None:
    """💬 Мягкие инсайты месяца."""
    st.markdown("#### 💬 Мягкие инсайты")

    insights = db.get_month_insights(year, month)
    for text in insights:
        st.markdown(
            f'<div class="mood-insight">🌿 {text}</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# ПЯТИМИНУТКА НЕДЕЛИ
# ============================================================

def _week_row_html(person: str) -> str:
    """Ряд узора последних 7 дней для одной девушки."""
    pattern = db.get_week_pattern(person)

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
        f'<div class="mood-week-row">'
        f'<span class="mood-week-person">{PERSON_EMOJI[person]}'
        f'</span>{"".join(dots)}</div>'
    )


def _render_ritual() -> None:
    """🕯 Пятиминутка недели: узор + вопросы для диалога."""
    st.markdown(f"#### {RITUAL_TITLE}")

    if st.button("🕯 Начать пятиминутку", key="mood_ritual_toggle"):
        st.session_state["mood_ritual_open"] = (
            not st.session_state.get("mood_ritual_open", False)
        )
        st.session_state["mood_ritual_questions"] = (
            random.sample(RITUAL_QUESTIONS, 3)
        )

    if not st.session_state.get("mood_ritual_open"):
        return

    st.markdown(
        f"""
        <div class="mood-ritual-card">
            <div style="color:#8a7a6a; font-size:.9rem;">
                {RITUAL_SUBTITLE}
            </div>
            <div style="margin-top:.8rem;">
                {_week_row_html(PERSONS[0])}
                {_week_row_html(PERSONS[1])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("Вопросы для разговора вдвоём:")
    questions = st.session_state.get(
        "mood_ritual_questions",
        random.sample(RITUAL_QUESTIONS, 3),
    )
    for q in questions:
        st.markdown(
            f'<div class="mood-ritual-question">💬 {q}</div>',
            unsafe_allow_html=True,
        )

    if st.button("🔄 Новые вопросы", key="mood_ritual_refresh"):
        st.session_state["mood_ritual_questions"] = (
            random.sample(RITUAL_QUESTIONS, 3)
        )
        st.rerun()


# ============================================================
# ДОСТИЖЕНИЯ
# ============================================================

def _render_achievements(year: int, month: int, person: str) -> None:
    """Достижения за месяц."""
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
# БЛОК ОДНОЙ ДЕВУШКИ
# ============================================================

def _render_person_block(year: int, month: int, person: str) -> None:
    """Полный блок отчёта по одной девушке."""
    emoji = PERSON_EMOJI[person]
    st.markdown(f"#### {emoji} {person}")

    # 1. Сводные карточки
    st.markdown(
        _person_stats_html(year, month, person),
        unsafe_allow_html=True,
    )

    # 2. Палитра
    st.markdown(
        _palette_html(year, month, person),
        unsafe_allow_html=True,
    )

    # 3. Баланс тепла
    st.markdown(
        _balance_html(year, month, person),
        unsafe_allow_html=True,
    )

    # 4. Ритм недели
    st.caption("Ритм недели:")
    rhythm = db.get_weekday_rhythm(year, month, person)
    st.markdown(
        _rhythm_html(rhythm, list(range(7)), DAYS_OF_WEEK),
        unsafe_allow_html=True,
    )

    # 5. Время суток
    st.caption("Время суток:")
    part_rhythm = db.get_part_rhythm(year, month, person)
    part_labels = [f"{PART_EMOJI[p]} {p}" for p in PARTS_OF_DAY]
    st.markdown(
        _rhythm_html(part_rhythm, PARTS_OF_DAY, part_labels, "parts"),
        unsafe_allow_html=True,
    )

    # Узор месяца
    st.caption(f"Узор месяца — {person}:")
    st.markdown(
        _pattern_html(year, month, person),
        unsafe_allow_html=True,
    )

    # Достижения
    st.caption("Достижения:")
    _render_achievements(year, month, person)
    st.markdown("---")


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def render_stats() -> None:
    """Рендерит блок статистики (скрыт до нажатия кнопки)."""
    st.markdown("### 📊 Статистика")

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

    # Блоки по каждой девушке
    for person in PERSONS:
        _render_person_block(year, month, person)

    # Блок коллег
    _render_pair_block(year, month)

    # Мягкие инсайты
    _render_insights(year, month)

    # Пятиминутка недели
    _render_ritual()