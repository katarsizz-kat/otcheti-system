"""
Сводные таблицы проверки внесения жалоб: лист «Не внесённые жалобы»,
доли по сотрудникам/ресторанам, статистика классификации.
Чистая агрегация pandas, без Streamlit/openpyxl.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd

from . import constants as c

# Колонки листа «Не внесённые жалобы» (действующие правила + столбец
# «Телефон Гостя» по уточнению 17.11.2026).
NOT_ENTERED_COLS = [
    "Дата", "Сотрудник", "Тикеты", "Ресторан", "Категория жалобы",
    "Суть обращения", "Телефон Гостя", "Результат сверки",
]


def _by_status(comparison: pd.DataFrame, status: str) -> pd.DataFrame:
    if comparison is None or comparison.empty:
        return pd.DataFrame(columns=NOT_ENTERED_COLS)
    scoped = comparison[comparison["Статус"] == status]
    if scoped.empty:
        return pd.DataFrame(columns=NOT_ENTERED_COLS)
    out = scoped.copy()
    for col in NOT_ENTERED_COLS:
        if col not in out.columns:
            out[col] = ""
    return out[NOT_ENTERED_COLS].reset_index(drop=True)


def build_not_entered(comparison: pd.DataFrame) -> pd.DataFrame:
    """Только жалобы без подтверждённой записи — счётчик невнесённых."""
    return _by_status(comparison, c.STATUS_NOT_ENTERED)


def build_probable(comparison: pd.DataFrame) -> pd.DataFrame:
    """Вероятные совпадения — отдельным блоком, в счётчик не входят."""
    return _by_status(comparison, c.STATUS_PROBABLE)


def build_no_keys(comparison: pd.DataFrame) -> pd.DataFrame:
    return _by_status(comparison, c.STATUS_NO_KEYS)


def build_employee_not_entered_share(comparison: pd.DataFrame) -> pd.DataFrame:
    cols = ["Сотрудник", "Всего жалоб", "Не внесено", "% не внесено"]
    if comparison is None or comparison.empty:
        return pd.DataFrame(columns=cols)
    df = comparison[comparison["Сотрудник"].notna() & (comparison["Сотрудник"] != "")]
    if df.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for employee, grp in df.groupby("Сотрудник"):
        total = len(grp)
        not_entered = int((grp["Статус"] == c.STATUS_NOT_ENTERED).sum())
        rows.append({
            "Сотрудник": employee,
            "Всего жалоб": total,
            "Не внесено": not_entered,
            "% не внесено": round(100 * not_entered / total, 1) if total else 0.0,
        })
    return pd.DataFrame(rows, columns=cols).sort_values("% не внесено", ascending=False)


def build_restaurant_summary(comparison: pd.DataFrame) -> pd.DataFrame:
    cols = ["Ресторан", "Всего жалоб", "Не внесено", "% не внесено"]
    if comparison is None or comparison.empty:
        return pd.DataFrame(columns=cols)
    df = comparison[comparison["Ресторан"].notna() & (comparison["Ресторан"] != "")]
    if df.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for rest, grp in df.groupby("Ресторан"):
        total = len(grp)
        not_entered = int((grp["Статус"] == c.STATUS_NOT_ENTERED).sum())
        rows.append({
            "Ресторан": rest,
            "Всего жалоб": total,
            "Не внесено": not_entered,
            "% не внесено": round(100 * not_entered / total, 1) if total else 0.0,
        })
    return pd.DataFrame(rows, columns=cols).sort_values("% не внесено", ascending=False)


def build_classification_preview(label_counts: Dict[str, Dict[str, int]]) -> pd.DataFrame:
    """Сколько сообщений/групп прогнано через классификатор и почему часть
    не признана жалобой — здесь заметны побочные эффекты правил."""
    rows = []
    for source, counts in label_counts.items():
        total = sum(counts.values())
        complaints = (
            counts.get("quality", 0) + counts.get("delay", 0)
            + counts.get("delay_promo", 0) + counts.get("compensation", 0)
        )
        rows.append({
            "Источник": source,
            "Всего групп": total,
            "Признано жалобой": complaints,
            "Опоздания (промокод за задержку)": counts.get("delay_promo", 0),
            "Требует внимания (техсбои)": counts.get("attention", 0),
            "Недовоз целиком (не жалоба)": counts.get("not_delivered", 0),
            "Изменения заказа": counts.get("logistics", 0),
            "Лояльность/промокоды": counts.get("loyalty", 0),
            "Дни рождения": counts.get("birthday", 0),
            "Похвала": counts.get("praise", 0),
            "Нейтральные/возвраты": counts.get("neutral", 0),
            "Не определено": counts.get("not_determined", 0),
        })
    return pd.DataFrame(rows)