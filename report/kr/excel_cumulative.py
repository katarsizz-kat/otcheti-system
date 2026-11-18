# report/kr/excel_cumulative.py

"""
Запись недельных данных в накопительный файл «Клиентский рейтинг».

Режим «NEW неделя»:
- загруженный отчёт прошлой недели дополняется новым недельным листом —
  копией последнего недельного листа (оформление и формулы сохраняются),
  меняются только данные и дата;
- новый лист вставляется перед листом «Сводная по жалобам»;
- в «Сводной по жалобам» обновляется дата (A1) и очищаются ячейки
  counts по ресторанам; формулы и структура сохраняются.

Здесь не должно быть:
- Streamlit;
- бизнес-расчётов (они в stats.py);
- генерации отчёта с нуля (это excel.py).
"""

from __future__ import annotations

import io
from typing import Any, Dict, Optional

import pandas as pd
from openpyxl import load_workbook
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

# ==========================================================
# ИМПОРТ КОНСТАНТ
# ==========================================================
try:
    from . import constants as c
except Exception:
    from report.kr import constants as c

ALL_RESTAURANTS = getattr(c, "ALL_RESTAURANTS", [])
MONTHS_GENITIVE = getattr(c, "MONTHS_GENITIVE", [])

COL_RESTAURANT = getattr(c, "COL_RESTAURANT", "Ресторан")
RATING_COLUMNS = getattr(c, "RATING_COLUMNS", ["1", "2", "3", "4", "5"])
LOW_REVIEW_COLUMN = getattr(c, "LOW_REVIEW_COLUMN", "Отзывы ≤ порог")

BLOCK_TITLE_SITE = getattr(c, "BLOCK_TITLE_SITE", "Сайт/приложение")
BLOCK_TITLE_AGG = getattr(c, "BLOCK_TITLE_AGG", "Агрегаторы")
BLOCK_TITLE_GEO = getattr(c, "BLOCK_TITLE_GEO", "Геосервисы (Я.Карты, 2ГИС, Гугл карты)")

EXCEL_SHEET_SUMMARY = getattr(c, "EXCEL_SHEET_SUMMARY", "Сводная по жалобам")

SOURCE_SITE = getattr(c, "SOURCE_SITE", "site")
SOURCE_AGG = getattr(c, "SOURCE_AGG", "agg")
SOURCE_GEO = getattr(c, "SOURCE_GEO", "geo")

# Колонки недельного листа: C..G — звёзды 1..5, J — низкие отзывы сайта.
STAR_FIRST_COLUMN = 3
LOW_REVIEWS_COLUMN = 10

# Лист «Сводная по жалобам»: B..F — counts по категориям жалоб.
SUMMARY_FIRST_CLEAR_COLUMN = 2
SUMMARY_LAST_CLEAR_COLUMN = 6

SUMMARY_HEADER_LABEL = "ресторан"
SUMMARY_TOTAL_PREFIX = "всего"

MAX_SHEET_TITLE_LENGTH = 31


# ==========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================================
def _norm(value: Any) -> str:
    """
    Нормализует текст ячейки для сравнения: strip + нижний регистр.
    """
    return str(value or "").strip().casefold()


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _capitalize_month(label: str) -> str:
    """
    «1-16 ноября» -> «1-16 Ноября» (как в ячейке B1 образца).
    """
    months = {str(m).casefold() for m in MONTHS_GENITIVE}
    return " ".join(
        word.capitalize() if word.casefold() in months else word
        for word in str(label).split(" ")
    )


def _find_summary_sheet(wb: Workbook) -> Optional[Worksheet]:
    for ws in wb.worksheets:
        if _norm(ws.title) == _norm(EXCEL_SHEET_SUMMARY):
            return ws
    return None


def _has_site_block(ws: Worksheet) -> bool:
    """
    Недельный лист узнаём по заголовку блока «Сайт/приложение» в колонке B.
    """
    for row in range(1, ws.max_row + 1):
        if _norm(ws.cell(row=row, column=2).value) == _norm(BLOCK_TITLE_SITE):
            return True
    return False


def _find_last_weekly_sheet(
    wb: Workbook,
    summary_ws: Worksheet,
) -> Optional[Worksheet]:
    """
    Последний недельный лист перед «Сводной по жалобам».
    """
    summary_index = wb.index(summary_ws)
    for ws in reversed(wb.worksheets[:summary_index]):
        if _has_site_block(ws):
            return ws
    return None


def _collect_block_rows(ws: Worksheet) -> Dict[str, Dict[str, int]]:
    """
    Находит строки ресторанов в каждом блоке (сайт/агрегаторы/гео)
    по заголовкам и именам в колонке B — без хардкода номеров строк.

    Возвращает: {source: {ресторан: номер строки}}.
    """
    blocks: Dict[str, Dict[str, int]] = {
        SOURCE_SITE: {},
        SOURCE_AGG: {},
        SOURCE_GEO: {},
    }
    restaurant_by_norm = {_norm(name): name for name in ALL_RESTAURANTS}

    current_source: Optional[str] = None

    for row in range(1, ws.max_row + 1):
        text = _norm(ws.cell(row=row, column=2).value)
        if not text:
            continue

        if text == _norm(BLOCK_TITLE_SITE):
            current_source = SOURCE_SITE
            continue
        if text == _norm(BLOCK_TITLE_AGG):
            current_source = SOURCE_AGG
            continue
        if text.startswith("геосервисы"):
            current_source = SOURCE_GEO
            continue

        if current_source is None:
            continue

        restaurant = restaurant_by_norm.get(text)
        if restaurant is not None:
            blocks[current_source][restaurant] = row

    return blocks


