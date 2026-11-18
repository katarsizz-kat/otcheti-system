# tests/test_kr_new_week.py

"""
Тесты режима «NEW неделя» (накопительный файл «Клиентский рейтинг»).

Запуск: python tests/test_kr_new_week.py

Данные синтетические: реальные выгрузки и отчёты в репозиторий не попадают.
"""

from __future__ import annotations

import io
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from openpyxl import Workbook, load_workbook

from report.kr import constants as c
from report.kr.excel_cumulative import _capitalize_month, build_kr_cumulative_excel
from report.kr.models import (
    KRPreparedData,
    KRReportRequest,
    KRReportSettings,
    KRSourceFiles,
    KRWeekSettings,
)
from report.kr.stats import calculate_report_data

SPB_NAMES = [
    "Транспортный", "Димитрова ", "Шмидта", "Пулковская",
    "Благодатная", "Энтузиастов ", "Серебристый ", "Мурино",
    "Ветеранов", "Туристская ", "Наука", "Ленинский",
]
TMN_NAMES = ["Орджоникидзе", "Мельникайте"]

SITE_ROWS_SPB = list(range(6, 18))
SITE_ROWS_TMN = [23, 24]
AGG_ROWS_SPB = list(range(37, 49))
AGG_ROWS_TMN = [54, 55]
GEO_ROWS_SPB = list(range(68, 80))
GEO_ROWS_TMN = [85, 86]

SUMMARY_SPB_NAMES = [
    "01 Транспортный", "02 Димитрова", "04 Соверен", "05 Пулковская",
    "06 Благодатная", "07 Энтузиастов", "08 Серибристый", "13 Мурино",
    "15 Ветеранов", "16 Туристская", "18 Науки", "20 Ленинский",
]
SUMMARY_TMN_NAMES = ["ТМН 2", "ТМН 3"]


# ==========================================================
# СИНТЕТИЧЕСКИЙ НАКОПИТЕЛЬНЫЙ ФАЙЛ (структура как в образце)
# ==========================================================
def _write_weekly_sheet(ws, date_label: str) -> None:
    ws["B1"] = date_label
    ws["L1"] = "=B1"
    ws["B2"] = c.BLOCK_TITLE_SITE
    ws["L2"] = c.BLOCK_TITLE_COMMON

    blocks = (
        (2, SITE_ROWS_SPB, SITE_ROWS_TMN, 19, 27, True),
        (33, AGG_ROWS_SPB, AGG_ROWS_TMN, 50, 58, False),
        (64, GEO_ROWS_SPB, GEO_ROWS_TMN, 81, 89, False),
    )

    for title_row, spb_rows, tmn_rows, spb_total, tmn_total, with_low in blocks:
        if title_row != 2:
            ws.cell(row=title_row - 1, column=2, value="=B1")
        ws.cell(row=title_row, column=2, value=(
            c.BLOCK_TITLE_SITE if title_row == 2
            else c.BLOCK_TITLE_AGG if title_row == 33
            else c.BLOCK_TITLE_GEO
        ))

        for header_row, rows in ((title_row + 3, spb_rows), (title_row + 20, tmn_rows)):
            ws.cell(row=header_row, column=2, value="СПБ" if rows is spb_rows else "Тюмень")
            for offset, star in enumerate(c.RATING_COLUMNS):
                ws.cell(row=header_row, column=3 + offset, value=star)

        for row in spb_rows + tmn_rows:
            name = (SPB_NAMES + TMN_NAMES)[
                (spb_rows + tmn_rows).index(row)
            ]
            ws.cell(row=row, column=2, value=name)
            for col in range(3, 8):
                ws.cell(row=row, column=col, value=1)
            ws.cell(row=row, column=8, value=f"=SUM(C{row}:G{row})")
            ws.cell(
                row=row, column=9,
                value=f"=(C{row}*1+D{row}*2+E{row}*3+F{row}*4+G{row}*5)/H{row}",
            )
            if with_low:
                ws.cell(row=row, column=10, value=1)

        for total_row, rows in ((spb_total, spb_rows), (tmn_total, tmn_rows)):
            ws.cell(row=total_row, column=2, value="Итого:")
            first, last = rows[0], rows[-1]
            for col in range(3, 8):
                letter = chr(ord("C") + col - 3)
                ws.cell(row=total_row, column=col, value=f"=SUM({letter}{first}:{letter}{last})")

    # Общий блок справа (формулы, как в образце)
    for row in SITE_ROWS_SPB + SITE_ROWS_TMN:
        ws.cell(row=row, column=12, value=ws.cell(row=row, column=2).value)
        for col in range(13, 18):
            letter = chr(ord("C") + col - 13)
            ws.cell(
                row=row, column=col,
                value=f"={letter}{row}+{letter}{row + 31}+{letter}{row + 62}",
            )
        ws.cell(row=row, column=18, value=f"=SUM(M{row}:Q{row})")


