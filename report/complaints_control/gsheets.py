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
import time

import requests

SPB_SHEET_ID = "1iuKPpRwaMGNpIVf7UQPd98NS45-zOAYJ53KWl_O-w5c"
TMN_SHEET_ID = "1GACra2Y0D6qFwaOadphFmO5q8MFhXhD6gZzSOJOwWs0"

SHEET_IDS = {"СПб": SPB_SHEET_ID, "Тюмень": TMN_SHEET_ID}

_TIMEOUT_SECONDS = 120
_RETRIES = 3


def fetch_main_table(city: str) -> io.BytesIO:
    """Скачивает актуальную версию главной таблицы города как XLSX.

    Google иногда отвечает медленным экспортом (read timeout) — делаем до
    трёх попыток с паузой, прежде чем сообщить о недоступности. UI должен
    показать ошибку и предложить ручную загрузку файла.
    """
    sheet_id = SHEET_IDS[city]
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    last_exc = None
    for attempt in range(_RETRIES):
        try:
            response = requests.get(url, timeout=_TIMEOUT_SECONDS)
            response.raise_for_status()
            out = io.BytesIO(response.content)
            out.seek(0)
            return out
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < _RETRIES - 1:
                time.sleep(2 * (attempt + 1))
    raise last_exc