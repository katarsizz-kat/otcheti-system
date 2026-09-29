# pages/КП_B2B.py

"""
Тонкая точка входа для страницы «Корпоративное предложение (B2B)».

Вся логика и интерфейс — в kp_b2b/page.py.
Здесь только подключение и запуск render_page().
"""

from pathlib import Path
import sys

# Корень проекта, чтобы импорты работали независимо от способа запуска
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from kp_b2b.page import render_page
except Exception as exc:  # noqa: BLE001
    import streamlit as st

    st.set_page_config(
        page_title="КП для B2B",
        page_icon="🍕",
        layout="wide",
    )

    st.error("Не удалось загрузить интерфейс страницы «КП для B2B».")
    st.info(
        "Проверь, что есть папка `kp_b2b/` с файлом `page.py` "
        "и в нём есть функция `render_page()`."
    )
    st.exception(exc)
    st.stop()

# Запуск интерфейса страницы
render_page()