def _require_full_blocks(blocks: Dict[str, Dict[str, int]]) -> None:
    source_labels = {
        SOURCE_SITE: BLOCK_TITLE_SITE,
        SOURCE_AGG: BLOCK_TITLE_AGG,
        SOURCE_GEO: BLOCK_TITLE_GEO,
    }
    for source, rows in blocks.items():
        missing = [name for name in ALL_RESTAURANTS if name not in rows]
        if missing:
            raise ValueError(
                f"В блоке «{source_labels.get(source, source)}» загруженного "
                f"отчёта не найдены рестораны: {', '.join(missing)}. "
                "Проверьте, что файл соответствует формату «Клиентский рейтинг»."
            )


def _stats_row(stats: Optional[pd.DataFrame], restaurant: str) -> Optional[pd.Series]:
    if stats is None or getattr(stats, "empty", True):
        return None
    subset = stats[stats[COL_RESTAURANT] == restaurant]
    if subset.empty:
        return None
    return subset.iloc[0]


def _write_weekly_data(
    ws: Worksheet,
    blocks: Dict[str, Dict[str, int]],
    report_data: Any,
) -> None:
    """
    Записывает звёзды C:G по каждому источнику и колонку J для сайта.
    Формулы (H, I, общий блок справа) остаются нетронутыми.
    """
    stats_by_source = {
        SOURCE_SITE: getattr(report_data, "stats_site", None),
        SOURCE_AGG: getattr(report_data, "stats_agg", None),
        SOURCE_GEO: getattr(report_data, "stats_geo", None),
    }

    for source, rows in blocks.items():
        stats = stats_by_source.get(source)
        for restaurant, row in rows.items():
            stats_row = _stats_row(stats, restaurant)

            for offset, column_name in enumerate(RATING_COLUMNS):
                value = 0 if stats_row is None else _to_int(stats_row.get(column_name, 0))
                ws.cell(
                    row=row,
                    column=STAR_FIRST_COLUMN + offset,
                    value=value,
                )

            if source == SOURCE_SITE:
                low_value = 0
                if stats_row is not None and LOW_REVIEW_COLUMN in stats_row.index:
                    low_value = _to_int(stats_row[LOW_REVIEW_COLUMN])
                ws.cell(row=row, column=LOW_REVIEWS_COLUMN, value=low_value)


def _update_summary_sheet(ws: Worksheet, date_label: str) -> None:
    """
    Новая дата в A1; ячейки counts B:F очищаются в обоих блоках
    (строки между заголовком «Ресторан» и итогом/пустой строкой).
    Формулы SUM и структура сохраняются.
    """
    ws.cell(row=1, column=1, value=date_label)

    row = 1
    while row <= ws.max_row:
        if _norm(ws.cell(row=row, column=1).value) == SUMMARY_HEADER_LABEL:
            data_row = row + 1
            while data_row <= ws.max_row:
                name = _norm(ws.cell(row=data_row, column=1).value)
                if not name or name.startswith(SUMMARY_TOTAL_PREFIX):
                    break
                for column in range(
                    SUMMARY_FIRST_CLEAR_COLUMN,
                    SUMMARY_LAST_CLEAR_COLUMN + 1,
                ):
                    # value=None в ws.cell() игнорируется openpyxl —
                    # очищаем явным присваиванием.
                    ws.cell(row=data_row, column=column).value = None
                data_row += 1
            row = data_row
        row += 1


# ==========================================================
# ПУБЛИЧНАЯ ФУНКЦИЯ
# ==========================================================
def build_kr_cumulative_excel(
    report_data: Any,
    settings: Any,
    previous_file: Any,
) -> io.BytesIO:
    """
    Дополняет загруженный накопительный отчёт новым недельным листом
    и возвращает обновлённый файл как BytesIO.
    """
    if previous_file is None:
        raise ValueError("Не передан отчёт прошлой недели.")

    period_label = str(getattr(settings, "period_label", "") or "").strip()
    if not period_label:
        raise ValueError("Не определена подпись периода для нового листа.")

    date_label = _capitalize_month(period_label)
    sheet_title = period_label[:MAX_SHEET_TITLE_LENGTH]

    try:
        if hasattr(previous_file, "seek"):
            previous_file.seek(0)
        wb = load_workbook(previous_file)
    except Exception as exc:
        raise ValueError(
            f"Не удалось прочитать отчёт прошлой недели: {exc}"
        ) from exc

    summary_ws = _find_summary_sheet(wb)
    if summary_ws is None:
        raise ValueError(
            f"В загруженном отчёте не найден лист «{EXCEL_SHEET_SUMMARY}». "
            "Загрузите накопительный файл «Клиентский рейтинг»."
        )

    last_weekly_ws = _find_last_weekly_sheet(wb, summary_ws)
    if last_weekly_ws is None:
        raise ValueError(
            "В загруженном отчёте не найден недельный лист с блоком "
            f"«{BLOCK_TITLE_SITE}». Проверьте формат файла."
        )

    if any(_norm(ws.title) == _norm(sheet_title) for ws in wb.worksheets):
        raise ValueError(
            f"Лист «{sheet_title}» уже есть в загруженном отчёте. "
            "Измените подпись периода или даты."
        )

    # Копия последнего недельного листа сохраняет оформление и формулы.
    new_ws = wb.copy_worksheet(last_weekly_ws)
    new_ws.title = sheet_title

    # Вставляем новый лист перед «Сводной по жалобам».
    wb.move_sheet(new_ws, offset=wb.index(summary_ws) - wb.index(new_ws))

    blocks = _collect_block_rows(new_ws)
    _require_full_blocks(blocks)

    new_ws.cell(row=1, column=2, value=date_label)
    _write_weekly_data(new_ws, blocks, report_data)

    _update_summary_sheet(summary_ws, date_label)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
