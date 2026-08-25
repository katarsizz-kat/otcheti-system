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
# СРЕДНИЙ РЕЙТИНГ ПО РЕСТОРАНАМ (из отзывов: сайт/агрегаторы/гео)
# ==========================================================
def calc_avg_rating_summary(reviews: pd.DataFrame) -> pd.DataFrame:
    """Средний рейтинг и количество оценок по ресторану. Итоги — взвешенное среднее, не сумма."""
    rows = []
    for rest in ALL_RESTAURANTS:
        sub = reviews[reviews[COL_RESTAURANT] == rest] if reviews is not None and not reviews.empty else pd.DataFrame()
        ratings = sub["Рейтинг"].dropna() if not sub.empty and "Рейтинг" in sub.columns else pd.Series(dtype=float)
        rows.append({
            COL_RESTAURANT: rest,
            "Средний рейтинг": round(float(ratings.mean()), 2) if len(ratings) else None,
            "Кол-во оценок": int(len(ratings)),
        })
    summary = pd.DataFrame(rows)

    def _weighted_total(label: str, subset: List[str]) -> Dict[str, object]:
        part = summary[summary[COL_RESTAURANT].isin(subset)]
        total_count = int(part["Кол-во оценок"].sum())
        avg = None
        if total_count:
            avg = round((part["Средний рейтинг"].fillna(0) * part["Кол-во оценок"]).sum() / total_count, 2)
        return {COL_RESTAURANT: label, "Средний рейтинг": avg, "Кол-во оценок": total_count}

    spb_part = summary[summary[COL_RESTAURANT].isin(SPB_ORDER)]
    tmn_part = summary[summary[COL_RESTAURANT].isin(TMN_ORDER)]
    return pd.concat([
        spb_part,
        pd.DataFrame([_weighted_total("Всего СПб:", SPB_ORDER)]),
        tmn_part,
        pd.DataFrame([_weighted_total("Всего Тюмень:", TMN_ORDER)]),
    ], ignore_index=True)


# ==========================================================
# ДОЛЯ КАТЕГОРИЙ ОТ ОБЩЕГО ЧИСЛА ЖАЛОБ РЕСТОРАНА (%)
# ==========================================================
def calc_complaint_share_summary(complaint_summary: pd.DataFrame) -> pd.DataFrame:
    """То же, что «Сводная по жалобам», но категории — в процентах от «Всего:» строки."""
    if complaint_summary is None or complaint_summary.empty:
        return complaint_summary
    out = complaint_summary.copy()
    for cat in COMPLAINT_CATEGORIES:
        if cat not in out.columns:
            continue
        out[cat] = [
            round(row[cat] / row[TOTAL_COL] * 100, 1) if row.get(TOTAL_COL) else 0.0
            for _, row in out.iterrows()
        ]
    return out


# ==========================================================
# ТОП ПРОБЛЕМНЫХ РЕСТОРАНОВ
# ==========================================================
def calc_top_restaurants(complaint_summary: pd.DataFrame) -> pd.DataFrame:
    """Рестораны, отсортированные по убыванию общего числа жалоб."""
    if complaint_summary is None or complaint_summary.empty:
        return pd.DataFrame(columns=["№", COL_RESTAURANT, TOTAL_COL])
    only_restaurants = complaint_summary[complaint_summary[COL_RESTAURANT].isin(ALL_RESTAURANTS)]
    ranked = only_restaurants[[COL_RESTAURANT, TOTAL_COL]].sort_values(
        TOTAL_COL, ascending=False
    ).reset_index(drop=True)
    ranked.insert(0, "№", ranked.index + 1)
    return ranked


