"""
Страница 11: Дневник эмоциональной погоды.

Тонкий слой: подключает стили, проверяет пароль,
рендерит три вкладки. Вся логика — в модулях mood/.
"""

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы import mood
# работал при любом способе запуска страницы
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

import mood
from mood.auth import logout, render_auth_gate
from mood.calendar import render_calendar
from mood.form import render_entry_form
from mood.stats import render_stats


def _inject_styles() -> None:
    """Подключает mood/styles.css к странице."""
    styles_path = Path(mood.__file__).parent / "styles.css"
    try:
        css = styles_path.read_text(encoding="utf-8")
        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True,
        )
    except FileNotFoundError:
        st.warning("⚠️ Не найден файл mood/styles.css")


def _render_header() -> None:
    """Шапка страницы с кнопкой выхода."""
    title_col, logout_col = st.columns([6, 1])

    with title_col:
        st.markdown("# 🌿 Дневник эмоциональной погоды")
        st.caption("дневник настроения для двоих")

    with logout_col:
        st.markdown(
            "<div style='height:2.2rem'></div>",
            unsafe_allow_html=True,
        )
        if st.button("Выйти", key="mood_logout"):
            logout()


def main() -> None:
    """Точка входа страницы."""
    _inject_styles()
    _render_header()

    # Вход по паролю; False — дальше не рендерим
    if not render_auth_gate():
        return

    # Три вкладки
    tab_form, tab_calendar, tab_stats = st.tabs(
        ["📝 Отметить", "📅 Календарь", "📊 Статистика"]
    )

    with tab_form:
        render_entry_form()

    with tab_calendar:
        render_calendar()

    with tab_stats:
        render_stats()


main()