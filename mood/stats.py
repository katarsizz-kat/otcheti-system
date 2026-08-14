"""
Отчёт статистики с разделами-кнопками.

Разделы:
- 🌸 Катя / 🌷 Кристина: карточки, палитра, баланс, ритмы, узор, достижения
- 🎭 Эмоции за период (цветные строки)
- 🤝 Вдвоём: синхронность, поддержка, ресурсы + инсайты
- 🕯 Пятиминутка недели
- 💌 Письмо недели
"""

import random
from datetime import datetime, timedelta, timezone

import streamlit as st

from mood import db
from mood.config import (
    DAYS_OF_WEEK,
    MOOD_CATEGORIES,
    MONTHS_SHORT,
    PART_EMOJI,
    PARTS_OF_DAY,
    PERSON_EMOJI,
    PERSONS,
    RITUAL_QUESTIONS,
    RITUAL_SUBTITLE,
    RITUAL_TITLE,
    get_mood_category,
    get_mood_data,
)
from mood.calendar import _month_options, _parse_month

# Московское время (UTC+3) — по правилам проекта
MOSCOW_TZ = timezone(timedelta(hours=3))

# ============================================================
# РАЗДЕЛЫ СТАТИСТИКИ
# ============================================================

SECTION_LABELS = {
    "katya": "🌸 Катя",
    "kristina": "🌷 Кристина",
    "emotions": "🎭 Эмоции",
    "pair": "🤝 Вдвоём",
    "ritual": "🕯 Пятиминутка",
    "letter": "💌 Письмо",
}


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
    """📅/🕰 Ряд ячеек ритма."""
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
# ЭМОЦИИ ЗА ПЕРИОД
# ============================================================

def _human_date(d) -> str:
    """Дата в формате '11 авг'."""
    return f"{d.day} {MONTHS_SHORT[d.month - 1]}"