# ==========================================================
# ИТОГОВАЯ СВОДКА (executive summary)
# ==========================================================
def calc_report_overview(
    complaints: pd.DataFrame,
    reviews: pd.DataFrame,
    complaint_summary: pd.DataFrame,
    positive_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Пара строк-показателей наверх отчёта: сколько всего, откуда, какая категория чаще всего."""
    total_complaints = int(len(complaints)) if complaints is not None else 0
    total_reviews = int(len(reviews)) if reviews is not None else 0

    complaints_from_reviews = 0
    if complaints is not None and not complaints.empty and COL_SOURCE in complaints.columns:
        complaints_from_reviews = int(
            complaints[complaints[COL_SOURCE].isin(["Сайт", "Агрегаторы", "Геосервисы"])].shape[0]
        )
    share = round(complaints_from_reviews / total_reviews * 100, 1) if total_reviews else None

    top_category, top_count = None, 0
    if complaint_summary is not None and not complaint_summary.empty:
        only_rest = complaint_summary[complaint_summary[COL_RESTAURANT].isin(ALL_RESTAURANTS)]
        for cat in COMPLAINT_CATEGORIES:
            if cat not in only_rest.columns:
                continue
            total = int(only_rest[cat].sum())
            if total > top_count:
                top_count, top_category = total, cat

    total_positive = 0
    if positive_summary is not None and not positive_summary.empty and TOTAL_COL in positive_summary.columns:
        only_rest_pos = positive_summary[positive_summary[COL_RESTAURANT].isin(ALL_RESTAURANTS)]
        total_positive = int(only_rest_pos[TOTAL_COL].sum())

    rows = [
        {"Показатель": "Всего жалоб (все источники)", "Значение": total_complaints},
        {"Показатель": "Жалоб из отзывов (сайт/агрегаторы/гео)", "Значение": complaints_from_reviews},
        {"Показатель": "Доля жалоб от всех отзывов, %", "Значение": share if share is not None else "—"},
        {"Показатель": "Всего позитивных моментов в отзывах", "Значение": total_positive},
        {
            "Показатель": "Самая частая категория жалоб",
            "Значение": f"{top_category} ({top_count})" if top_category else "—",
        },
    ]
    return pd.DataFrame(rows)


# ==========================================================
# КОМПЕНСАЦИИ (без сумм — только количество обращений)
# ==========================================================
RESOLUTION_COL = "Решение"
STATUS_COL = "Статус возмещения"
EMPLOYEE_COL = "Сотрудник"


def calc_resolution_summary(complaints: pd.DataFrame) -> pd.DataFrame:
    """Сколько жалоб закрыто каждым типом решения (баллы/купон/возврат и т.п.), по ресторанам.
    Суммы компенсаций сознательно не считаем — только количество обращений."""
    if complaints is None or complaints.empty or RESOLUTION_COL not in complaints.columns:
        return pd.DataFrame(columns=[COL_RESTAURANT, TOTAL_COL])

    with_resolution = complaints[
        complaints[RESOLUTION_COL].notna() & (complaints[RESOLUTION_COL].astype(str).str.strip() != "")
    ]
    if with_resolution.empty:
        return pd.DataFrame(columns=[COL_RESTAURANT, TOTAL_COL])

    resolution_types = sorted(with_resolution[RESOLUTION_COL].astype(str).str.strip().unique().tolist())

    rows = []
    for rest in ALL_RESTAURANTS:
        sub = with_resolution[with_resolution[COL_RESTAURANT] == rest]
        row = {COL_RESTAURANT: rest}
        for rtype in resolution_types:
            row[rtype] = int((sub[RESOLUTION_COL].astype(str).str.strip() == rtype).sum())
        row[TOTAL_COL] = int(len(sub))
        rows.append(row)

    summary = pd.DataFrame(rows)
    return _add_totals(summary, resolution_types)


def calc_unresolved_complaints(complaints: pd.DataFrame) -> pd.DataFrame:
    """Обращения через ОС, которые ещё не обработаны (Статус возмещения = False) — список к дозакрытию."""
    cols = ["Дата", COL_RESTAURANT, COL_TYPE, COL_TEXT, COL_SOURCE, EMPLOYEE_COL]
    if complaints is None or complaints.empty or STATUS_COL not in complaints.columns:
        return pd.DataFrame(columns=cols)

    unresolved = complaints[complaints[STATUS_COL] == False]  # noqa: E712 — явное сравнение с bool, не с truthy
    if unresolved.empty:
        return pd.DataFrame(columns=cols)

    out = unresolved[[col for col in cols if col in unresolved.columns]].copy()
    return out.sort_values("Дата") if "Дата" in out.columns else out


def calc_no_compensation_complaints(complaints: pd.DataFrame) -> pd.DataFrame:
    """Обращения с решением «без компенсации» — та же форма, что «Необработанные обращения»,
    но для проверки: обосновано ли решение не компенсировать."""
    cols = ["Дата", COL_RESTAURANT, COL_TYPE, COL_TEXT, COL_SOURCE, EMPLOYEE_COL]
    if complaints is None or complaints.empty or RESOLUTION_COL not in complaints.columns:
        return pd.DataFrame(columns=cols)

    resolution_norm = complaints[RESOLUTION_COL].astype(str).str.strip().str.lower()
    subset = complaints[resolution_norm.str.startswith("без комп")]
    if subset.empty:
        return pd.DataFrame(columns=cols)

    out = subset[[col for col in cols if col in subset.columns]].copy()
    return out.sort_values("Дата") if "Дата" in out.columns else out


# ==========================================================
# СВОДНЫЕ ПО ИСТОЧНИКАМ
# ==========================================================
OS_SOURCE_LABELS = ["ОС", "ОС Тюмень"]


def calc_stats_by_source(complaints: pd.DataFrame, reviews: pd.DataFrame) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Считает сводные по каждому источнику отдельно.
    ОС (СПб) и ОС Тюмень объединены в один источник «ОС и компенсации» — это один
    канал, а не два. Позитив для него не считаем — это не отзывы, там нет рейтинга.
    Возвращает dict: {source: {"complaint_summary": df, "positive_summary": df|None}}
    """
    result = {}

    os_mask = complaints[COL_SOURCE].isin(OS_SOURCE_LABELS) if complaints is not None else None
    os_complaints = complaints[os_mask] if os_mask is not None else pd.DataFrame()
    result["ОС и компенсации"] = {
        "complaint_summary": calc_complaint_summary(os_complaints),
        "positive_summary": None,
    }

    for source in ("Сайт", "Агрегаторы", "Геосервисы"):
        source_complaints = complaints[complaints[COL_SOURCE] == source] if complaints is not None else pd.DataFrame()
        source_reviews = reviews[reviews[COL_SOURCE] == source] if reviews is not None else pd.DataFrame()
        result[source] = {
            "complaint_summary": calc_complaint_summary(source_complaints),
            "positive_summary": calc_positive_summary(source_reviews),
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

    avg_rating_summary = calc_avg_rating_summary(reviews)
    complaint_share_summary = calc_complaint_share_summary(complaint_summary)
    top_restaurants = calc_top_restaurants(complaint_summary)
    report_overview = calc_report_overview(complaints, reviews, complaint_summary, positive_summary)
    resolution_summary = calc_resolution_summary(complaints)
    unresolved_complaints = calc_unresolved_complaints(complaints)
    no_compensation_complaints = calc_no_compensation_complaints(complaints)

    return {
        "complaints": complaints,
        "duplicates": duplicates,
        "complaint_summary": complaint_summary,
        "positive_summary": positive_summary,
        "main_categories_summary": main_categories_summary,
        "extended_categories_summary": extended_categories_summary,
        "by_source": by_source,
        "avg_rating_summary": avg_rating_summary,
        "complaint_share_summary": complaint_share_summary,
        "top_restaurants": top_restaurants,
        "report_overview": report_overview,
        "resolution_summary": resolution_summary,
        "unresolved_complaints": unresolved_complaints,
        "no_compensation_complaints": no_compensation_complaints,
    }