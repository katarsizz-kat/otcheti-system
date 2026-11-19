"""
Excel модуля «Работа ОС»: общий отчёт руководителю (одобренный формат,
7 листов, пустые разделы не создаются) и личные книги (2 листа, без
сравнения с коллегой). Палитра и табличные помощники переиспользуются
из модуля «Контроль жалоб» (тёмно-синие заголовки 1F3864, сдержанный
красный для подтверждённых проблем, янтарный для требующего сверки).
"""
from __future__ import annotations

import io
from typing import Dict, List, Optional

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from report.complaints_control.excel import (
    AMBER_FILL,
    DATA_FONT,
    RED_FILL,
    _write_table,
    _write_title,
)

from . import constants as c

RESULT_FILLS = {
    outcome: PatternFill("solid", fgColor=color)
    for outcome, color in c.STATUS_COLORS.items()
}


def _color_result_column(ws, start_row: int, df: pd.DataFrame, header_row: int) -> None:
    if df is None or df.empty or "Результат" not in df.columns:
        return
    col_idx = list(df.columns).index("Результат") + 1
    for i, (_, row) in enumerate(df.iterrows()):
        fill = RESULT_FILLS.get(str(row.get("Результат", "")))
        if fill is not None:
            ws.cell(row=header_row + 1 + i, column=col_idx).fill = fill


def _sheet_has_content(*dfs: pd.DataFrame) -> bool:
    return any(df is not None and not df.empty for df in dfs)


