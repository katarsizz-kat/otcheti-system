import streamlit as st

st.set_page_config(
    page_title="Foodcost отчёты",
    page_icon="📊",
    layout="wide",
)

from config.greetings import get_current_greeting
from config.holidays import get_today_holiday
from styles import apply_subtle_theme

greeting_data = get_current_greeting() or {}
holiday = get_today_holiday() or {}

apply_subtle_theme(
    greeting_data.get("theme"),
    holiday.get("effects") if isinstance(holiday, dict) else None,
)

from ui.pages.foodcost import render

render()