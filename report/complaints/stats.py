"""
Статистика отчёта «Анализ жалоб».
Считает:
- сводная «Жалобы»: ресторан x категория;
- сводная «Позитив»: ресторан x категория;
- сводная по 5 основным категориям жалоб;
- сводная по 10 расширенным категориям жалоб;
- сводные по каждому источнику отдельно.
Дедупликация уже сделана в data.py, здесь только статистика.
Не использует Streamlit.
"""
from __future__ import annotations
import re
from typing import Dict, List
import pandas as pd

try:
    from . import constants as c
except Exception:
    from report.complaints import constants as c

# ----------------------------------------------------------
# КОНСТАНТЫ (с фолбэками)
# ----------------------------------------------------------
COMPLAINT_KEYWORDS = getattr(c, "COMPLAINT_KEYWORDS", {})
POSITIVE_KEYWORDS = getattr(c, "POSITIVE_KEYWORDS", {})
COMPLAINT_CATEGORIES = getattr(c, "COMPLAINT_CATEGORIES", list(COMPLAINT_KEYWORDS.keys()))
SPB_ORDER = getattr(c, "SPB_ORDER", [])
TMN_ORDER = getattr(c, "TMN_ORDER", [])
ALL_RESTAURANTS = getattr(c, "ALL_RESTAURANTS", SPB_ORDER + TMN_ORDER)

# Расширенные категории (10 шт)
EXTENDED_COMPLAINT_CATEGORIES = getattr(c, "EXTENDED_COMPLAINT_CATEGORIES", [])
EXTENDED_COMPLAINT_KEYWORDS = getattr(c, "EXTENDED_COMPLAINT_KEYWORDS", {})

# Колонки подготовленных данных
COL_SOURCE = "Источник"
COL_RESTAURANT = "Ресторан"
COL_TEXT = "Текст"
COL_TYPE = "Вид жалобы"
TOTAL_COL = "Всего:"

# 5 основных категорий жалоб для первой страницы
MAIN_COMPLAINT_CATEGORIES = [
    "Жалоба на продукт",
    "Ошибки в приготовлении",
    "Перепутанные/недоложенные позиции",
    "Жалобы на сервис",
    "Опоздание",
]

# Маппинг для приведения к основным категориям
CATEGORY_NORMALIZE = {
    "жалоба на продукт": "Жалоба на продукт",
    "жалобы на продукт": "Жалоба на продукт",
    "ошибки в приготовлении": "Ошибки в приготовлении",
    "ошибки приготовления": "Ошибки в приготовлении",
    "ошибка в приготовлении": "Ошибки в приготовлении",
    "перепутанные/недоложенные позиции": "Перепутанные/недоложенные позиции",
    "перепутанные/недовезенные позиции": "Перепутанные/недоложенные позиции",
    "жалобы на сервис": "Жалобы на сервис",
    "жалоба на сервис": "Жалобы на сервис",
    "опоздание": "Опоздание",
    "опоздания": "Опоздание",
}


# ==========================================================
# СВОДНАЯ: ресторан x категория
# ==========================================================
def _summary_by_restaurant(
    df: pd.DataFrame,
    categories: List[str],
    count_col: str,
) -> pd.DataFrame:
    """Считает количество жалоб/позитива по каждому ресторану и категории."""
    rows = []
    for rest in ALL_RESTAURANTS:
        sub = df[df[COL_RESTAURANT] == rest]
        row = {COL_RESTAURANT: rest}
        for cat in categories:
            row[cat] = int((sub[count_col] == cat).sum()) if count_col else 0
        row[TOTAL_COL] = int(len(sub))
        rows.append(row)
    return pd.DataFrame(rows)