def build_os_work_excel(
    data,
    period_label: str,
    coverage_notes: List[str],
) -> io.BytesIO:
    wb = Workbook()

    # ---------------- ДАШБОРД ----------------
    ws = wb.active
    ws.title = c.SHEET_DASHBOARD
    row = _write_title(ws, 1, f"Проверка работы ОС — {period_label}")
    row += 1
    row = _write_table(ws, row, "Основные показатели", data.dashboard,
                       description="Личные количества включают совместные обращения у обоих "
                                   "участников; скорость относится к фактическому автору ответа. "
                                   "Ориентир среднего — 10 минут.")
    row = _write_table(ws, row, "Группы времени ответа", data.speed_groups)
    row = _write_table(ws, row, "Решение вопроса", data.outcomes,
                       description="Процент решённых = решённые / (решённые + нерешённые "
                                   "с установленным результатом). «Ожидаются данные Гостя» и "
                                   "«Недостаточно данных» в знаменатель не входят.")
    if coverage_notes:
        cell = ws.cell(row=row, column=1, value="Полнота источников:")
        cell.font = Font(name="Calibri", size=10, bold=True, color="1F3864")
        row += 1
        for note in coverage_notes:
            ws.cell(row=row, column=1, value="• " + note).font = DATA_FONT
            row += 1

    # ---------------- ДИНАМИКА И НАГРУЗКА ----------------
    if _sheet_has_content(data.daily, data.hourly, data.weekday, data.joint):
        ws2 = wb.create_sheet(c.SHEET_DYNAMIC)
        row = _write_title(ws2, 1, f"Динамика и нагрузка — {period_label}")
        row += 1
        row = _write_table(ws2, row, "По дням (одна строка на дату)", data.daily)
        weekly = getattr(data, "weekly", None)
        if weekly is not None and not weekly.empty:
            row = _write_table(ws2, row, "По неделям — отдел, Женя, Полина", weekly)
        row = _write_table(ws2, row, "Нагрузка по часам (МСК, до 02:00 = предыдущий день)",
                           data.hourly, description="Считаются сообщения гостей.")
        row = _write_table(ws2, row, "По дням недели", data.weekday)
        row = _write_table(ws2, row, "Совместная работа (дни с ответами обоих сотрудников)", data.joint)

    # ---------------- БЕЗ ОТВЕТА И РЕШЕНИЯ ----------------
    if _sheet_has_content(data.unanswered, data.long_answers, data.next_day,
                          data.old_period_closed, data.old_period_open):
        ws3 = wb.create_sheet(c.SHEET_NO_ANSWER)
        row = _write_title(ws3, 1, f"Без ответа и решения — {period_label}")
        row += 1
        row = _write_table(ws3, row, "Обращения без ответа", data.unanswered, row_fill=RED_FILL)
        row = _write_table(ws3, row, f"Ответ дольше {c.DETAIL_THRESHOLD_MIN} рабочих минут",
                           data.long_answers, row_fill=AMBER_FILL,
                           description="Обращения хотя бы с одним таким ожиданием; максимум и детали.")
        row = _write_table(ws3, row, "Ответили только на следующий день (первый ответ)",
                           data.next_day, description="Ответ через два дня и позже — строки с «Дней до ответа» ≥ 2.")
        row = _write_table(ws3, row, "Ожидания прошлых периодов, закрытые в этом",
                           data.old_period_closed,
                           description="Принадлежат периоду первого вопроса; здесь — справочно.")
        _write_table(ws3, row, "Незавершённые ожидания прошлых периодов",
                     data.old_period_open, row_fill=AMBER_FILL,
                     description="Продолжения, не новые обращения; вопрос задан до начала периода.")

    # ---------------- ЗАМЕЧАНИЯ ----------------
    if _sheet_has_content(data.remarks):
        ws4 = wb.create_sheet(c.SHEET_REMARKS)
        row = _write_title(ws4, 1, f"Замечания — {period_label}")
        row += 1
        _write_table(ws4, row, "Замечания (ручная разметка)", data.remarks, row_fill=RED_FILL)

    # ---------------- НЕ ВНЕСЁННЫЕ ЖАЛОБЫ ----------------
    if _sheet_has_content(data.not_entered, data.probable):
        ws5 = wb.create_sheet(c.SHEET_NOT_ENTERED)
        row = _write_title(ws5, 1, f"Не внесённые жалобы — {period_label}")
        row += 1
        row = _write_table(ws5, row, "Не внесённые жалобы", data.not_entered,
                           description="Из чатов ресторанов Битрикс24, сверка с Google-таблицами "
                                       "(модуль «Контроль жалоб»).", row_fill=RED_FILL)
        _write_table(ws5, row, "Вероятные совпадения — требуют сверки", data.probable,
                     row_fill=AMBER_FILL)

    # ---------------- РАБОТА С РЕСТОРАНАМИ ----------------
    if _sheet_has_content(data.restaurant_work):
        ws6 = wb.create_sheet(c.SHEET_RESTAURANTS)
        row = _write_title(ws6, 1, f"Работа с ресторанами — {period_label}")
        row += 1
        _write_table(ws6, row, "Вопросы ОС ресторанам", data.restaurant_work,
                     description="Изменения текущего заказа не требуют ответа ресторана. "
                                 "«Ответ не найден» в доступных CSV не доказывает молчание.")

    # ---------------- ТРЕБУЕТ ВНИМАНИЯ ----------------
    if _sheet_has_content(data.attention):
        ws7 = wb.create_sheet(c.SHEET_ATTENTION)
        row = _write_title(ws7, 1, f"Требует внимания — {period_label}")
        row += 1
        _write_table(ws7, row, "Требует внимания", data.attention)

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out


def build_personal_excel(
    employee: str,
    personal: Dict[str, pd.DataFrame],
    period_label: str,
) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = c.PERSONAL_SHEET_METRICS
    row = _write_title(ws, 1, f"{employee} — мои показатели — {period_label}")
    row += 1
    _write_table(ws, row, "Показатели", personal["metrics"],
                 description="Совместные обращения учитываются у обоих участников; сравнения "
                             "с коллегой нет. Скорость — по фактическим ответам.")

    ws2 = wb.create_sheet(c.PERSONAL_SHEET_APPEALS)
    row = _write_title(ws2, 1, f"{employee} — обращения и комментарии")
    row += 1
    appeals_df = personal["appeals"]
    header_row = row + 1  # заголовок таблицы после строки описания
    _write_table(ws2, row, "Обращения", appeals_df)
    _color_result_column(ws2, row, appeals_df, header_row)

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out