def _write_summary_sheet(ws, date_label: str) -> None:
    ws["A1"] = date_label
    headers = ["Ресторан"] + list(c.COMPLAINT_KEYWORDS.keys()) + ["Всего:"]

    for header_row, names, start_row in (
        (2, SUMMARY_SPB_NAMES, 3),
        (21, SUMMARY_TMN_NAMES, 22),
    ):
        for col, title in enumerate(headers, start=1):
            ws.cell(row=header_row, column=col, value=title)
        for offset, name in enumerate(names):
            row = start_row + offset
            ws.cell(row=row, column=1, value=name)
            for col in range(2, 7):
                ws.cell(row=row, column=col, value=1)
            ws.cell(row=row, column=7, value=f"=SUM(B{row}:F{row})")

    ws["A16"] = "Всего:"
    ws["B16"] = "=SUM(B3:B15)"
    ws["A19"] = "Тюмень"
    ws["A20"] = "=A1"
    ws["A25"] = "Всего:"
    ws["B25"] = "=SUM(B22:B24)"


def make_previous_workbook() -> io.BytesIO:
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "1-8 ноября"
    _write_weekly_sheet(ws1, "1-8 Ноября")

    ws2 = wb.copy_worksheet(ws1)
    ws2.title = "1-15 ноября "
    ws2["B1"] = "1-15 Ноября"

    _write_summary_sheet(wb.create_sheet(c.EXCEL_SHEET_SUMMARY), "1-15 Ноября")

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def make_report_data() -> SimpleNamespace:
    """
    Синтетическая статистика: у ресторана с индексом i
    звёзды = i+1..i+5, низких отзывов = i.
    """
    def stats(with_low: bool) -> pd.DataFrame:
        rows = []
        for i, name in enumerate(c.ALL_RESTAURANTS):
            row = {c.COL_RESTAURANT: name}
            for star in range(1, 6):
                row[str(star)] = i + star
            if with_low:
                row[c.LOW_REVIEW_COLUMN] = i
            rows.append(row)
        return pd.DataFrame(rows)

    return SimpleNamespace(
        stats_site=stats(True),
        stats_agg=stats(False),
        stats_geo=stats(False),
    )


def make_settings(label: str = "") -> KRReportSettings:
    return KRReportSettings(
        mode=c.MODE_NEW_WEEK,
        week=KRWeekSettings(
            use_period=True,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 15),
            custom_label=label,
        ),
    )


# ==========================================================
# ТЕСТЫ
# ==========================================================
def test_models_new_week() -> None:
    settings = make_settings()
    assert settings.is_new_week
    assert settings.is_week, "NEW неделя должна наследовать недельное поведение"
    assert not settings.is_month
    assert settings.period_label == "1-15 ноября", settings.period_label
    assert settings.file_name == "Клиентский рейтинг 1-15 ноября.xlsx", settings.file_name
    assert settings.week_filter_period == (date(2026, 11, 1), date(2026, 11, 15))

    custom = make_settings("1-16 ноября")
    assert custom.period_label == "1-16 ноября"
    assert custom.file_name == "Клиентский рейтинг 1-16 ноября.xlsx"

    files = KRSourceFiles(site=object(), agg=object(), geo=object())
    request = KRReportRequest(files=files, settings=settings)
    try:
        request.validate()
    except ValueError as exc:
        assert "прошлой недели" in str(exc)
    else:
        raise AssertionError("validate() должен требовать отчёт прошлой недели")

    files.previous = object()
    KRReportRequest(files=files, settings=settings).validate()


def test_stats_threshold_new_week() -> None:
    site = pd.DataFrame([
        {c.COL_RESTAURANT: "Транспортный", c.COL_RATING: 5, c.COL_TEXT: "ок", c.COL_SUM: 500},
        {c.COL_RESTAURANT: "Транспортный", c.COL_RATING: 5, c.COL_TEXT: "ок", c.COL_SUM: 800},
        {c.COL_RESTAURANT: "Транспортный", c.COL_RATING: 4, c.COL_TEXT: "ок", c.COL_SUM: 300},
        {c.COL_RESTAURANT: "Транспортный", c.COL_RATING: 1, c.COL_TEXT: "плохо", c.COL_SUM: 100},
    ])
    empty = pd.DataFrame(columns=[c.COL_RESTAURANT, c.COL_RATING, c.COL_TEXT])
    prepared = KRPreparedData(site=site, agg=empty, geo=empty)

    data = calculate_report_data(prepared, make_settings())
    row = data.stats_site[data.stats_site[c.COL_RESTAURANT] == "Транспортный"].iloc[0]
    assert row[c.LOW_REVIEW_COLUMN] == 1, "5★ ≤ 749 должен попасть в колонку J"
    assert row["5"] == 1, "дешёвая пятёрка должна быть исключена из оценок"
    assert row["4"] == 1 and row["1"] == 1

    all_row = data.stats_all[data.stats_all[c.COL_RESTAURANT] == "Транспортный"].iloc[0]
    assert all_row["5"] == 1, "общий итог тоже должен исключать дешёвые пятёрки"

    # Обычная неделя не изменилась: порога нет, все пятёрки на месте.
    week_settings = KRReportSettings(
        mode=c.MODE_WEEK,
        week=KRWeekSettings(use_period=False),
    )
    week_data = calculate_report_data(prepared, week_settings)
    week_row = week_data.stats_site[
        week_data.stats_site[c.COL_RESTAURANT] == "Транспортный"
    ].iloc[0]
    assert week_row["5"] == 2
    assert c.LOW_REVIEW_COLUMN not in week_data.stats_site.columns