def _add_totals(summary: pd.DataFrame, categories: List[str]) -> pd.DataFrame:
    """Добавляет строки итогов по СПб и Тюмени."""
    out = summary.copy()
    spb = out[out[COL_RESTAURANT].isin(SPB_ORDER)]
    tmn = out[out[COL_RESTAURANT].isin(TMN_ORDER)]

    spb_total = {COL_RESTAURANT: "Всего СПб:"}
    tmn_total = {COL_RESTAURANT: "Всего Тюмень:"}

    for cat in categories + [TOTAL_COL]:
        spb_total[cat] = int(spb[cat].sum())
        tmn_total[cat] = int(tmn[cat].sum())

    # Вставляем итоги после СПб и после Тюмени
    spb_part = out[out[COL_RESTAURANT].isin(SPB_ORDER)]
    tmn_part = out[out[COL_RESTAURANT].isin(TMN_ORDER)]

    result = pd.concat([
        spb_part,
        pd.DataFrame([spb_total]),
        tmn_part,
        pd.DataFrame([tmn_total]),
    ], ignore_index=True)

    return result


def calc_complaint_summary(complaints: pd.DataFrame) -> pd.DataFrame:
    """Сводная жалоб: ресторан x категория."""
    if complaints is None or complaints.empty:
        rows = []
        for rest in ALL_RESTAURANTS:
            row = {COL_RESTAURANT: rest}
            for cat in COMPLAINT_CATEGORIES:
                row[cat] = 0
            row[TOTAL_COL] = 0
            rows.append(row)
        summary = pd.DataFrame(rows)
        return _add_totals(summary, COMPLAINT_CATEGORIES)

    summary = _summary_by_restaurant(complaints, COMPLAINT_CATEGORIES, COL_TYPE)
    return _add_totals(summary, COMPLAINT_CATEGORIES)


def calc_positive_summary(reviews: pd.DataFrame) -> pd.DataFrame:
    """Сводная позитива: ресторан x категория (str.contains)."""
    rows = []
    for rest in ALL_RESTAURANTS:
        sub = reviews[reviews[COL_RESTAURANT] == rest] if reviews is not None else pd.DataFrame()
        row = {COL_RESTAURANT: rest}
        total = 0
        for cat, pattern in POSITIVE_KEYWORDS.items():
            cnt = 0
            if sub is not None and not sub.empty:
                try:
                    cnt = int(sub[COL_TEXT].str.contains(pattern, case=False, na=False, regex=True).sum())
                except Exception:
                    cnt = 0
            row[cat] = cnt
            total += cnt
        row[TOTAL_COL] = total
        rows.append(row)

    summary = pd.DataFrame(rows)
    return _add_totals(summary, list(POSITIVE_KEYWORDS.keys()))


# ==========================================================
# СВОДНАЯ ПО 5 ОСНОВНЫМ КАТЕГОРИЯМ
# ==========================================================
def _normalize_category(cat: str) -> str:
    """Приводит категорию к основному виду."""
    if not cat:
        return ""
    cat_lower = cat.strip().lower()
    return CATEGORY_NORMALIZE.get(cat_lower, cat)


def calc_main_categories_summary(complaints: pd.DataFrame) -> pd.DataFrame:
    """Сводная по 5 основным категориям жалоб."""
    if complaints is None or complaints.empty:
        rows = []
        for rest in ALL_RESTAURANTS:
            row = {COL_RESTAURANT: rest}
            for cat in MAIN_COMPLAINT_CATEGORIES:
                row[cat] = 0
            row[TOTAL_COL] = 0
            rows.append(row)
        summary = pd.DataFrame(rows)
        return _add_totals(summary, MAIN_COMPLAINT_CATEGORIES)

    # Нормализуем категории
    complaints_copy = complaints.copy()
    complaints_copy["Категория_осн"] = complaints_copy[COL_TYPE].map(_normalize_category)

    rows = []
    for rest in ALL_RESTAURANTS:
        sub = complaints_copy[complaints_copy[COL_RESTAURANT] == rest]
        row = {COL_RESTAURANT: rest}
        for cat in MAIN_COMPLAINT_CATEGORIES:
            row[cat] = int((sub["Категория_осн"] == cat).sum())
        row[TOTAL_COL] = int(len(sub))
        rows.append(row)

    summary = pd.DataFrame(rows)
    return _add_totals(summary, MAIN_COMPLAINT_CATEGORIES)


