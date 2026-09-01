# report/orders_plan.py

"""
Расчёт плана по количеству заказов на произвольный целевой месяц/период,
по каждому ресторану сети.

Источник данных — помесячная история заказов по ресторанам (см. load_history).

Логика расчёта (для каждого целевого календарного месяца):
1. Основной метод — сезонный коэффициент:
     коэфф = заказы(тот же месяц, год назад) / заказы(предыдущий месяц, год назад)
     прогноз = заказы(последний доступный факт перед целевым месяцем) × коэфф
   Если данных "год назад" больше одного года — коэффициент считается как
   среднее по всем доступным годам для этого календарного месяца.
2. Проверочный метод — линейный тренд (OLS) по всей доступной истории,
   экстраполированный на целевой месяц.
3. Если для сезонного коэффициента нет данных (мало истории, новый ресторан,
   слишком длинный горизонт вперёд) — план строится по тренду (fallback).
4. Отклонение прогноза (метод 1) от тренда (метод 2) в % — при |отклонении|
   больше DEVIATION_WARNING_THRESHOLD ресторан помечается needs_review=True.

Модуль не зависит от Streamlit и не привязан к конкретному способу
получения исходного файла — на вход годится путь, file-like объект или
уже загруженный DataFrame (см. load_history).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, List, Optional, Sequence, Union

import pandas as pd

# ==========================================================
# КОНСТАНТЫ
# ==========================================================

MONTHS_RU = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]

# "09 (Сентябрь) 2025", "08 (Август) 2025г", "9(сентябрь)2025" и т.п.
_HEADER_RE = re.compile(
    r"(?P<month_num>\d{1,2})\s*\(\s*[А-Яа-яЁё]+\s*\)\s*(?P<year>\d{4})"
)

RESTAURANT_COLUMN_LABELS = {"торговое предприятие", "ресторан", "точка"}
TOTAL_MARKERS = {"итого", "итог", "всего"}

# группа №1 — явный номер после "№"; группа №2 — число в самом названии
# (напр. "Тюмень 2. Орджоникидзе"); группа №3 — номера нет вовсе
_NUM_MARK_RE = re.compile(r"№\s*0*(\d+)")
_NUM_FALLBACK_RE = re.compile(r"(?<!\d)0*(\d+)(?!\d)")

DEVIATION_WARNING_THRESHOLD = 0.15  # 15%

TargetPeriod = Union[str, date, tuple, Sequence]


# ==========================================================
# ЗАГРУЗКА И НОРМАЛИЗАЦИЯ ИСТОРИИ
# ==========================================================

def parse_month_header(label: Any) -> Optional[date]:
    """
    Парсит подпись столбца-месяца (например "09 (Сентябрь) 2025" или
    "08 (Август) 2025г") в дату первого числа месяца.

    Год и номер месяца берутся из самой подписи, а не из положения
    столбца — порядок столбцов в файле может быть произвольным.
    """
    if not isinstance(label, str):
        return None
    match = _HEADER_RE.search(label)
    if not match:
        return None
    month_num = int(match.group("month_num"))
    year = int(match.group("year"))
    if not 1 <= month_num <= 12:
        return None
    return date(year, month_num, 1)


def _find_header_row(raw: pd.DataFrame) -> int:
    """Строка с наибольшим числом распознанных подписей-месяцев — шапка таблицы."""
    best_row, best_score = None, 0
    for idx in range(len(raw)):
        score = sum(parse_month_header(v) is not None for v in raw.iloc[idx])
        if score > best_score:
            best_row, best_score = idx, score
    if best_row is None:
        raise ValueError("Не найдена строка-шапка с подписями месяцев вида '09 (Сентябрь) 2025'.")
    return best_row


def load_history(source: Union[str, pd.DataFrame, Any], sheet_name: Union[int, str] = 0) -> pd.DataFrame:
    """
    Читает файл истории заказов (путь/буфер/DataFrame) и приводит его
    к длинному формату: restaurant | period (date, 1-е число месяца) | orders.

    Строки/столбцы "Итого" отбрасываются. Месяцы сортируются по реальной
    дате, а не по исходному порядку столбцов.
    """
    if isinstance(source, pd.DataFrame):
        raw = source
    else:
        raw = pd.read_excel(source, sheet_name=sheet_name, header=None)

    header_row = _find_header_row(raw)
    header = raw.iloc[header_row]

    month_columns: List[tuple] = []
    for col_idx, label in header.items():
        period = parse_month_header(label)
        if period is not None:
            month_columns.append((col_idx, period))
    if not month_columns:
        raise ValueError("В шапке файла не найдено ни одного столбца с месяцем.")

    restaurant_col = header.index[0]

    body = raw.iloc[header_row + 1:]
    records = []
    for _, row in body.iterrows():
        name = row[restaurant_col]
        if not isinstance(name, str) or not name.strip():
            continue
        if name.strip().lower() in TOTAL_MARKERS:
            continue
        for col_idx, period in month_columns:
            value = row[col_idx]
            if pd.isna(value):
                continue
            records.append({"restaurant": name.strip(), "period": period, "orders": float(value)})

    history = pd.DataFrame.from_records(records, columns=["restaurant", "period", "orders"])
    history = history.sort_values(["restaurant", "period"]).reset_index(drop=True)
    return history


# ==========================================================
# СОРТИРОВКА РЕСТОРАНОВ
# ==========================================================

def restaurant_sort_key(name: str):
    """
    Сначала рестораны с явным номером "№N" (по возрастанию N), затем
    рестораны без "№", но с числом в названии (напр. "Тюмень 2..."),
    тоже по возрастанию числа; всё остальное — в конец, по алфавиту.

    Правило легко расширяется: новый город/формат с числом в названии
    автоматически попадёт во вторую группу и встанет в ней по номеру.
    """
    match = _NUM_MARK_RE.search(name)
    if match:
        return (0, int(match.group(1)), name)
    match = _NUM_FALLBACK_RE.search(name)
    if match:
        return (1, int(match.group(1)), name)
    return (2, 0, name)


def sort_restaurants(names: Iterable[str]) -> List[str]:
    return sorted(set(names), key=restaurant_sort_key)


# ==========================================================
# ЦЕЛЕВОЙ ПЕРИОД
# ==========================================================

def _shift_months(d: date, months: int) -> date:
    total = (d.year * 12 + (d.month - 1)) + months
    year, month = divmod(total, 12)
    return date(year, month + 1, 1)


def _to_month_date(value: Any) -> date:
    if isinstance(value, date):
        return date(value.year, value.month, 1)
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"\d{4}-\d{1,2}", text):
            year, month = text.split("-")
            return date(int(year), int(month), 1)
        parsed = pd.to_datetime(text)
        return date(parsed.year, parsed.month, 1)
    if isinstance(value, tuple) and len(value) == 2:
        year, month = value
        return date(int(year), int(month), 1)
    raise ValueError(f"Не удалось разобрать целевой период: {value!r}")


def resolve_target_months(target_period: TargetPeriod) -> List[date]:
    """
    Приводит целевой период к списку дат (1-е число каждого месяца).

    Принимает: "2026-09", date(2026, 9, 1), (2026, 9), диапазон
    "2026-09:2026-11", (start, end) или список/множество месяцев.
    """
    if isinstance(target_period, str) and ":" in target_period:
        start_raw, end_raw = target_period.split(":", 1)
        start, end = _to_month_date(start_raw), _to_month_date(end_raw)
        months, cur = [], start
        while cur <= end:
            months.append(cur)
            cur = _shift_months(cur, 1)
        return months

    if isinstance(target_period, (list, set)):
        return sorted({_to_month_date(v) for v in target_period})

    if isinstance(target_period, tuple) and len(target_period) == 2 and all(
        isinstance(v, (date, str)) for v in target_period
    ):
        start, end = _to_month_date(target_period[0]), _to_month_date(target_period[1])
        months, cur = [], start
        while cur <= end:
            months.append(cur)
            cur = _shift_months(cur, 1)
        return months

    return [_to_month_date(target_period)]


# ==========================================================
# РАСЧЁТ ПРОГНОЗА ДЛЯ ОДНОГО РЕСТОРАНА / ОДНОГО МЕСЯЦА
# ==========================================================

@dataclass
class MonthForecast:
    restaurant: str
    target_period: date
    method: str  # "seasonal" | "trend_only" | "insufficient_data"
    base_period: Optional[date] = None
    base_orders: Optional[float] = None
    seasonal_coef: Optional[float] = None
    seasonal_years_used: int = 0
    forecast_seasonal: Optional[float] = None
    forecast_trend: Optional[float] = None
    deviation_pct: Optional[float] = None
    plan: Optional[float] = None
    needs_review: bool = False
    warning: Optional[str] = None

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["target_period"] = self.target_period.isoformat()
        d["base_period"] = self.base_period.isoformat() if self.base_period else None
        return d


def _seasonal_coefficient(series: pd.Series, target: date) -> tuple:
    """
    series: index=period(date) -> orders, для одного ресторана.
    Возвращает (коэфф или None, число учтённых лет).
    """
    ratios = []
    k = 1
    max_k = target.year - series.index.min().year + 1 if len(series) else 0
    while k <= max_k:
        same = _shift_months(target, -12 * k)
        prev = _shift_months(same, -1)
        if same in series.index and prev in series.index and series[prev]:
            ratios.append(series[same] / series[prev])
        k += 1
    if not ratios:
        return None, 0
    return sum(ratios) / len(ratios), len(ratios)


def _linear_trend(series: pd.Series, target: date) -> Optional[float]:
    """OLS-тренд по всей истории ресторана, экстраполированный на target."""
    if len(series) < 2:
        return None
    base = series.index.min()
    x = [(d.year - base.year) * 12 + (d.month - base.month) for d in series.index]
    y = list(series.values)
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    denom = sum((xi - mean_x) ** 2 for xi in x)
    if denom == 0:
        return mean_y
    slope = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / denom
    intercept = mean_y - slope * mean_x
    target_x = (target.year - base.year) * 12 + (target.month - base.month)
    return intercept + slope * target_x


def forecast_restaurant_month(
    series: pd.Series,
    restaurant: str,
    target: date,
    deviation_threshold: float = DEVIATION_WARNING_THRESHOLD,
) -> MonthForecast:
    """series: index=period(date) -> orders, только для одного ресторана, отсортирован."""
    past = series[series.index < target]
    base_period = past.index.max() if len(past) else None
    base_orders = float(past[base_period]) if base_period is not None else None

    trend = _linear_trend(series, target)
    coef, years_used = _seasonal_coefficient(series, target)

    if coef is not None and base_orders is not None:
        forecast_seasonal = base_orders * coef
        deviation_pct = None
        if trend:
            deviation_pct = (forecast_seasonal / trend - 1) * 100
        return MonthForecast(
            restaurant=restaurant,
            target_period=target,
            method="seasonal",
            base_period=base_period,
            base_orders=base_orders,
            seasonal_coef=coef,
            seasonal_years_used=years_used,
            forecast_seasonal=forecast_seasonal,
            forecast_trend=trend,
            deviation_pct=deviation_pct,
            plan=forecast_seasonal,
            needs_review=bool(deviation_pct is not None and abs(deviation_pct) > deviation_threshold * 100),
        )

    if trend is not None:
        return MonthForecast(
            restaurant=restaurant,
            target_period=target,
            method="trend_only",
            base_period=base_period,
            base_orders=base_orders,
            forecast_trend=trend,
            plan=trend,
            warning="Нет данных для сезонного коэффициента — план построен по тренду.",
        )

    return MonthForecast(
        restaurant=restaurant,
        target_period=target,
        method="insufficient_data",
        base_period=base_period,
        base_orders=base_orders,
        plan=base_orders,
        warning="Недостаточно истории для расчёта тренда или сезонности.",
    )


# ==========================================================
# ПУБЛИЧНЫЙ API
# ==========================================================

def build_plan(
    history: pd.DataFrame,
    target_period: TargetPeriod,
    restaurants: Optional[Iterable[str]] = None,
    deviation_threshold: float = DEVIATION_WARNING_THRESHOLD,
) -> dict:
    """
    history: DataFrame со столбцами restaurant | period(date) | orders — см. load_history().
    target_period: см. resolve_target_months() — один месяц, диапазон или список месяцев.
    restaurants: ограничить расчёт списком ресторанов (по умолчанию — все из history).

    Возвращает JSON-совместимый словарь:
      {
        "target_months": [...],
        "restaurants": [ {restaurant, months: [MonthForecast...], plan: сумма по периоду}, ... ],
        "total": {"plan": ..., "needs_review_count": ...},
      }
    """
    target_months = resolve_target_months(target_period)

    all_names = restaurants if restaurants is not None else history["restaurant"].unique()
    ordered_names = sort_restaurants(all_names)

    restaurant_results = []
    grand_total = 0.0
    needs_review_count = 0

    for name in ordered_names:
        series = (
            history.loc[history["restaurant"] == name]
            .drop_duplicates("period", keep="last")
            .set_index("period")["orders"]
            .sort_index()
        )

        month_forecasts = [
            forecast_restaurant_month(series, name, month, deviation_threshold)
            for month in target_months
        ]

        plan_sum = sum(mf.plan for mf in month_forecasts if mf.plan is not None)
        review_flag = any(mf.needs_review for mf in month_forecasts)
        needs_review_count += int(review_flag)
        grand_total += plan_sum

        restaurant_results.append({
            "restaurant": name,
            "plan": plan_sum,
            "needs_review": review_flag,
            "months": [mf.to_dict() for mf in month_forecasts],
        })

    return {
        "target_months": [m.isoformat() for m in target_months],
        "restaurants": restaurant_results,
        "total": {
            "plan": grand_total,
            "restaurant_count": len(ordered_names),
            "needs_review_count": needs_review_count,
        },
    }


def plan_to_dataframe(plan: dict) -> pd.DataFrame:
    """
    Разворачивает результат build_plan() в плоский DataFrame — по строке
    на пару (ресторан, целевой месяц). Удобно для предпросмотра/экспорта.
    """
    rows = []
    for entry in plan["restaurants"]:
        for month in entry["months"]:
            rows.append({"restaurant": entry["restaurant"], **month})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["restaurant"] = pd.Categorical(
            df["restaurant"],
            categories=sort_restaurants(df["restaurant"].unique()),
            ordered=True,
        )
        df = df.sort_values(["restaurant", "target_period"]).reset_index(drop=True)
    return df


if __name__ == "__main__":
    import json
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "заказов.xlsx"
    target = sys.argv[2] if len(sys.argv) > 2 else "2026-09"

    hist = load_history(path)
    result = build_plan(hist, target)
    print(json.dumps(result, ensure_ascii=False, indent=2))
