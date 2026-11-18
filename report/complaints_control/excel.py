"""
Генерация Excel «Проверка внесения жалоб» по действующим правилам
(ред. 18.11.2026).

Листы (пустые разделы не создаются):
- «Не внесённые жалобы»: только жалобы без подтверждённой записи +
  отдельный блок вероятных совпадений (в счётчик невнесённых не входят);
  колонки: Дата, Сотрудник, Тикеты, Ресторан, Категория жалобы,
  Суть обращения, Телефон Гостя, Результат сверки;
- «Сверка»: полное сопоставление чатов с таблицей по статусам + сводки
  по сотрудникам и ресторанам;
- «Требует внимания»: технические сбои, пропавшие заказы, ранний статус
  «доставлен», недоступные телефоны — не невнесённые жалобы.

Палитра одобренных отчётов: тёмно-синие заголовки с белым текстом,
подтверждённые проблемы — сдержанный красный, требующее сверки — янтарный.
"""
from __future__ import annotations

import io
from typing import Optional

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import constants as c

THIN = Side(style="thin")
THIN_BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

TITLE_FONT = Font(name="Calibri", size=14, bold=True)
SECTION_FONT = Font(name="Calibri", size=12, bold=True, color="1F3864")
DESC_FONT = Font(name="Calibri", size=10, italic=True, color="555555")
DATA_FONT = Font(name="Calibri", size=10)

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT_WHITE = Font(name="Calibri", size=10, bold=True, color="FFFFFF")

RED_FILL = PatternFill("solid", fgColor="F8CBAD")
AMBER_FILL = PatternFill("solid", fgColor="FFE699")

CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)

STATUS_FILLS = {
    status: PatternFill("solid", fgColor=color)
    for status, color in c.STATUS_FILL_COLORS.items()
}


def _clean(val):
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    return val


def _set_widths(ws, columns, sample_rows) -> None:
    for j, colname in enumerate(columns, start=1):
        name = str(colname)
        width = len(name) + 2
        for row in sample_rows:
            try:
                width = max(width, len(str(_clean(row.iloc[j - 1]))) + 2)
            except Exception:
                pass
        if "Текст" in name or "Суть" in name or "Комментарий" in name:
            width = 60
        ws.column_dimensions[get_column_letter(j)].width = min(max(width, 12), 70)


def _write_title(ws, row: int, text: str, font: Font = TITLE_FONT) -> int:
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = font
    return row + 1


def _write_table(
    ws, start_row: int, title: str, df: pd.DataFrame,
    description: Optional[str] = None,
    row_fill: Optional[PatternFill] = None,
    status_colors: bool = False,
) -> int:
    row = _write_title(ws, start_row, title, SECTION_FONT)
    if description:
        cell = ws.cell(row=row, column=1, value=description)
        cell.font = DESC_FONT
        row += 1
    if df is None or df.empty:
        ws.cell(row=row, column=1, value="Нет данных").font = DATA_FONT
        return row + 2

    headers = list(df.columns)
    for j, h in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=j, value=str(h))
        cell.font = HEADER_FONT_WHITE
        cell.fill = HEADER_FILL
        cell.alignment = CENTER
        cell.border = THIN_BORDER

    r = row + 1
    for _, data_row in df.iterrows():
        fill = row_fill
        if status_colors and "Статус" in headers:
            fill = STATUS_FILLS.get(str(data_row.get("Статус", ""))) or row_fill
        for j, h in enumerate(headers, start=1):
            cell = ws.cell(row=r, column=j, value=_clean(data_row[h]))
            cell.font = DATA_FONT
            cell.border = THIN_BORDER
            cell.alignment = LEFT if "Текст" in str(h) or "Суть" in str(h) or j == 1 else CENTER
            if fill is not None:
                cell.fill = fill
        r += 1

    _set_widths(ws, headers, [x[1] for x in df.head(80).iterrows()])
    return r + 2


def build_complaints_control_excel(
    not_entered: pd.DataFrame,
    probable: pd.DataFrame,
    comparison: pd.DataFrame,
    attention: pd.DataFrame,
    employee_share: pd.DataFrame,
    restaurant_summary: pd.DataFrame,
    period_label: str = "",
    no_keys: Optional[pd.DataFrame] = None,
) -> io.BytesIO:
    wb = Workbook()

    # ------------------------------------------------------
    # ЛИСТ 1: НЕ ВНЕСЁННЫЕ ЖАЛОБЫ
    # ------------------------------------------------------
    ws1 = wb.active
    ws1.title = "Не внесённые жалобы"
    row = 1
    if period_label:
        row = _write_title(ws1, row, f"Проверка внесения жалоб — {period_label}")
        row += 1
    row = _write_table(
        ws1, row, "Не внесённые жалобы", not_entered,
        description=(
            "Жалобы из переписки ресторанов без подтверждённой записи в таблице. "
            "«Запись не найдена» требует сверки перед внесением."
        ),
        row_fill=RED_FILL,
    )
    row = _write_table(
        ws1, row, "Вероятные совпадения — требуют сверки", probable,
        description=(
            "Возможная запись найдена по частичным ключам; совпадение требует "
            "сверки. В счётчик невнесённых не входят."
        ),
        row_fill=AMBER_FILL,
    )
    if no_keys is not None and not no_keys.empty:
        row = _write_table(
            ws1, row, "Неполные ключи — ручная проверка", no_keys,
            description="Нет телефона и номера заказа — невнесение не доказано.",
        )

    # ------------------------------------------------------
    # ЛИСТ 2: СВЕРКА (полное сопоставление)
    # ------------------------------------------------------
    if comparison is not None and not comparison.empty:
        ws2 = wb.create_sheet("Сверка")
        row = 1
        if period_label:
            row = _write_title(ws2, row, period_label)
            row += 1
        row = _write_table(ws2, row, "Сопоставление чатов с главной таблицей", comparison,
                           status_colors=True)
        row = _write_table(ws2, row, "% невнесённых по сотруднику", employee_share)
        row = _write_table(ws2, row, "По ресторанам", restaurant_summary)

    # ------------------------------------------------------
    # ЛИСТ 3: ТРЕБУЕТ ВНИМАНИЯ
    # ------------------------------------------------------
    if attention is not None and not attention.empty:
        ws3 = wb.create_sheet("Требует внимания")
        row = 1
        row = _write_table(
            ws3, row, "Требует внимания", attention,
            description=(
                "Технические сбои, пропавшие заказы, недовоз заказа целиком, "
                "ранний статус «доставлен», недоступные телефоны — не невнесённые жалобы."
            ),
        )

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out