"""
Календарь настроения: три режима просмотра.

- 🌸 Календарь Кати (точки по всем настроениям дня)
- 🌷 Календарь Кристины (точки по всем настроениям дня)
- 👯‍♀️ Общий (две полоски в каждой ячейке)

За одну часть дня может быть несколько настроений:
- в личном календаре — точка за каждое настроение;
- в общем — градиентная полоска из цветов настроений;
- в подсказке — цепочка «😊 хорошее → 😟 тревога».
"""

import calendar as cal
from datetime import datetime, timedelta, timezone

import streamlit as st

from mood import db
from mood.config import (
    CALENDAR_MODES,
    DAYS_OF_WEEK,
    MOODS,
    MONTHS,
    PARTS_OF_DAY,
    PERSONS,
    get_mood_data,
)

# Московское время (UTC+3) — по правилам проекта
MOSCOW_TZ = timezone(timedelta(hours=3))

# Прозрачный сегмент (нет записи за часть дня)
EMPTY_SEGMENT = "rgba(0, 0, 0, 0.05)"

# Штриховка для дня-паузы
PAUSE_STRIPE = (
    "repeating-linear-gradient(45deg, "
    "#e0e0e0 0 4px, #f2f2f2 4px 8px)"
)


# ============================================================
# МЕСЯЦЫ
# ============================================================

def _month_options() -> list:
    """Список 'Месяц Год' за последние 12 месяцев."""
    today = datetime.now(MOSCOW_TZ).date()
    options = []
    for i in range(11, -1, -1):
        y = today.year
        m = today.month - i
        while m < 1:
            m += 12
            y -= 1
        options.append(f"{MONTHS[m - 1]} {y}")
    return options


def _parse_month(option: str):
    """Из 'Август 2026' вернуть (год, номер_месяца)."""
    parts = option.split()
    return int(parts[1]), MONTHS.index(parts[0]) + 1


# ============================================================
# ДЕТАЛИ ЯЧЕЕК
# ============================================================

def _logged_entries(entries: list, part: str = None) -> list:
    """Отфильтровать только logged-записи (опционально по части дня)."""
    result = []
    for e in entries:
        if e.get("status") != "logged":
            continue
        if part is not None and e.get("part_of_day") != part:
            continue
        result.append(e)
    return result


def _part_background(logged: list) -> str:
    """
    Фон сегмента части дня.

    Одно настроение — сплошной цвет,
    несколько — градиент из цветов по хронологии.
    """
    colors = [get_mood_data(e["mood"])["color"] for e in logged]
    if not colors:
        return EMPTY_SEGMENT
    if len(colors) == 1:
        return colors[0]
    return f"linear-gradient(90deg, {', '.join(colors)})"


def _person_dots(entries: list) -> str:
    """Точки по всем настроениям дня (личный календарь)."""
    if entries and all(
        e.get("status") == "pause" for e in entries
    ):
        return (
            '<div class="mood-calendar-dots">'
            '<span class="mood-calendar-dot" '
            'style="background:#d0d0d0"></span>'
            '<span style="font-size:.7rem">🌫</span></div>'
        )

    dots = []
    for e in _logged_entries(entries):
        color = get_mood_data(e["mood"])["color"]
        dots.append(
            f'<span class="mood-calendar-dot" '
            f'style="background:{color}"></span>'
        )
    return f'<div class="mood-calendar-dots">{"".join(dots)}</div>'


def _person_stripe(entries: list) -> str:
    """Полоска из 3 сегментов (общий календарь)."""
    if not entries:
        return (
            f'<div class="mood-calendar-stripe" '
            f'style="background:{EMPTY_SEGMENT}"></div>'
        )

    if all(e.get("status") == "pause" for e in entries):
        return (
            f'<div class="mood-calendar-stripe" '
            f'style="background:{PAUSE_STRIPE}"></div>'
        )

    segments = []
    for part in PARTS_OF_DAY:
        logged = _logged_entries(entries, part)
        background = _part_background(logged)
        segments.append(
            '<div class="mood-calendar-stripe-segment" '
            f'style="background:{background}"></div>'
        )
    return (
        f'<div class="mood-calendar-stripe">'
        f'{"".join(segments)}</div>'
    )


