# pages/13_ControlComplaints.py

"""
Тонкая точка входа для страницы «Контроль жалоб».

Вся логика и интерфейс — в ui/pages/complaints_control.py.
Здесь только подключение и запуск render_page().
"""

from pathlib import Path
import sys

# Корень проекта, чтобы импорты работали независимо от способа запуска
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from ui.pages.complaints_control import render_page
except Exception as exc:  # noqa: BLE001
    import streamlit as st

    st.set_page_config(
        page_title="Контроль жалоб",
        page_icon="🕵️",
        layout="wide",
    )

    st.error("Не удалось загрузить интерфейс страницы «Контроль жалоб».")
    st.info(
        "Проверь, что создан файл `ui/pages/complaints_control.py` "
        "и в нём есть функция `render_page()`."
    )
    st.exception(exc)
    st.stop()

# Запуск интерфейса страницы
render_page()
