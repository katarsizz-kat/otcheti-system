"""
Страница: Универсальный отчёт.

Точка входа Streamlit.
Вся визуальная часть вынесена в:
    ui/pages/universal_report.py
"""

import streamlit as st

from ui.pages.universal_report import render_universal_report


def run() -> None:
    render_universal_report()


run()