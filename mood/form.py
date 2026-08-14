"""
Форма ввода настроения: две колонки (Катя и Кристина).

Общий блок: вопрос дня + рефлексия (ответы обеих девушек).
Каждая колонка: дата, часть дня, эмоция, интенсивность 1–5,
заметка «почему я это чувствую», кнопки «Сохранить» и «Пауза»,
список записей дня.
"""

import random
from datetime import datetime, timedelta, timezone

import streamlit as st

from mood import db
from mood.config import (
    INTENSITY_LABELS,
    MOODS,
    PART_EMOJI,
    PARTS_OF_DAY,
    PAUSE_TEXTS,
    PERSON_EMOJI,
    PERSONS,
    REACTIONS,
    get_mood_options,
    parse_mood_from_option,
)

# Московское время (UTC+3) — по правилам проекта
MOSCOW_TZ = timezone(timedelta(hours=3))

# ============================================================
# ВОПРОС ДНЯ
# ============================================================

DAILY_QUESTIONS = [
    "Что сегодня тебя удивило?",
    "Что сегодня получилось хорошо?",
    "Что хочется оставить в офисе сегодня?",
    "Что заставило улыбнуться сегодня?",
    "Что ты скажешь себе завтра утром?",
    "Что было самым приятным за день?",
    "Что сегодня забрало больше всего сил?",
    "Что сегодня дало тебе энергии?",
    "Чем хочется поделиться с коллегой?",
    "Чего не хватило сегодня до идеала?",
    "Какой момент дня хочется запомнить?",
    "Что маленькое, но важное случилось сегодня?",
]


def _daily_question() -> str:
    """
    Вопрос дня: один на страницу, один в течение дня.

    Детерминированный выбор по дате (seed = номер дня),
    поэтому весь день вопрос не меняется.
    """
    today = datetime.now(MOSCOW_TZ).date()
    rng = random.Random(today.toordinal())
    return rng.choice(DAILY_QUESTIONS)


# ============================================================
# СЛУЖЕБНЫЕ
# ============================================================

def _today_moscow():
    """Сегодняшняя дата по Москве."""
    return datetime.now(MOSCOW_TZ).date()


def _apply_pending_actions(person: str) -> None:
    """
    Отложенные действия ДО отрисовки виджетов.

    Streamlit разрешает менять значение виджета по ключу
    только до того, как виджет отрисован в этом запуске.
    """
    if st.session_state.pop(f"mood_clear_note_{person}", False):
        st.session_state[f"mood_note_{person}"] = ""


def _show_flash(person: str) -> None:
    """Показать сохранённое сообщение после rerun."""
    flash = st.session_state.pop(f"mood_flash_{person}", None)
    if flash:
        st.success(flash)


# ============================================================
# ВОПРОС ДНЯ + РЕФЛЕКСИЯ
# ============================================================

def _render_daily_reflection() -> None:
    """Вопрос дня и поля для ответов обеих девушек."""
    question = _daily_question()
    today = _today_moscow()

    st.markdown(
        f'<div class="mood-daily-question">'
        f'❓ Вопрос дня: {question}</div>',
        unsafe_allow_html=True,
    )

    flash = st.session_state.pop("mood_flash_reflection", None)
    if flash:
        st.success(flash)

    existing = db.get_reflections_for_date(today)
    by_person = {r["person"]: r for r in existing}

    cols = st.columns(2, gap="large")
    answers = {}
    for col, person in zip(cols, PERSONS):
        with col:
            saved = by_person.get(person)
            answers[person] = st.text_area(
                f"💬 Ответ — {person}",
                value=saved["answer"] if saved else "",
                height=90,
                key=f"mood_reflection_{person}",
                placeholder="Пара строк о своём…",
            )

    if st.button(
        "💬 Сохранить ответы",
        key="mood_reflection_save",
    ):
        for person in PERSONS:
            db.save_reflection(
                person, today, question, answers[person]
            )
        st.session_state["mood_flash_reflection"] = (
            "Ответы сохранены 🌿"
        )
        st.rerun()


# ============================================================
# ЗАПИСИ ДНЯ
# ============================================================