# ==========================================================
# СВОДНАЯ ПО 10 РАСШИРЕННЫМ КАТЕГОРИЯМ
# ==========================================================
def calc_extended_categories_summary(complaints: pd.DataFrame) -> pd.DataFrame:
    """
    Сводная по 10 расширенным категориям жалоб.
    Классифицирует жалобы по регулярным выражениям из EXTENDED_COMPLAINT_KEYWORDS.
    """
    if not EXTENDED_COMPLAINT_CATEGORIES or not EXTENDED_COMPLAINT_KEYWORDS:
        # Если расширенные категории не определены — возвращаем пустую таблицу
        rows = []
        for rest in ALL_RESTAURANTS:
            row = {COL_RESTAURANT: rest}
            for cat in EXTENDED_COMPLAINT_CATEGORIES:
                row[cat] = 0
            row[TOTAL_COL] = 0
            rows.append(row)
        summary = pd.DataFrame(rows)
        return _add_totals(summary, EXTENDED_COMPLAINT_CATEGORIES)

    if complaints is None or complaints.empty:
        rows = []
        for rest in ALL_RESTAURANTS:
            row = {COL_RESTAURANT: rest}
            for cat in EXTENDED_COMPLAINT_CATEGORIES:
                row[cat] = 0
            row[TOTAL_COL] = 0
            rows.append(row)
        summary = pd.DataFrame(rows)
        return _add_totals(summary, EXTENDED_COMPLAINT_CATEGORIES)

    rows = []
    for rest in ALL_RESTAURANTS:
        sub = complaints[complaints[COL_RESTAURANT] == rest]
        row = {COL_RESTAURANT: rest}

        for cat, pattern in EXTENDED_COMPLAINT_KEYWORDS.items():
            cnt = 0
            if sub is not None and not sub.empty:
                try:
                    cnt = int(sub[COL_TEXT].str.contains(pattern, case=False, na=False, regex=True).sum())
                except Exception:
                    cnt = 0
            row[cat] = cnt

        row[TOTAL_COL] = int(len(sub))
        rows.append(row)

    summary = pd.DataFrame(rows)
    return _add_totals(summary, EXTENDED_COMPLAINT_CATEGORIES)


# ==========================================================
# СВОДНЫЕ ПО ИСТОЧНИКАМ
# ==========================================================
def calc_stats_by_source(complaints: pd.DataFrame, reviews: pd.DataFrame) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Считает сводные по каждому источнику отдельно.
    Возвращает dict: {source: {"complaint_summary": df, "positive_summary": df}}
    """
    sources = ["ОС", "Сайт", "Агрегаторы", "Геосервисы"]
    result = {}

    for source in sources:
        # Жалобы по источнику
        source_complaints = complaints[complaints[COL_SOURCE] == source] if complaints is not None else pd.DataFrame()
        complaint_summary = calc_complaint_summary(source_complaints)

        # Позитив по источнику
        source_reviews = reviews[reviews[COL_SOURCE] == source] if reviews is not None else pd.DataFrame()
        positive_summary = calc_positive_summary(source_reviews)

        result[source] = {
            "complaint_summary": complaint_summary,
            "positive_summary": positive_summary,
        }

    return result


# ==========================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ==========================================================
def build_complaints_stats(prepared) -> Dict[str, pd.DataFrame]:
    """
    Собирает всю статистику.
    Ожидает prepared с полями:
    - reviews: отзывы (Источник, Ресторан, Рейтинг, Текст, Телефон, Дата)
    - complaints: жалобы без дублей (уже дедуплицированы в data.py)
    - duplicates: дубликаты (уже найдены в data.py)
    """
    reviews = getattr(prepared, "reviews", None)
    complaints = getattr(prepared, "complaints", None)
    duplicates = getattr(prepared, "duplicates", None)

    # Считаем сводные
    complaint_summary = calc_complaint_summary(complaints)
    positive_summary = calc_positive_summary(reviews)
    main_categories_summary = calc_main_categories_summary(complaints)
    extended_categories_summary = calc_extended_categories_summary(complaints)
    by_source = calc_stats_by_source(complaints, reviews)

    return {
        "complaints": complaints,
        "duplicates": duplicates,
        "complaint_summary": complaint_summary,
        "positive_summary": positive_summary,
        "main_categories_summary": main_categories_summary,
        "extended_categories_summary": extended_categories_summary,
        "by_source": by_source,
    }