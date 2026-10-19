"""Главная страница приложения.

v3.0 (дизайн-система Sage & Sandstone):
- Критический CSS без "мигания": фон из палитры; если в URL есть
  ?theme=dark — сразу тёмный.
- Блок "Ближайшие события" и кнопка календаря убраны с главной
  (календарь доступен в меню слева).
- "Ближайшие праздники" — 5 дней вперёд.
- Динозавр только здесь: render_footer(show_dino=True).
- Пятница после 17:00 (МСК) — конфетти и пятничный подзаголовок.
- Убраны мёртвые импорты (get_reports, render_report_card).
"""
import streamlit as st
from datetime import datetime

# =============================================================================
# 1. НАСТРОЙКА СТРАНИЦЫ (ВСЕГДА ПЕРВАЯ КОМАНДА!)
# =============================================================================
st.set_page_config(page_title="Система отчётов", page_icon="🦖", layout="wide")

# =============================================================================
# 2. КРИТИЧЕСКИЙ CSS (МГНОВЕННОЕ ПРИМЕНЕНИЕ)
# Фон берётся из палитры; при override ?theme=dark — сразу тёмный,
# чтобы не было мигания светлым при перезагрузке.
# =============================================================================
_override = st.query_params.get("theme")
_crit_bg = "#1E2420" if _override == "dark" else "#F7F5F1"

st.markdown(
    f"""
<style>
/* Принудительно красим контейнеры Streamlit ДО загрузки apply_theme */
.stApp,
body,
.main .block-container,
[data-testid="stAppViewBlockContainer"] {{
    background-color: {_crit_bg} !important;
    background: {_crit_bg} !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# 3. ИМПОРТЫ
# =============================================================================
from config.greetings import get_current_greeting, MOSCOW_TZ
from config.holidays import get_today_holiday, get_upcoming_holidays
from styles import apply_theme
from components import (
    render_app_header,
    render_welcome_block,
    render_holiday_banner,
    render_upcoming_holidays_section,
    render_footer,
)

# =============================================================================
# Сброс состояния динозавра при загрузке главной страницы
# =============================================================================
if "main_page_dino_modal_open" not in st.session_state:
    st.session_state.main_page_dino_modal_open = False

# =============================================================================
# Получение данных
# =============================================================================
greeting_data = get_current_greeting()
holiday = get_today_holiday()
upcoming_holidays = get_upcoming_holidays(days=5)
holiday_effects = holiday.get("effects") if holiday and isinstance(holiday, dict) else None

_now = datetime.now(MOSCOW_TZ)
is_friday_evening = _now.weekday() == 4 and _now.hour >= 17
if is_friday_evening:
    holiday_effects = list(holiday_effects or [])
    if "confetti" not in holiday_effects:
        holiday_effects.append("confetti")

# Применяем тему (база A/B + эффекты поверх, с учётом override из URL)
apply_theme(greeting_data["theme"], holiday_effects)

# =============================================================================
# Рендеринг страницы
# =============================================================================
render_app_header()

if is_friday_evening:
    subtitle = "Пятница! Отчёты подождут 🦖"
else:
    subtitle = "Праздники, отчёты и немного магии — всё здесь."
render_welcome_block(
    icon=greeting_data["icon"],
    greeting=greeting_data["greeting"],
    subtitle=subtitle,
)

# =============================================================================
# Праздничный баннер (если есть праздник сегодня)
# =============================================================================
if holiday:
    render_holiday_banner(holiday)

# =============================================================================
# Ближайшие праздники (5 дней вперёд)
# =============================================================================
if upcoming_holidays:
    render_upcoming_holidays_section(upcoming_holidays)

# =============================================================================
# Футер (с динозавром — только на главной)
# =============================================================================
render_footer(show_dino=True)