def _render_day_entries(person: str, entry_date) -> None:
    """Список записей человека за выбранную дату + удаление."""
    st.markdown("---")
    st.caption("Записи за выбранный день")

    entries = db.get_entries_for_date(entry_date)
    person_entries = [
        e for e in entries if e.get("person") == person
    ]

    if not person_entries:
        st.caption("Пока пусто ✨")
        return

    for e in person_entries:
        if e.get("status") == "pause":
            color = "#d0d0d0"
            text = "🌫 День без ответа"
            note_html = ""
        else:
            mood_data = MOODS.get(e.get("mood"), {})
            color = mood_data.get("color", "#cccccc")
            part_emoji = PART_EMOJI.get(e.get("part_of_day"), "")
            text = (
                f"{part_emoji} {mood_data.get('emoji', '')} "
                f"{e.get('mood')} · {e.get('intensity')}/5"
            )
            note_html = (
                f'<div style="font-size:.8rem; color:#8a7a6a;">'
                f'{e.get("note")}</div>'
                if e.get("note") else ""
            )

        line_col, del_col = st.columns([6, 1])
        with line_col:
            st.markdown(
                f'<div class="mood-entry-item" '
                f'style="border-left-color:{color};">'
                f'<div>{text}</div>{note_html}</div>',
                unsafe_allow_html=True,
            )
        with del_col:
            if st.button("🗑", key=f"mood_del_{e['id']}"):
                db.delete_entry(e["id"])
                st.rerun()


# ============================================================
# КОЛОНКА ОДНОГО ЧЕЛОВЕКА
# ============================================================

def _render_person_column(person: str) -> None:
    """Полная форма одного человека."""
    emoji = PERSON_EMOJI[person]
    st.markdown(f"### {emoji} {person}")

    # Отложенные действия и сообщения — ДО виджетов
    _apply_pending_actions(person)
    _show_flash(person)

    # Дата (не дальше сегодня)
    entry_date = st.date_input(
        "Дата",
        value=_today_moscow(),
        max_value=_today_moscow(),
        min_value=_today_moscow() - timedelta(days=365),
        key=f"mood_date_{person}",
    )

    # Часть дня
    part = st.selectbox(
        "Часть дня",
        PARTS_OF_DAY,
        key=f"mood_part_{person}",
    )

    # Эмоция
    mood_option = st.selectbox(
        "Эмоция",
        get_mood_options(),
        key=f"mood_select_{person}",
    )
    mood_name = parse_mood_from_option(mood_option)
    mood_data = MOODS[mood_name]

    # Цветное превью выбранной эмоции
    st.markdown(
        f"""
        <div style="
            background: {mood_data['gradient']};
            border-radius: 14px;
            padding: .6rem 1rem;
            color: white;
            font-weight: 600;
            text-align: center;
            box-shadow: 0 4px 14px {mood_data['color']}44;
            margin-bottom: .8rem;
        ">
            {mood_data['emoji']} {mood_name}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Интенсивность: 5 кнопок-кружочков, цвет от эмоции
    st.markdown(
        f"""
        <style>
        div[data-testid="stRadio"]:has(
            input[id^="mood_intensity_{person}"]
        ) label > div {{
            border-radius: 999px !important;
            min-width: 34px;
            height: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid {mood_data['color']}55;
            font-weight: 700;
            transition: all .2s ease;
        }}
        div[data-testid="stRadio"]:has(
            input[id^="mood_intensity_{person}"]
        ) input:checked + div {{
            background: {mood_data['gradient']} !important;
            color: white !important;
            border-color: transparent;
            box-shadow: 0 4px 12px {mood_data['color']}66;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    intensity = int(
        st.radio(
            "Интенсивность",
            ["1", "2", "3", "4", "5"],
            horizontal=True,
            index=int(
                st.session_state.get(
                    f"mood_intensity_{person}", 3
                )
            ) - 1,
            key=f"mood_intensity_{person}",
        )
    )
    st.caption(INTENSITY_LABELS[intensity])

    # Заметка: почему я это чувствую
    note = st.text_input(
        "Заметка (необязательно)",
        key=f"mood_note_{person}",
        placeholder="Почему? Что случилось?",
    )

    # Кнопки действий
    col_save, col_pause = st.columns(2)
    with col_save:
        if st.button(
            "💾 Сохранить",
            key=f"mood_save_{person}",
            use_container_width=True,
        ):
            db.save_entry(
                person, entry_date, part,
                mood_name, intensity, note,
            )
            st.session_state[f"mood_flash_{person}"] = (
                REACTIONS.get(mood_name, "Запись сохранена 🌿")
            )
            # Очищаем заметку отложенно (на следующем рендере)
            st.session_state[f"mood_clear_note_{person}"] = True
            st.rerun()

    with col_pause:
        if st.button(
            "🌫 Пауза",
            key=f"mood_pause_{person}",
            use_container_width=True,
        ):
            db.save_pause(person, entry_date)
            st.session_state[f"mood_flash_{person}"] = (
                random.choice(PAUSE_TEXTS)
            )
            st.session_state[f"mood_clear_note_{person}"] = True
            st.rerun()

    # Записи дня
    _render_day_entries(person, entry_date)


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def render_entry_form() -> None:
    """Рендерит вопрос дня с рефлексией + две колонки формы."""
    # Вопрос дня + ответы на него
    _render_daily_reflection()

    cols = st.columns(2, gap="large")
    for col, person in zip(cols, PERSONS):
        with col:
            _render_person_column(person)