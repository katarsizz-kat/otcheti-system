
"""
Расчётный модуль КР.

Ответственность файла:
- расчёт статистики оценок по ресторанам;
- расчёт среднего рейтинга;
- расчёт количества отзывов ниже порога (только для месяца);
- анализ отзывов по ключевым словам (жалобы и позитив);
- добавление итоговых строк по регионам (СПб и Тюмень);
- сборка полного расчётного отчёта из подготовленных данных.

Здесь не должно быть:
- Streamlit;
- чтения файлов;
- генерации Excel;
- маппинга ресторанов (это делает data.py).
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

# ==========================================================
# ИМПОРТ КОНСТАНТ
# ==========================================================
try:
    from . import constants as c
except Exception:
    from report.kr import constants as c

# ==========================================================
# ИМПОРТ МОДЕЛЕЙ
# ==========================================================
try:
    from .models import KRPreparedData, KRReportData, KRReportSettings
except Exception:
    from report.kr.models import KRPreparedData, KRReportData, KRReportSettings


# ==========================================================
# ЛОКАЛЬНЫЕ ССЫЛКИ НА КОНСТАНТЫ
# ==========================================================
ALL_RESTAURANTS = getattr(c, "ALL_RESTAURANTS", [])
SPB_ORDER = getattr(c, "SPB_ORDER", [])
TMN_ORDER = getattr(c, "TMN_ORDER", [])

COL_RESTAURANT = getattr(c, "COL_RESTAURANT", "Ресторан")
COL_RATING = getattr(c, "COL_RATING", "Рейтинг")
COL_TEXT = getattr(c, "COL_TEXT", "Текст")
COL_SUM = getattr(c, "COL_SUM", "Сумма")

TOTAL_COLUMN = getattr(c, "TOTAL_COLUMN", "всего:")
AVG_COLUMN = getattr(c, "AVG_COLUMN", "Средний рейтинг")
LOW_REVIEW_COLUMN = getattr(c, "LOW_REVIEW_COLUMN", "Отзывы ≤ порог")

DEFAULT_PRICE_THRESHOLD = getattr(c, "DEFAULT_PRICE_THRESHOLD", 749)

COMPLAINT_KEYWORDS = getattr(c, "COMPLAINT_KEYWORDS", {})
POSITIVE_KEYWORDS = getattr(c, "POSITIVE_KEYWORDS", {})

ANALYSIS_TOTAL_COLUMN = getattr(c, "ANALYSIS_TOTAL_COLUMN", "Всего:")
ANALYSIS_RESTAURANT_COLUMN = getattr(c, "ANALYSIS_RESTAURANT_COLUMN", "Ресторан")

CITY_SPB = getattr(c, "CITY_SPB", "СПб")
CITY_TMN = getattr(c, "CITY_TMN", "Тюмень")


# ==========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================================
def _weighted_avg(counts: Dict[int, int], total: int) -> float:
    """Средневзвешенный рейтинг по оценкам 1–5."""
    if total <= 0:
        return 0.0
    return round(sum(i * counts.get(i, 0) for i in range(1, 6)) / total, 2)


def _make_empty_stats(with_low: bool = False) -> pd.DataFrame:
    """Пустой DataFrame статистики с нулями для всех ресторанов."""
    rows = []
    for restaurant in ALL_RESTAURANTS:
        row = {COL_RESTAURANT: restaurant}
        for i in range(1, 6):
            row[str(i)] = 0
        row[TOTAL_COLUMN] = 0
        row[AVG_COLUMN] = 0.0
        if with_low:
            row[LOW_REVIEW_COLUMN] = 0
        rows.append(row)
    return pd.DataFrame(rows)


def _make_empty_analysis(keywords_dict: Dict[str, str]) -> pd.DataFrame:
    """Пустой DataFrame анализа с нулями для всех ресторанов."""
    rows = []
    for restaurant in ALL_RESTAURANTS:
        row = {COL_RESTAURANT: restaurant}
        for category in keywords_dict.keys():
            row[category] = 0
        row[ANALYSIS_TOTAL_COLUMN] = 0
        rows.append(row)
    return pd.DataFrame(rows)


# ==========================================================
# РАСЧЁТ СТАТИСТИКИ ОЦЕНОК
# ==========================================================
def calc_stats_site(df: pd.DataFrame, threshold: int) -> pd.DataFrame:
    """
    Статистика по сайту с учётом порога суммы заказа.

    Отзывы с рейтингом 5 и суммой <= порога считаются отдельно
    в колонке LOW_REVIEW_COLUMN и исключаются из основного расчёта.
    """
    if df.empty or COL_RATING not in df.columns:
        return _make_empty_stats(with_low=True)

    results = []
    for restaurant in ALL_RESTAURANTS:
        sub = df[df[COL_RESTAURANT] == restaurant].copy()

        # Определяем низкие отзывы (5 звёзд, сумма <= порога)
        if COL_SUM in sub.columns:
            low_mask = (sub[COL_RATING] == 5) & (sub[COL_SUM] <= threshold)
        else:
            low_mask = pd.Series(False, index=sub.index)

        low_count = int(low_mask.sum())

        # Исключаем низкие отзывы из основного расчёта
        sub_filtered = sub[~low_mask]

        counts = {i: int((sub_filtered[COL_RATING] == i).sum()) for i in range(1, 6)}
        total = sum(counts.values())

        row = {COL_RESTAURANT: restaurant}
        for i in range(1, 6):
            row[str(i)] = counts[i]
        row[TOTAL_COLUMN] = total
        row[AVG_COLUMN] = _weighted_avg(counts, total)
        row[LOW_REVIEW_COLUMN] = low_count

        results.append(row)

    return pd.DataFrame(results)


def calc_stats_standard(df: pd.DataFrame) -> pd.DataFrame:
    """
    Стандартная статистика оценок без учёта порога.
    Используется для агрегаторов, геосервиса и недельного отчёта.
    """
    if df.empty or COL_RATING not in df.columns:
        return _make_empty_stats(with_low=False)

    results = []
    for restaurant in ALL_RESTAURANTS:
        sub = df[df[COL_RESTAURANT] == restaurant]

        counts = {i: int((sub[COL_RATING] == i).sum()) for i in range(1, 6)}
        total = sum(counts.values())

        row = {COL_RESTAURANT: restaurant}
        for i in range(1, 6):
            row[str(i)] = counts[i]
        row[TOTAL_COLUMN] = total
        row[AVG_COLUMN] = _weighted_avg(counts, total)

        results.append(row)

    return pd.DataFrame(results)


# ==========================================================
# АНАЛИЗ ОТЗЫВОВ ПО КЛЮЧЕВЫМ СЛОВАМ
# ==========================================================
def calc_summary_fast(df: pd.DataFrame, keywords_dict: Dict[str, str]) -> pd.DataFrame:
    """
    Быстрый векторизованный анализ отзывов по ключевым словам.
    """
    if df.empty or COL_TEXT not in df.columns:
        return _make_empty_analysis(keywords_dict)

    results = []
    for restaurant in ALL_RESTAURANTS:
        sub = df[df[COL_RESTAURANT] == restaurant]
        counts = {category: 0 for category in keywords_dict.keys()}

        if not sub.empty:
            texts = sub[COL_TEXT].fillna("").astype(str)
            for category, pattern in keywords_dict.items():
                counts[category] = int(
                    texts.str.contains(pattern, case=False, na=False, regex=True).sum()
                )

        row = {COL_RESTAURANT: restaurant}
        row.update(counts)
        row[ANALYSIS_TOTAL_COLUMN] = sum(counts.values())
        results.append(row)

    return pd.DataFrame(results)


def add_summary_totals(
    df: pd.DataFrame,
    region: str,
    keywords_dict: Dict[str, str],
) -> pd.DataFrame:
    """
    Добавляет итоговую строку 'Всего {region}:' по заданному региону.
    """
    if region == CITY_SPB:
        subset = df[df[COL_RESTAURANT].isin(SPB_ORDER)]
    else:
        subset = df[df[COL_RESTAURANT].isin(TMN_ORDER)]

    total_row = {ANALYSIS_RESTAURANT_COLUMN: f"Всего {region}:"}
    for category in keywords_dict.keys():
        total_row[category] = int(subset[category].sum())
    total_row[ANALYSIS_TOTAL_COLUMN] = sum(
        total_row[category] for category in keywords_dict.keys()
    )

    return pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)


# ==========================================================
# ОСНОВНАЯ ФУНКЦИЯ РАСЧЁТА
# ==========================================================
def calculate_report_data(
    prepared: KRPreparedData,
    settings: KRReportSettings,
) -> KRReportData:
    """
    Собирает полный расчётный отчёт из подготовленных данных.

    Логика:
    - Месяц: сайт считается с порогом, низкие отзывы исключаются
      из оценок, но учитываются в анализе отзывов.
    - Неделя: все источники считаются без порога.
    """
    threshold = DEFAULT_PRICE_THRESHOLD
    if settings.month is not None:
        threshold = settings.month.price_threshold

    # ------------------------------------------------------
    # 1. Статистика по каждому источнику
    # ------------------------------------------------------
    if settings.is_month:
        stats_site = calc_stats_site(prepared.site, threshold)
    else:
        stats_site = calc_stats_standard(prepared.site)

    stats_agg = calc_stats_standard(prepared.agg)
    stats_geo = calc_stats_standard(prepared.geo)

    # ------------------------------------------------------
    # 2. Общий итог по оценкам
    # ------------------------------------------------------
    # Для месяца из оценок сайта исключаем низкие отзывы
    if settings.is_month and COL_SUM in prepared.site.columns:
        site_for_ratings = prepared.site[
            ~((prepared.site[COL_RATING] == 5) & (prepared.site[COL_SUM] <= threshold))
        ][[COL_RESTAURANT, COL_RATING, COL_TEXT]]
    else:
        site_for_ratings = prepared.site[[COL_RESTAURANT, COL_RATING, COL_TEXT]]

    df_all_ratings = pd.concat(
        [
            site_for_ratings,
            prepared.agg[[COL_RESTAURANT, COL_RATING, COL_TEXT]],
            prepared.geo[[COL_RESTAURANT, COL_RATING, COL_TEXT]],
        ],
        ignore_index=True,
    )

    stats_all = calc_stats_standard(df_all_ratings)

    # Для месяца добавляем колонку "Отзывы ≤ порог" в общий итог
    if settings.is_month:
        low_map = dict(zip(stats_site[COL_RESTAURANT], stats_site[LOW_REVIEW_COLUMN]))
        stats_all[LOW_REVIEW_COLUMN] = (
            stats_all[COL_RESTAURANT].map(low_map).fillna(0).astype(int)
        )

    # ------------------------------------------------------
    # 3. Анализ отзывов (жалобы и позитив)
    # ------------------------------------------------------
    # Для анализа используем ВСЕ тексты, включая низкие отзывы сайта
    df_all_texts = pd.concat(
        [
            prepared.site[[COL_RESTAURANT, COL_TEXT]],
            prepared.agg[[COL_RESTAURANT, COL_TEXT]],
            prepared.geo[[COL_RESTAURANT, COL_TEXT]],
        ],
        ignore_index=True,
    )

    complaints = calc_summary_fast(df_all_texts, COMPLAINT_KEYWORDS)
    positives = calc_summary_fast(df_all_texts, POSITIVE_KEYWORDS)

    complaints = add_summary_totals(complaints, CITY_SPB, COMPLAINT_KEYWORDS)
    complaints = add_summary_totals(complaints, CITY_TMN, COMPLAINT_KEYWORDS)

    positives = add_summary_totals(positives, CITY_SPB, POSITIVE_KEYWORDS)
    positives = add_summary_totals(positives, CITY_TMN, POSITIVE_KEYWORDS)

    return KRReportData(
        stats_site=stats_site,
        stats_agg=stats_agg,
        stats_geo=stats_geo,
        stats_all=stats_all,
        complaints=complaints,
        positives=positives,
    )