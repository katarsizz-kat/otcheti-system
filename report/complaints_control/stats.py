"""
Сводные таблицы и 5 метрик листа 4 — ТЗ §6 (лист 3), §7 (лист 4).
Принимает уже загруженные/сопоставленные таблицы, чистая агрегация pandas.
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from . import constants as c

BACKLOG_STATUSES = {"В ожидании", "Открыт", "В очереди"}
_NO_COMPENSATION_LABELS = {"", "без компенсации"}


# ============================================================
# ЛИСТ 3: СВОД
# ============================================================
def build_not_entered_all(comparison_chats: pd.DataFrame, comparison_issues: pd.DataFrame) -> pd.DataFrame:
    parts = [df[df["Статус"] == c.STATUS_NOT_ENTERED] for df in (comparison_chats, comparison_issues) if df is not None and not df.empty]
    if not parts:
        return pd.DataFrame(columns=comparison_chats.columns if comparison_chats is not None else [])
    return pd.concat(parts, ignore_index=True)


def build_no_phone_all(comparison_chats: pd.DataFrame, comparison_issues: pd.DataFrame) -> pd.DataFrame:
    parts = [df[df["Статус"] == c.STATUS_NO_PHONE] for df in (comparison_chats, comparison_issues) if df is not None and not df.empty]
    if not parts:
        return pd.DataFrame(columns=comparison_chats.columns if comparison_chats is not None else [])
    return pd.concat(parts, ignore_index=True)


def build_employee_not_entered_share(comparison_chats: pd.DataFrame) -> pd.DataFrame:
    """% незанесённых по сотруднику — только чаты (issues_report даёт
    очередь/отдел, не человека, см. ТЗ §6, лист 3)."""
    cols = ["Сотрудник", "Всего обращений", "Не занесено", "% не занесено"]
    if comparison_chats is None or comparison_chats.empty:
        return pd.DataFrame(columns=cols)
    df = comparison_chats[comparison_chats["Сотрудник"].notna() & (comparison_chats["Сотрудник"] != "")]
    if df.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for employee, grp in df.groupby("Сотрудник"):
        total = len(grp)
        not_entered = int((grp["Статус"] == c.STATUS_NOT_ENTERED).sum())
        rows.append({
            "Сотрудник": employee,
            "Всего обращений": total,
            "Не занесено": not_entered,
            "% не занесено": round(100 * not_entered / total, 1) if total else 0.0,
        })
    return pd.DataFrame(rows, columns=cols).sort_values("% не занесено", ascending=False)


def build_restaurant_summary(comparison_chats: pd.DataFrame, comparison_issues: pd.DataFrame) -> pd.DataFrame:
    cols = ["Ресторан (по источнику)", "Всего обращений", "Не занесено", "% не занесено"]
    parts = [df for df in (comparison_chats, comparison_issues) if df is not None and not df.empty]
    if not parts:
        return pd.DataFrame(columns=cols)
    combined = pd.concat(parts, ignore_index=True)
    combined = combined[combined["Ресторан (по источнику)"].notna() & (combined["Ресторан (по источнику)"] != "")]
    if combined.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for rest, grp in combined.groupby("Ресторан (по источнику)"):
        total = len(grp)
        not_entered = int((grp["Статус"] == c.STATUS_NOT_ENTERED).sum())
        rows.append({
            "Ресторан (по источнику)": rest,
            "Всего обращений": total,
            "Не занесено": not_entered,
            "% не занесено": round(100 * not_entered / total, 1) if total else 0.0,
        })
    return pd.DataFrame(rows, columns=cols).sort_values("% не занесено", ascending=False)


# ============================================================
# ЛИСТ 4: 5 МЕТРИК (§7)
# ============================================================
def metric_unpaid_compensation(main_df: pd.DataFrame) -> pd.DataFrame:
    """1) Доля жалоб с оформленной, но невыплаченной компенсацией —
    по сотруднику и по ресторану."""
    cols = ["Группа", "Значение", "Всего с компенсацией", "Невыплачено", "% невыплачено"]
    if main_df is None or main_df.empty:
        return pd.DataFrame(columns=cols)

    has_decision = main_df["Решение"].fillna("").str.strip().str.lower().map(
        lambda v: v not in _NO_COMPENSATION_LABELS
    )
    scoped = main_df[has_decision]
    if scoped.empty:
        return pd.DataFrame(columns=cols)

    rows = []
    for group_name, group_col in (("Сотрудник", "Сотрудник"), ("Ресторан", "Ресторан")):
        for value, grp in scoped.groupby(group_col, dropna=True):
            total = len(grp)
            unpaid = int((grp["Статус возмещения"] == False).sum())  # noqa: E712
            rows.append({
                "Группа": group_name, "Значение": value,
                "Всего с компенсацией": total, "Невыплачено": unpaid,
                "% невыплачено": round(100 * unpaid / total, 1) if total else 0.0,
            })
    return pd.DataFrame(rows, columns=cols)


def metric_deviation_confirmed(main_df: pd.DataFrame) -> pd.DataFrame:
    """2) Доля подтверждённых нарушений стандарта — только СПб (поля нет
    в тюменской таблице), часто мало данных (заполняется нерегулярно)."""
    cols = ["Ресторан", "Заполнено «Отклонение»", "Подтверждено («Да»)", "% подтверждено"]
    if main_df is None or main_df.empty:
        return pd.DataFrame(columns=cols)
    scoped = main_df[main_df["Отклонение"].notna() & (main_df["Отклонение"] != "")]
    if scoped.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for rest, grp in scoped.groupby("Ресторан", dropna=True):
        total = len(grp)
        confirmed = int((grp["Отклонение"].str.strip().str.lower() == "да").sum())
        rows.append({
            "Ресторан": rest, "Заполнено «Отклонение»": total,
            "Подтверждено («Да»)": confirmed,
            "% подтверждено": round(100 * confirmed / total, 1) if total else 0.0,
        })
    return pd.DataFrame(rows, columns=cols)


def metric_compensation_cost(main_df: pd.DataFrame) -> pd.DataFrame:
    """3) Стоимость компенсаций — сумма и среднее, по ресторану и по типу жалобы."""
    cols = ["Группа", "Значение", "Кол-во", "Сумма", "Среднее"]
    if main_df is None or main_df.empty:
        return pd.DataFrame(columns=cols)
    scoped = main_df[main_df["Стоимость компенсации"].notna()]
    if scoped.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for group_name, group_col in (("Ресторан", "Ресторан"), ("Тип жалобы", "Вид жалобы")):
        for value, grp in scoped.groupby(group_col, dropna=True):
            total_cost = grp["Стоимость компенсации"].sum()
            rows.append({
                "Группа": group_name, "Значение": value,
                "Кол-во": len(grp), "Сумма": round(float(total_cost), 2),
                "Среднее": round(float(grp["Стоимость компенсации"].mean()), 2),
            })
    return pd.DataFrame(rows, columns=cols)


def metric_backlog(issues_df: pd.DataFrame) -> pd.DataFrame:
    """4) Незакрытый бэклог issues_report — доля «В ожидании»/«Открыт»/
    «В очереди» по полю «Исполнитель» (очередь/отдел)."""
    cols = ["Исполнитель", "Всего обращений", "В бэклоге", "% в бэклоге"]
    if issues_df is None or issues_df.empty or "Исполнитель" not in issues_df.columns:
        return pd.DataFrame(columns=cols)
    rows = []
    for executor, grp in issues_df.groupby("Исполнитель", dropna=True):
        total = len(grp)
        backlog = int(grp["Статус"].isin(BACKLOG_STATUSES).sum())
        rows.append({
            "Исполнитель": executor, "Всего обращений": total,
            "В бэклоге": backlog,
            "% в бэклоге": round(100 * backlog / total, 1) if total else 0.0,
        })
    return pd.DataFrame(rows, columns=cols).sort_values("% в бэклоге", ascending=False)


def metric_decision_distribution(main_df: pd.DataFrame) -> pd.DataFrame:
    """5) Распределение способов компенсации по ресторанам — проверка на
    единообразие политики между точками."""
    if main_df is None or main_df.empty:
        return pd.DataFrame()
    df = main_df.copy()
    df["Решение"] = df["Решение"].fillna("").str.strip()
    df.loc[df["Решение"] == "", "Решение"] = "без компенсации"
    pivot = pd.pivot_table(df, index="Ресторан", columns="Решение", aggfunc="size", fill_value=0)
    pivot["Всего:"] = pivot.sum(axis=1)
    return pivot.reset_index()


def build_classification_preview(label_counts: Dict[str, Dict[str, int]]) -> pd.DataFrame:
    """Статистика классификации до генерации Excel (ТЗ §9, §8.9) — сколько
    сообщений/тикетов, сколько признано жалобой, разбивка по причинам
    исключения. `label_counts`: {источник: {reason_label: count}}."""
    rows = []
    for source, counts in label_counts.items():
        total = sum(counts.values())
        complaints = counts.get("quality", 0) + counts.get("compensation", 0) + counts.get("quality_reason", 0)
        rows.append({
            "Источник": source,
            "Всего сообщений/тикетов": total,
            "Признано жалобой": complaints,
            "Дни рождения": counts.get("birthday", 0),
            "Логистика/опоздание": counts.get("logistics", 0),
            "Похвала": counts.get("praise", 0),
            "Нейтральные": counts.get("neutral", 0),
            "Не определено": counts.get("not_determined", 0),
            "Не жалоба (причина CRM)": counts.get("noncomplaint_reason", 0),
        })
    return pd.DataFrame(rows)
