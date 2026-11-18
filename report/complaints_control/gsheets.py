"""
Прямое чтение главных таблиц из Google Sheets (без ручной выгрузки).

Таблицы доступны по ссылке на чтение — проверено 18.11.2026: полный
XLSX-экспорт (/export?format=xlsx) отдаёт все листы, включая «Сводную»
со справочником ресторанов, поэтому существующие загрузчики data.py
работают с результатом без изменений.

Без Streamlit: кеширование и обработка ошибок — на стороне UI.
"""
from __future__ import annotations

import io

import requests

SPB_SHEET_ID = "1iuKPpRwaMGNpIVf7UQPd98NS45-zOAYJ53KWl_O-w5c"
TMN_SHEET_ID = "1GACra2Y0D6qFwaOadphFmO5q8MFhXhD6gZzSOJOwWs0"

SHEET_IDS = {"СПб": SPB_SHEET_ID, "Тюмень": TMN_SHEET_ID}

_TIMEOUT_SECONDS = 60


def fetch_main_table(city: str) -> io.BytesIO:
    """Скачивает актуальную версию главной таблицы города как XLSX.

    Бросает requests.HTTPError / KeyError при недоступности — UI должен
    показать ошибку и предложить ручную загрузку файла.
    """
    sheet_id = SHEET_IDS[city]
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    response = requests.get(url, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    out = io.BytesIO(response.content)
    out.seek(0)
    return out