def _tooltip(date_str: str, mode: str, index: dict) -> str:
    """Подсказка при наведении на ячейку."""
    persons = PERSONS if mode == "Общий" else [mode]
    lines = []

    for person in persons:
        entries = index.get((date_str, person), [])
        if not entries:
            continue

        if all(e.get("status") == "pause" for e in entries):
            lines.append(f"{person}: 🌫 без ответа")
            continue

        parts = []
        for part in PARTS_OF_DAY:
            logged = _logged_entries(entries, part)
            if logged:
                chain = " → ".join(
                    f"{get_mood_data(e['mood'])['emoji']} "
                    f"{e['mood']} {e['intensity']}/5"
                    for e in logged
                )
                parts.append(f"{part}: {chain}")

        if parts:
            lines.append(f"{person}: {'; '.join(parts)}")

    return "&#10;".join(lines)


def _cell_html(
    day: int,
    date_str: str,
    mode: str,
    index: dict,
    today_str: str,
) -> str:
    """HTML одной ячейки календаря."""
    cls = "mood-calendar-cell"
    if date_str == today_str:
        cls += " today"
    if mode == "Общий":
        cls += " mood-calendar-cell-shared"

    title = _tooltip(date_str, mode, index)
    title_attr = f' title="{title}"' if title else ""

    inner = f'<div class="mood-calendar-date">{day}</div>'

    if mode == "Общий":
        for person in PERSONS:
            inner += _person_stripe(
                index.get((date_str, person), [])
            )
    else:
        inner += _person_dots(index.get((date_str, mode), []))

    return f'<div class="{cls}"{title_attr}>{inner}</div>'


# ============================================================
# СЕТКА И ЛЕГЕНДА
# ============================================================

def _calendar_html(year: int, month: int, mode: str, index: dict) -> str:
    """Полная HTML-сетка месяца."""
    first_weekday, days_in_month = cal.monthrange(year, month)
    today_str = datetime.now(MOSCOW_TZ).date().isoformat()

    cells = []
    for _ in range(first_weekday):
        cells.append(
            '<div class="mood-calendar-cell empty"></div>'
        )

    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        cells.append(
            _cell_html(day, date_str, mode, index, today_str)
        )

    header = "".join(
        f'<div class="mood-calendar-day-label">{d}</div>'
        for d in DAYS_OF_WEEK
    )

    return (
        '<div class="mood-calendar-container">'
        f'<div class="mood-calendar-grid">{header}'
        f'{"".join(cells)}</div></div>'
    )


def _legend_html() -> str:
    """Легенда эмоций под календарём."""
    chips = []
    for name, data in MOODS.items():
        chips.append(
            f'<span class="chip">'
            f'<i style="background:{data["color"]}"></i>'
            f'{data["emoji"]} {name}</span>'
        )
    chips.append(
        '<span class="chip">'
        '<i style="background:#d0d0d0"></i>🌫 без ответа</span>'
    )
    return f'<div class="legend">{"".join(chips)}</div>'


def _render_shared_insights(year: int, month: int) -> None:
    """Мягкие инсайты для общего календаря."""
    info = db.get_shared_info(year, month)
    both = len(info["both_days"])
    matched = len(info["matched_days"])

    if both == 0:
        return

    st.markdown(
        f"""
        <div class="mood-card" style="margin-top:1rem;">
            💞 Дней, когда отмечали обе: <b>{both}</b><br>
            ✨ Из них с совпавшим настроением: <b>{matched}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def render_calendar() -> None:
    """Рендерит блок календаря с переключением режимов."""
    st.markdown("### 📅 Календарь настроений")

    # Кнопки режимов
    btn_cols = st.columns(3)
    for col, (mode, meta) in zip(btn_cols, CALENDAR_MODES.items()):
        with col:
            active = (
                st.session_state.get("mood_calendar_mode")
                == mode
            )
            if st.button(
                f"{meta['emoji']} {meta['label']}",
                use_container_width=True,
                type="primary" if active else "secondary",
                key=f"mood_mode_{mode}",
            ):
                st.session_state["mood_calendar_mode"] = mode
                st.rerun()

    mode = st.session_state.get("mood_calendar_mode")

    # Календарь появляется только после нажатия кнопки
    if not mode:
        st.info(
            "Выберите режим календаря — "
            "и он появится здесь 🌸"
        )
        return

    # Выбор месяца
    options = _month_options()
    month_option = st.selectbox(
        "Месяц",
        options,
        index=len(options) - 1,
        key="mood_calendar_month",
    )
    year, month = _parse_month(month_option)

    # Данные месяца
    entries = db.get_entries_for_month(year, month)
    index = {}
    for e in entries:
        index.setdefault((e["date"], e["person"]), []).append(e)

    # Календарь + легенда
    st.markdown(
        _calendar_html(year, month, mode, index),
        unsafe_allow_html=True,
    )
    st.markdown(_legend_html(), unsafe_allow_html=True)

    # Инсайты для общего режима
    if mode == "Общий":
        _render_shared_insights(year, month)