def _render_emotion_stats() -> None:
    """🎭 Эмоции за период: цветные строки."""
    st.markdown("#### 🎭 Эмоции за период")

    today = datetime.now(MOSCOW_TZ).date()

    period_option = st.selectbox(
        "Период",
        ["Месяц", "Неделя", "Свой период"],
        key="mood_emotion_period",
    )

    if period_option == "Месяц":
        start = today.replace(day=1)
        end = today
    elif period_option == "Неделя":
        start = today - timedelta(days=today.weekday())
        end = today
    else:
        col_from, col_to = st.columns(2)
        with col_from:
            start = st.date_input(
                "С",
                value=today - timedelta(days=30),
                max_value=today,
                key="mood_period_from",
            )
        with col_to:
            end = st.date_input(
                "По",
                value=today,
                max_value=today,
                key="mood_period_to",
            )
        if start > end:
            st.warning("Дата «с» позже даты «по» 🙈")
            return

    st.caption(
        f"Период: {_human_date(start)} — {_human_date(end)} {end.year}"
    )

    counts = db.get_emotion_counts(start, end)

    if not counts:
        st.caption("За этот период записей пока нет ✨")
        return

    only_total = st.toggle(
        "👯‍♀️ Только общее",
        key="mood_emotion_only_total",
    )

    total_all = sum(row["total"] for row in counts.values())
    max_total = max(row["total"] for row in counts.values())

    sorted_moods = sorted(
        counts.items(),
        key=lambda kv: kv[1]["total"],
        reverse=True,
    )

    for mood, row in sorted_moods:
        data = get_mood_data(mood)
        pct = round(row["total"] * 100 / total_all) if total_all else 0
        bar_pct = round(row["total"] * 100 / max_total) if max_total else 0

        k_count = row[PERSONS[0]]
        kr_count = row[PERSONS[1]]
        if k_count > kr_count:
            leader = PERSON_EMOJI[PERSONS[0]]
        elif kr_count > k_count:
            leader = PERSON_EMOJI[PERSONS[1]]
        else:
            leader = ""

        if only_total:
            nums = f"всего {row['total']} · {pct}%"
        else:
            nums = (
                f"{PERSON_EMOJI[PERSONS[0]]} {k_count} · "
                f"{PERSON_EMOJI[PERSONS[1]]} {kr_count} · "
                f"всего {row['total']} · {pct}%"
            )

        st.markdown(
            f"""
            <div class="mood-emotion-row">
                <div class="mood-emotion-head">
                    <span class="mood-emotion-name">
                        <i style="background:{data['color']}"></i>
                        {data['emoji']} {mood} {leader}
                    </span>
                    <span class="mood-emotion-nums">{nums}</span>
                </div>
                <div class="mood-emotion-bar">
                    <div class="mood-emotion-fill"
                         style="width:{bar_pct}%;
                                background:{data['gradient']}"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# БЛОК КОЛЛЕГ + ИНСАЙТЫ
# ============================================================

def _render_pair_block(year: int, month: int) -> None:
    """🤝 Вы вдвоём + мягкие инсайты месяца."""
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

    # Инсайты месяца
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
    """Ряд узора последних 7 дней."""
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
    """🕯 Пятиминутка недели."""
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
# ПИСЬМО НЕДЕЛИ
# ============================================================

def _pair_from_entries(entries: list) -> dict:
    """Дни поддержки и ресурсы из произвольного набора записей."""
    by_date = {}
    for e in entries:
        if e.get("status") != "logged":
            continue
        day = by_date.setdefault(
            e["date"], {p: {"cats": set()} for p in PERSONS}
        )
        person_data = day.get(e.get("person"))
        if person_data is not None:
            person_data["cats"].add(get_mood_category(e["mood"]))

    support_days = []
    resource_days = []
    for d in sorted(by_date.keys()):
        a = by_date[d][PERSONS[0]]["cats"]
        b = by_date[d][PERSONS[1]]["cats"]
        if not a or not b:
            continue
        if ("tense" in a and "warm" in b) or ("tense" in b and "warm" in a):
            support_days.append(d)
        if "warm" in a and "warm" in b and "tense" not in a and "tense" not in b:
            resource_days.append(d)

    return {"support_days": support_days, "resource_days": resource_days}


def _render_letter() -> None:
    """💌 Письмо недели: бережный текст по данным за 7 дней."""
    st.markdown("#### 💌 Письмо недели")

    today = datetime.now(MOSCOW_TZ).date()
    start = today - timedelta(days=6)
    entries = db.get_entries_for_range(start, today)
    logged = [e for e in entries if e.get("status") == "logged"]

    if not logged:
        st.info(
            "На этой неделе записей пока нет — "
            "письму ещё рано 🌱"
        )
        return

    paragraphs = [
        f"Катя и Кристина, здравствуйте! Вот ваша неделя: "
        f"{_human_date(start)} — {_human_date(today)}.",
    ]

    for person in PERSONS:
        p_logged = [e for e in logged if e.get("person") == person]

        if not p_logged:
            paragraphs.append(
                f"{PERSON_EMOJI[person]} {person}, на этой неделе "
                f"вы были тише — и это тоже нормально 🌫"
            )
            continue

        counts: dict = {}
        warm = tense = 0
        for e in p_logged:
            counts[e["mood"]] = counts.get(e["mood"], 0) + 1
            cat = get_mood_category(e["mood"])
            if cat == "warm":
                warm += 1
            elif cat == "tense":
                tense += 1

        top = max(counts.items(), key=lambda kv: kv[1])
        paragraphs.append(
            f"{PERSON_EMOJI[person]} {person}, вы отметили "
            f"{len(p_logged)} раз. Чаще всего — "
            f"{get_mood_data(top[0])['emoji']} {top[0]}. "
            f"Тёплых моментов: {warm}, напряжённых: {tense}. "
            f"И у каждого из них есть право быть 💚"
        )

    pair = _pair_from_entries(entries)

    if pair["support_days"]:
        paragraphs.append(
            f"🤝 Дней поддержки на этой неделе: "
            f"{len(pair['support_days'])}. Когда одной было тяжело, "
            f"другая была в ресурсе — это ваша суперсила."
        )

    if pair["resource_days"]:
        dates = ", ".join(
            _human_date(datetime.fromisoformat(d).date())
            for d in pair["resource_days"]
        )
        paragraphs.append(
            f"🌟 Общие ресурсные дни: {dates}. "
            f"Вспомните, что сделало их такими, — и повторите!"
        )

    paragraphs.append("Берегите себя — и друг друга. Ваш дневник 🌿")

    html = "".join(f"<p>{p}</p>" for p in paragraphs)
    st.markdown(
        f'<div class="mood-ritual-card mood-letter">{html}</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# БЛОК ОДНОЙ ДЕВУШКИ
# ============================================================

def _render_person_block(year: int, month: int, person: str) -> None:
    """Полный блок отчёта по одной девушке."""
    emoji = PERSON_EMOJI[person]
    st.markdown(f"#### {emoji} {person}")

    st.markdown(
        _person_stats_html(year, month, person),
        unsafe_allow_html=True,
    )
    st.markdown(
        _palette_html(year, month, person),
        unsafe_allow_html=True,
    )
    st.markdown(
        _balance_html(year, month, person),
        unsafe_allow_html=True,
    )

    st.caption("Ритм недели:")
    rhythm = db.get_weekday_rhythm(year, month, person)
    st.markdown(
        _rhythm_html(rhythm, list(range(7)), DAYS_OF_WEEK),
        unsafe_allow_html=True,
    )

    st.caption("Время суток:")
    part_rhythm = db.get_part_rhythm(year, month, person)
    part_labels = [f"{PART_EMOJI[p]} {p}" for p in PARTS_OF_DAY]
    st.markdown(
        _rhythm_html(part_rhythm, PARTS_OF_DAY, part_labels, "parts"),
        unsafe_allow_html=True,
    )

    st.caption(f"Узор месяца — {person}:")
    st.markdown(
        _pattern_html(year, month, person),
        unsafe_allow_html=True,
    )

    st.caption("Достижения:")
    _render_achievements(year, month, person)


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
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def render_stats() -> None:
    """Рендерит статистику с кнопками-разделами."""
    st.markdown("### 📊 Статистика")

    # Кнопки-разделы
    cols = st.columns(len(SECTION_LABELS))
    for col, (key, label) in zip(cols, SECTION_LABELS.items()):
        with col:
            active = (
                st.session_state.get("mood_stats_section") == key
            )
            if st.button(
                label,
                use_container_width=True,
                type="primary" if active else "secondary",
                key=f"mood_section_{key}",
            ):
                st.session_state["mood_stats_section"] = key

    section = st.session_state.get("mood_stats_section")

    if not section:
        st.info(
            "Выберите раздел — и он откроется здесь 🌸"
        )
        return

    # Месяц для личных и парного разделов
    if section in ("katya", "kristina", "pair"):
        options = _month_options()
        month_option = st.selectbox(
            "Месяц",
            options,
            index=len(options) - 1,
            key="mood_stats_month",
        )
        year, month = _parse_month(month_option)

    if section == "katya":
        _render_person_block(year, month, PERSONS[0])
    elif section == "kristina":
        _render_person_block(year, month, PERSONS[1])
    elif section == "emotions":
        _render_emotion_stats()
    elif section == "pair":
        _render_pair_block(year, month)
    elif section == "ritual":
        _render_ritual()
    elif section == "letter":
        _render_letter()