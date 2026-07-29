"""Главная страница приложения."""
import streamlit as st

st.set_page_config(page_title="Система отчётов", page_icon="🦖", layout="wide")

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

greeting_data = get_current_greeting()
holiday = get_today_holiday()
reports = get_reports()
upcoming_holidays = get_upcoming_holidays(days=7)

holiday_effects = holiday.get("effects") if holiday and isinstance(holiday, dict) else None
apply_theme(greeting_data["theme"], holiday_effects)

render_app_header()

subtitle = "Здесь можно сформировать отчёты одним кликом."
render_welcome_block(
    icon=greeting_data["icon"],
    greeting=greeting_data["greeting"],
    subtitle=subtitle,
)

st.markdown("### Доступные отчёты", unsafe_allow_html=True)
cols = st.columns(3)
for idx, report in enumerate(reports):
    with cols[idx % 3]:
        render_report_card(report)

if holiday:
    render_holiday_banner(holiday)

render_upcoming_holidays_section(upcoming_holidays)

render_footer()