def test_writer_new_sheet() -> None:
    settings = make_settings("1-16 ноября")
    result = build_kr_cumulative_excel(make_report_data(), settings, make_previous_workbook())
    wb = load_workbook(result)

    assert wb.sheetnames == [
        "1-8 ноября", "1-15 ноября ", "1-16 ноября", c.EXCEL_SHEET_SUMMARY,
    ], wb.sheetnames

    ws = wb["1-16 ноября"]
    assert ws["B1"].value == "1-16 Ноября"
    assert ws["L1"].value == "=B1"
    assert ws["B32"].value == "=B1"

    # Транспортный — индекс 0: звёзды 1..5, низких 0.
    assert [ws.cell(row=6, column=col).value for col in range(3, 8)] == [1, 2, 3, 4, 5]
    assert ws.cell(row=6, column=10).value == 0
    # Димитрова — индекс 1: звёзды 2..6, низких 1.
    assert [ws.cell(row=7, column=col).value for col in range(3, 8)] == [2, 3, 4, 5, 6]
    assert ws.cell(row=7, column=10).value == 1
    # Агрегаторы и геосервисы тоже записаны.
    assert ws.cell(row=37, column=3).value == 1
    assert ws.cell(row=68, column=3).value == 1
    # Тюмень.
    assert ws.cell(row=23, column=3).value == 13

    # Формулы сохранены.
    assert ws["H6"].value == "=SUM(C6:G6)"
    assert ws["M6"].value == "=C6+C37+C68"
    assert ws["R6"].value == "=SUM(M6:Q6)"

    # Старые листы не тронуты.
    old = wb["1-8 ноября"]
    assert old["B1"].value == "1-8 Ноября"
    assert old["C6"].value == 1
    assert wb["1-15 ноября "]["B1"].value == "1-15 Ноября"


def test_writer_summary_cleared() -> None:
    settings = make_settings("1-16 ноября")
    result = build_kr_cumulative_excel(make_report_data(), settings, make_previous_workbook())
    ws = load_workbook(result)[c.EXCEL_SHEET_SUMMARY]

    assert ws["A1"].value == "1-16 Ноября"
    for row in list(range(3, 15)) + [22, 23]:
        for col in range(2, 7):
            assert ws.cell(row=row, column=col).value is None, (row, col)
    # Формулы и структура на месте.
    assert ws["G3"].value == "=SUM(B3:F3)"
    assert ws["B16"].value == "=SUM(B3:B15)"
    assert ws["A20"].value == "=A1"
    assert ws["A3"].value == "01 Транспортный"
    assert ws["A22"].value == "ТМН 2"


def test_writer_errors() -> None:
    # Лист с таким периодом уже есть (сравнение без пробелов по краям).
    try:
        build_kr_cumulative_excel(
            make_report_data(), make_settings("1-15 ноября"), make_previous_workbook()
        )
    except ValueError as exc:
        assert "уже есть" in str(exc)
    else:
        raise AssertionError("ожидалась ошибка про существующий лист")

    # Файл без «Сводной по жалобам».
    wb = Workbook()
    _write_weekly_sheet(wb.active, "1-8 Ноября")
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    try:
        build_kr_cumulative_excel(make_report_data(), make_settings("1-16 ноября"), buffer)
    except ValueError as exc:
        assert "Сводная по жалобам" in str(exc)
    else:
        raise AssertionError("ожидалась ошибка про отсутствие Сводной")


def test_capitalize_month() -> None:
    assert _capitalize_month("1-16 ноября") == "1-16 Ноября"
    assert _capitalize_month("30 сентября – 5 октября") == "30 Сентября – 5 Октября"
    assert _capitalize_month("Все даты") == "Все даты"


def main() -> None:
    tests = [
        test_models_new_week,
        test_stats_threshold_new_week,
        test_writer_new_sheet,
        test_writer_summary_cleared,
        test_writer_errors,
        test_capitalize_month,
    ]
    for test in tests:
        test()
        print(f"OK  {test.__name__}")
    print(f"\nВсе тесты пройдены: {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    main()
