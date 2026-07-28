"""Главная страница приложения."""
import streamlit as st
import streamlit.components.v1 as components

# ВАЖНО: set_page_config должен быть ПЕРВЫМ вызовом streamlit!
st.set_page_config(page_title="Система отчётов", page_icon="", layout="wide")

# Импорты
from config.greetings import get_current_greeting
from config.reports import get_reports
from config.holidays import get_today_holiday, get_upcoming_holidays
from styles import apply_theme
from components import (
    render_app_header,
    render_welcome_block,
    render_holiday_banner,
    render_report_card,
    render_upcoming_holidays_section,
    render_footer,
)
from easter_eggs.dino import (
    init_easter_egg,
    render_dino_modal,
    render_secret_button,
)

# Получаем данные
greeting_data = get_current_greeting()
holiday = get_today_holiday()
reports = get_reports()
upcoming_holidays = get_upcoming_holidays(days=7)

# Применяем тему
holiday_effects = holiday.get("effects") if holiday and isinstance(holiday, dict) else None
apply_theme(greeting_data["theme"], holiday_effects)

# === ИНИЦИАЛИЗАЦИЯ ПАСХАЛКИ ===
init_easter_egg()

# === ОБРАБОТКА СООБЩЕНИЙ ОТ JAVASCRIPT ===
components.html("""
<script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'easter_egg_activate') {
            var btn = document.createElement('button');
            btn.id = 'activate-easter-egg';
            btn.style.display = 'none';
            document.body.appendChild(btn);
            btn.click();
        }
    });
</script>
""", height=0, width=0)

# Скрытая кнопка для активации через JavaScript
if st.button("", key="js_activate_easter"):
    st.session_state.easter_egg_activated = True
    st.balloons()
    st.rerun()

# === МОДАЛЬНОЕ ОКНО С ДИНОЗАВРОМ ===
render_dino_modal()

# === ВЕРХНЯЯ ПАНЕЛЬ ===
render_app_header()

# === ПРИВЕТСТВЕННЫЙ БЛОК ===
subtitle = "Здесь можно сформировать отчёты одним кликом."
render_welcome_block(
    icon=greeting_data["icon"],
    greeting=greeting_data["greeting"],
    subtitle=subtitle,
)

# === КАРТОЧКИ ОТЧЁТОВ ===
st.markdown("### 📋 Доступные отчёты", unsafe_allow_html=True)
cols = st.columns(3)
for idx, report in enumerate(reports):
    with cols[idx % 3]:
        render_report_card(report)

# === ПРАЗДНИЧНЫЙ БАННЕР (кликабельный) ===
if holiday:
    render_holiday_banner(holiday)

# === БЛИЖАЙШИЕ ПРАЗДНИКИ ===
render_upcoming_holidays_section(upcoming_holidays)

# === ПОДВАЛ ===
render_footer()

# === ПРОЗРАЧНАЯ КНОПКА ВЫЗОВА ДИНО (ВНИЗУ СТРАНИЦЫ) ===
render_secret_button()
