"""Страница Продукт: входная точка."""
import streamlit as st

# Важно: должно быть первой командой Streamlit на странице
st.set_page_config(
    page_title="Отчет Продукт",
    page_icon="🍕",
    layout="wide"
)

from config.greetings import get_current_greeting
from config.holidays import get_today_holiday
from styles import apply_subtle_theme
from ui.pages.prodykt import render_prodykt_page
from report.prodykt import generate_product_report


# ==================== ТЕМА ====================
greeting_data = get_current_greeting()
holiday = get_today_holiday()

theme = greeting_data.get("theme", "day") if isinstance(greeting_data, dict) else "day"
holiday_effects = holiday.get("effects") if isinstance(holiday, dict) else None

apply_subtle_theme(theme, holiday_effects)


# ==================== ЗАГОЛОВОК СТРАНИЦЫ ====================
st.markdown(
    """
<div class="header-block fade-in">
    <h1>🍕 Отчет Продукт</h1>
    <p>Генератор сводного отчёта по продукту</p>
</div>
""",
    unsafe_allow_html=True
)


# ==================== СОСТОЯНИЕ ФАЙЛОВ ====================
if "product_files" not in st.session_state:
    st.session_state.product_files = {
        "main": None,
        "combo": None
    }


# ==================== РЕНДЕРИНГ ====================
render_prodykt_page(
    st.session_state.product_files,
    generate_product_report
)