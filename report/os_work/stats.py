"""
Показатели, нагрузка и сводные таблицы модуля «Работа ОС» (методика v4).

Основные показатели одинаковы в общем отчёте и личных; личные включают
совместные обращения у обоих участников, скорость относится к фактическому
автору ответа. Строка с нулевым основным показателем не выводится.
Нагрузка по часам/дням и категории жалоб переиспользуют проверенные
функции прежней страницы ОС (report/os_report.py).
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from report.os_report import (
    INTERVAL_ORDER,
    WEEKDAY_ORDER,
    get_hour_interval,
    get_interval_hours,
    get_restaurant_sort_key,
    get_weekday_name,
)

from . import constants as c
from .merge import Appeal
from .speed import speed_groups

DASHBOARD_COLS = ["Показатель", "Отдел", "Женя", "Полина"]


def _avg(values: List[float]) -> Optional[float]:
    return round(sum(values) / len(values), 1) if values else None


def _fmt_avg(values: List[float]) -> str:
    avg = _avg(values)
    return "—" if avg is None else f"{avg}"


def employee_waits(appeals: List[Appeal], employee: Optional[str]) -> List:
    out = []
    for a in appeals:
        for w in a.waits:
            if not w.in_period or not w.answered:
                continue
            if employee is None:
                out.append(w)
            elif c.OS_CRM_ACCOUNTS.get(w.author) == employee:
                out.append(w)
    return out


def employee_appeals(appeals: List[Appeal], employee: Optional[str]) -> List[Appeal]:
    if employee is None:
        return list(appeals)
    return [a for a in appeals if employee in a.employees]


def build_dashboard(
    appeals: List[Appeal],
    transfers: Dict[str, int],
    not_entered_by_emp: Dict[str, int],
    not_entered_total: int = 0,
) -> pd.DataFrame:
    rows: List[dict] = []

    def add(label: str, values: Dict[str, object], zero_skip: bool = True):
        dept, zhenya, polina = values.get("Отдел"), values.get("Женя"), values.get("Полина")
        if zero_skip:
            nums = []
            for v in (dept, zhenya, polina):
                try:
                    nums.append(float(str(v).split(" ")[0].replace("%", "").replace(",", ".")))
                except (ValueError, TypeError):
                    nums.append(0.0)
            if all(v == 0 for v in nums):
                return
        rows.append({"Показатель": label, "Отдел": dept, "Женя": zhenya, "Полина": polina})

    scopes = {"Отдел": None, "Женя": "Женя", "Полина": "Полина"}
    per_scope_appeals = {k: employee_appeals(appeals, v) for k, v in scopes.items()}
    per_scope_waits = {k: employee_waits(appeals, v) for k, v in scopes.items()}

    add("Количество обращений", {k: len(v) for k, v in per_scope_appeals.items()})

    solved = {}
    unsolved = {}
    for k, group in per_scope_appeals.items():
        solved[k] = sum(1 for a in group if a.outcome == c.OUTCOME_SOLVED)
        unsolved[k] = sum(1 for a in group if a.outcome == c.OUTCOME_UNSOLVED)
    pct = {}
    for k in scopes:
        denom = solved[k] + unsolved[k]
        pct[k] = f"{round(100 * solved[k] / denom, 1)}% ({solved[k]} из {denom})" if denom else "—"
    add("Вопрос решён, % (X из Y)", pct)
    add("Вопрос не решён", unsolved)

    add("Среднее время ответа, мин", {
        k: _fmt_avg([w.minutes for w in v]) for k, v in per_scope_waits.items()
    })
    add("Количество ответов", {k: len(v) for k, v in per_scope_waits.items()})
    add("Среднее время первого ответа, мин", {
        k: _fmt_avg([w.minutes for w in v if w.kind == "first"]) for k, v in per_scope_waits.items()
    })
    add("Первых ответов, шт", {
        k: sum(1 for w in v if w.kind == "first") for k, v in per_scope_waits.items()
    })
    add("Среднее время повторного ответа, мин", {
        k: _fmt_avg([w.minutes for w in v if w.kind == "repeat"]) for k, v in per_scope_waits.items()
    })
    add("Повторных ответов, шт", {
        k: sum(1 for w in v if w.kind == "repeat") for k, v in per_scope_waits.items()
    })

    add("Ответ дольше 20 минут (обращений)", {
        k: sum(1 for a in group if any(
            w.in_period and w.answered and w.minutes > c.DETAIL_THRESHOLD_MIN for w in a.waits
        )) for k, group in per_scope_appeals.items()
    })
    add("Обращение без ответа", {
        k: sum(1 for a in group if any(w.in_period and not w.answered for w in a.waits))
        for k, group in per_scope_appeals.items()
    })
    add("Жалобы не внесены в таблицу", {
        "Отдел": not_entered_total,
        "Женя": not_entered_by_emp.get("Женя", 0),
        "Полина": not_entered_by_emp.get("Полина", 0),
    })
    add("Жалобы переданы в ресторан", {
        "Отдел": sum(transfers.values()),
        "Женя": transfers.get("Женя", 0),
        "Полина": transfers.get("Полина", 0),
    })
    add("Нарушение тона", {
        k: sum(1 for a in group if a.tone) for k, group in per_scope_appeals.items()
    })
    add("Ответ не к месту / неверная информация", {
        k: sum(1 for a in group if a.wrong) for k, group in per_scope_appeals.items()
    })

    df = pd.DataFrame(rows, columns=DASHBOARD_COLS)
    for col in ("Отдел", "Женя", "Полина"):
        df[col] = df[col].astype(str)
    return df


def build_speed_groups_table(appeals: List[Appeal]) -> pd.DataFrame:
    minutes = [w.minutes for w in employee_waits(appeals, None)]
    le10, mid, gt30 = speed_groups(minutes)
    total = len(minutes)
    rows = []
    for label, count in (("≤10 минут", le10), (">10–30 минут", mid), (">30 минут", gt30)):
        rows.append({
            "Группа": label,
            "Ответов": count,
            "Доля": f"{round(100 * count / total, 1)}%" if total else "—",
        })
    return pd.DataFrame(rows, columns=["Группа", "Ответов", "Доля"])


def build_outcomes_table(appeals: List[Appeal]) -> pd.DataFrame:
    counts = Counter(a.outcome for a in appeals)
    total = len(appeals)
    order = [
        c.OUTCOME_SOLVED, c.OUTCOME_UNSOLVED, c.OUTCOME_WAIT_GUEST,
        c.OUTCOME_NO_DATA, c.OUTCOME_UNMARKED,
    ]
    rows = []
    for outcome in order:
        n = counts.get(outcome, 0)
        if n == 0:
            continue
        rows.append({
            "Результат вопроса": outcome,
            "Обращений": str(n),
            "Доля": f"{round(100 * n / total, 1)}%" if total else "—",
        })
    marked = total - counts.get(c.OUTCOME_UNMARKED, 0)
    rows.append({
        "Результат вопроса": f"Размечено вручную: {marked} из {total}",
        "Обращений": "",
        "Доля": "",
    })
    return pd.DataFrame(rows, columns=["Результат вопроса", "Обращений", "Доля"])


def build_unanswered(appeals: List[Appeal], restaurant_names: Dict[str, str]) -> pd.DataFrame:
    cols = ["Тикеты", "Дата вопроса", "Ресторан", "Суть обращения", "Последнее сообщение Гостя", "Сотрудник (назначен)"]
    rows = []
    for a in appeals:
        for w in a.waits:
            if w.in_period and not w.answered:
                last_guest = a.last_guest_message()
                rows.append({
                    "Тикеты": ", ".join(map(str, a.tickets)),
                    "Дата вопроса": w.question_ts,
                    "Ресторан": restaurant_names.get(a.key, a.city),
                    "Суть обращения": a.summary[:200],
                    "Последнее сообщение Гостя": (last_guest.text[:150] if last_guest else ""),
                    "Сотрудник (назначен)": ", ".join(a.employees) or "не назначен",
                })
    return pd.DataFrame(rows, columns=cols)


def build_long_answers(appeals: List[Appeal], restaurant_names: Dict[str, str]) -> pd.DataFrame:
    cols = ["Тикеты", "Ресторан", "Долгих ответов", "Макс. ожидание, мин",
            "Суть вопроса", "Время сообщения", "Время ответа", "Автор ответа"]
    rows = []
    for a in appeals:
        long_waits = [
            w for w in a.waits
            if w.in_period and w.answered and w.minutes > c.DETAIL_THRESHOLD_MIN
        ]
        if not long_waits:
            continue
        worst = max(long_waits, key=lambda w: w.minutes)
        rows.append({
            "Тикеты": ", ".join(map(str, a.tickets)),
            "Ресторан": restaurant_names.get(a.key, a.city),
            "Долгих ответов": len(long_waits),
            "Макс. ожидание, мин": round(worst.minutes, 1),
            "Суть вопроса": a.summary[:200],
            "Время сообщения": worst.start_ts,
            "Время ответа": worst.answer_ts,
            "Автор ответа": worst.author,
        })
    df = pd.DataFrame(rows, columns=cols)
    return df.sort_values("Макс. ожидание, мин", ascending=False) if not df.empty else df


def build_next_day(appeals: List[Appeal], restaurant_names: Dict[str, str]) -> pd.DataFrame:
    cols = ["Тикеты", "Ресторан", "Первый вопрос", "Первый ответ", "Дней до ответа", "Суть обращения"]
    rows = []
    for a in appeals:
        first = next((w for w in a.waits if w.in_period and w.kind == "first" and w.answered), None)
        if first is None:
            continue
        days = (first.answer_ts.date() - first.question_ts.date()).days
        if days < 1:
            continue
        rows.append({
            "Тикеты": ", ".join(map(str, a.tickets)),
            "Ресторан": restaurant_names.get(a.key, a.city),
            "Первый вопрос": first.question_ts,
            "Первый ответ": first.answer_ts,
            "Дней до ответа": days,
            "Суть обращения": a.summary[:200],
        })
    df = pd.DataFrame(rows, columns=cols)
    return df.sort_values("Дней до ответа", ascending=False) if not df.empty else df


def build_old_period_closed(appeals: List[Appeal], start: Optional[date], end: Optional[date]) -> pd.DataFrame:
    cols = ["Тикеты", "Вопрос (прошлый период)", "Ответ (в этом периоде)", "Ожидание, мин", "Автор ответа"]
    if start is None or end is None:
        return pd.DataFrame(columns=cols)
    rows = []
    for a in appeals:
        for w in a.waits:
            if w.answered and w.question_ts.date() < start and start <= w.answer_ts.date() <= end:
                rows.append({
                    "Тикеты": ", ".join(map(str, a.tickets)),
                    "Вопрос (прошлый период)": w.question_ts,
                    "Ответ (в этом периоде)": w.answer_ts,
                    "Ожидание, мин": round(w.minutes, 1),
                    "Автор ответа": w.author,
                })
    return pd.DataFrame(rows, columns=cols)


def build_old_period_open(appeals: List[Appeal], start: Optional[date]) -> pd.DataFrame:
    cols = ["Тикеты", "Вопрос (прошлый период)", "Суть обращения", "Последнее сообщение Гостя"]
    if start is None:
        return pd.DataFrame(columns=cols)
    rows = []
    for a in appeals:
        for w in a.waits:
            if not w.answered and w.question_ts.date() < start:
                last_guest = a.last_guest_message()
                rows.append({
                    "Тикеты": ", ".join(map(str, a.tickets)),
                    "Вопрос (прошлый период)": w.question_ts,
                    "Суть обращения": a.summary[:200],
                    "Последнее сообщение Гостя": (last_guest.text[:150] if last_guest else ""),
                })
    return pd.DataFrame(rows, columns=cols)


# ============================================================
# НАГРУЗКА (переиспользование интервалов прежней страницы ОС)
# ============================================================
def build_load(appeals: List[Appeal], start: Optional[date], end: Optional[date]):
    guest_rows = []
    answer_rows = []
    for a in appeals:
        for m in a.messages:
            if m.kind == "guest":
                day = m.ts.date()
                work_day = (m.ts - timedelta(days=1)).date() if m.ts.hour < 2 else day
                guest_rows.append({"ts": m.ts, "day": day, "work_day": work_day, "hour": m.ts.hour})
            elif m.kind == "staff" and c.OS_CRM_ACCOUNTS.get(m.author):
                answer_rows.append({
                    "ts": m.ts, "day": m.ts.date(),
                    "employee": c.OS_CRM_ACCOUNTS[m.author],
                })
    guests = pd.DataFrame(guest_rows)
    answers = pd.DataFrame(answer_rows)

    total_days = guests["work_day"].nunique() if not guests.empty else 0
    if not guests.empty:
        guests["Интервал"] = guests["hour"].map(get_hour_interval)
        h = guests.groupby("Интервал").size().reset_index(name="Сообщений")
        h["Сообщений/час"] = h.apply(
            lambda r: round(r["Сообщений"] / get_interval_hours(r["Интервал"]), 2), axis=1)
        h["Сообщений/час/день"] = h.apply(
            lambda r: round(r["Сообщений"] / get_interval_hours(r["Интервал"]) / total_days, 2)
            if total_days else 0, axis=1)
        h["_s"] = h["Интервал"].map(lambda x: INTERVAL_ORDER.index(x) if x in INTERVAL_ORDER else 99)
        h = h.sort_values("_s").drop(columns="_s")
        hourly = pd.DataFrame({"Интервал": INTERVAL_ORDER}).merge(h, on="Интервал", how="left").fillna(0)
        hourly["Сообщений"] = hourly["Сообщений"].astype(int)
    else:
        hourly = pd.DataFrame(columns=["Интервал", "Сообщений", "Сообщений/час", "Сообщений/час/день"])

    daily_rows = []
    if start and end:
        day = start
        while day <= end:
            g_count = int((guests["day"] == day).sum()) if not guests.empty else 0
            a_count = int((answers["day"] == day).sum()) if not answers.empty else 0
            appeals_count = sum(
                1 for a in appeals if a.first_question and a.first_question.date() == day
            )
            day_waits = [
                w.minutes for a in appeals for w in a.waits
                if w.answered and w.question_ts.date() == day
            ]
            daily_rows.append({
                "Дата": day,
                "День недели": get_weekday_name(day),
                "Сообщений гостей": g_count,
                "Ответов ОС": a_count,
                "Новых обращений": appeals_count,
                "Среднее ожидание, мин": str(_avg(day_waits)) if day_waits else "",
            })
            day += timedelta(days=1)
    daily = pd.DataFrame(daily_rows)

    if not guests.empty:
        wd = guests.groupby(guests["work_day"].map(get_weekday_name)).size().reset_index(name="Сообщений")
        wd.columns = ["День недели", "Сообщений"]
        wd["_s"] = wd["День недели"].map(lambda x: WEEKDAY_ORDER.index(x) if x in WEEKDAY_ORDER else 99)
        weekday = wd.sort_values("_s").drop(columns="_s")
    else:
        weekday = pd.DataFrame(columns=["День недели", "Сообщений"])

    joint = pd.DataFrame(columns=["Дата", "Сотрудники"])
    if not answers.empty:
        per_day = answers.groupby("day")["employee"].apply(lambda s: sorted(set(s)))
        multi = per_day[per_day.map(len) > 1]
        if not multi.empty:
            joint = pd.DataFrame({
                "Дата": list(multi.index),
                "Сотрудники": [", ".join(v) for v in multi.values],
            })
    return hourly, daily, weekday, joint, total_days


def build_weekly(appeals: List[Appeal]) -> pd.DataFrame:
    """Недельные таблицы отдела/Жени/Полины для месячного периода."""
    rows = []
    buckets: Dict[Tuple[int, int], List[Appeal]] = {}
    for a in appeals:
        if not a.first_question:
            continue
        iso = a.first_question.isocalendar()
        buckets.setdefault((iso[0], iso[1]), []).append(a)
    for (year, week), group in sorted(buckets.items()):
        dates = [a.first_question.date() for a in group if a.first_question]
        row = {
            "Неделя": f"{year}-W{week:02d}",
            "Даты": f"{min(dates).strftime('%d.%m')}–{max(dates).strftime('%d.%m')}",
            "Обращений (отдел)": len(group),
        }
        for emp in c.EMPLOYEES:
            emp_group = employee_appeals(group, emp)
            waits = employee_waits(group, emp)
            row[f"Обращений ({emp})"] = len(emp_group)
            row[f"Среднее, мин ({emp})"] = _fmt_avg([w.minutes for w in waits])
        rows.append(row)
    return pd.DataFrame(rows)


# ============================================================
# КАТЕГОРИИ (переиспользование прежней страницы ОС)
# ============================================================
def build_pivots(appeals: List[Appeal], restaurant_names: Dict[str, str]):
    rows = []
    for a in appeals:
        rows.append({
            "Ресторан": restaurant_names.get(a.key, a.city or "Не указан"),
            "Город": a.city,
            "Категория": a.category,
            "Категория_укрупн": a.agg_category,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    def pivot(col: str) -> pd.DataFrame:
        p = pd.pivot_table(df, index="Ресторан", columns=col, aggfunc="size", fill_value=0)
        p["ИТОГО"] = p.sum(axis=1)
        p = p.reset_index()
        p["_sk"] = p.apply(lambda r: get_restaurant_sort_key(r["Ресторан"], r.get("Город", "")), axis=1)
        p = p.sort_values("_sk").drop(columns=["_sk", "Город"], errors="ignore")
        return p

    city_map = df.drop_duplicates("Ресторан").set_index("Ресторан")["Город"].to_dict()
    p1 = pivot("Категория")
    p2 = pivot("Категория_укрупн")
    for p in (p1, p2):
        p.insert(1, "Город", p["Ресторан"].map(city_map).fillna(""))
    return p1, p2


# ============================================================
# ТРЕБУЕТ ВНИМАНИЯ
# ============================================================
def build_attention(appeals: List[Appeal], cc_attention: Optional[pd.DataFrame]) -> pd.DataFrame:
    cols = ["Тема", "Количество", "Тикеты", "Комментарий"]
    rows = []
    threat_tickets = []
    abuse_tickets = []
    for a in appeals:
        guest_text = " ".join(m.text.lower() for m in a.messages if m.kind == "guest")
        if any(k in guest_text for k in c.THREAT_KEYWORDS):
            threat_tickets.append(a)
        if a.abuse:
            abuse_tickets.append(a)
    if threat_tickets:
        rows.append({
            "Тема": "Угрозы обращения в надзорные/правоохранительные органы",
            "Количество": len(threat_tickets),
            "Тикеты": "; ".join(", ".join(map(str, a.tickets)) for a in threat_tickets),
            "Комментарий": "Эскалации не отправляются; темы зафиксированы для руководителя.",
        })
    if abuse_tickets:
        rows.append({
            "Тема": "Гости ругались (брань, унижения, оскорбления, угрозы)",
            "Количество": len(abuse_tickets),
            "Тикеты": "; ".join(", ".join(map(str, a.tickets)) for a in abuse_tickets),
            "Комментарий": "Определено автоматически по брани Гостя; отдельно от ошибок сотрудников.",
        })
    attention = pd.DataFrame(rows, columns=cols)
    if cc_attention is not None and not cc_attention.empty:
        cc_rows = []
        for _, r in cc_attention.iterrows():
            cc_rows.append({
                "Тема": str(r.get("Ресторан", "")) or "Технические случаи из чатов",
                "Количество": r.get("Кол-во сообщений", 1),
                "Тикеты": str(r.get("Автор", "")),
                "Комментарий": str(r.get("Текст", ""))[:300],
            })
        attention = pd.concat([attention, pd.DataFrame(cc_rows, columns=cols)], ignore_index=True)
    return attention


def build_remarks(appeals: List[Appeal], restaurant_names: Dict[str, str]) -> pd.DataFrame:
    cols = ["Проблема", "Количество обращений", "Тикеты", "Комментарий"]
    rows = []
    for flag, label in (("tone", "Нарушение тона"), ("wrong", "Ответ не к месту / неверная информация")):
        group = [a for a in appeals if getattr(a, flag)]
        if not group:
            continue
        rows.append({
            "Проблема": label,
            "Количество обращений": len(group),
            "Тикеты": "; ".join(", ".join(map(str, a.tickets)) for a in group),
            "Комментарий": "Отмечено в очереди ручной разметки. "
                           + " / ".join(a.summary[:80] for a in group[:3]),
        })
    return pd.DataFrame(rows, columns=cols)


def build_appeals_table(appeals: List[Appeal], restaurant_names: Dict[str, str]) -> pd.DataFrame:
    cols = ["Ключ", "Тикеты", "Дата", "Город", "Ресторан", "Категория", "Суть обращения",
            "Телефон Гостя", "Заказы", "Ответов", "Среднее ожидание, мин",
            "Без ответа", "Результат", "Сотрудники", "Замечания"]
    rows = []
    for a in appeals:
        answered = [w for w in a.waits if w.in_period and w.answered]
        marks = []
        if a.tone:
            marks.append("тон")
        if a.wrong:
            marks.append("не к месту")
        if a.abuse:
            marks.append("брань Гостя")
        rows.append({
            "Ключ": a.key,
            "Тикеты": ", ".join(map(str, a.tickets)),
            "Дата": a.first_question,
            "Город": a.city,
            "Ресторан": restaurant_names.get(a.key, a.city),
            "Категория": a.category,
            "Суть обращения": a.summary[:200],
            "Телефон Гостя": a.phone or "номер не указан",
            "Заказы": ", ".join(a.order_raws),
            "Ответов": len(answered),
            "Среднее ожидание, мин": str(_avg([w.minutes for w in answered])) if answered else "",
            "Без ответа": "Да" if any(w.in_period and not w.answered for w in a.waits) else "",
            "Результат": a.outcome,
            "Сотрудники": ", ".join(a.employees) or "не назначен",
            "Замечания": ", ".join(marks),
        })
    return pd.DataFrame(rows, columns=cols)


def build_waits_table(appeals: List[Appeal]) -> pd.DataFrame:
    cols = ["Тикеты", "Тип ответа", "Вопрос", "Начало отсчёта", "Ответ",
            "Ожидание, мин", "Автор ответа", "В периоде"]
    rows = []
    for a in appeals:
        for w in a.waits:
            rows.append({
                "Тикеты": ", ".join(map(str, a.tickets)),
                "Тип ответа": "первый" if w.kind == "first" else "повторный",
                "Вопрос": w.question_ts,
                "Начало отсчёта": w.start_ts,
                "Ответ": w.answer_ts if w.answered else "без ответа",
                "Ожидание, мин": str(round(w.minutes, 1)) if w.answered else "",
                "Автор ответа": w.author or "",
                "В периоде": "Да" if w.in_period else "прошлый период",
            })
    return pd.DataFrame(rows, columns=cols)


def build_personal(
    appeals: List[Appeal],
    employee: str,
    restaurant_names: Dict[str, str],
    transfers: Dict[str, int],
    not_entered_by_emp: Dict[str, int],
) -> Dict[str, pd.DataFrame]:
    group = employee_appeals(appeals, employee)
    waits = employee_waits(appeals, employee)
    if not group and not waits:
        return {
            "metrics": pd.DataFrame(columns=["Показатель", "Значение"]),
            "appeals": pd.DataFrame(),
        }
    solved = sum(1 for a in group if a.outcome == c.OUTCOME_SOLVED)
    unsolved = sum(1 for a in group if a.outcome == c.OUTCOME_UNSOLVED)
    denom = solved + unsolved
    metrics = [
        ("Количество обращений", len(group)),
        ("Вопрос решён, % (X из Y)",
         f"{round(100 * solved / denom, 1)}% ({solved} из {denom})" if denom else "—"),
        ("Вопрос не решён", unsolved),
        ("Среднее время ответа, мин", _fmt_avg([w.minutes for w in waits])),
        ("Количество ответов", len(waits)),
        ("Среднее время первого ответа, мин", _fmt_avg([w.minutes for w in waits if w.kind == "first"])),
        ("Первых ответов, шт", sum(1 for w in waits if w.kind == "first")),
        ("Среднее время повторного ответа, мин", _fmt_avg([w.minutes for w in waits if w.kind == "repeat"])),
        ("Повторных ответов, шт", sum(1 for w in waits if w.kind == "repeat")),
        ("Ответ дольше 20 минут (обращений)", sum(
            1 for a in group if any(w.in_period and w.answered and w.minutes > c.DETAIL_THRESHOLD_MIN for w in a.waits))),
        ("Обращение без ответа", sum(1 for a in group if any(w.in_period and not w.answered for w in a.waits))),
        ("Жалобы не внесены в таблицу", not_entered_by_emp.get(employee, 0)),
        ("Жалобы переданы в ресторан", transfers.get(employee, 0)),
        ("Нарушение тона", sum(1 for a in group if a.tone)),
        ("Ответ не к месту / неверная информация", sum(1 for a in group if a.wrong)),
    ]
    metrics_df = pd.DataFrame(
        [{"Показатель": k, "Значение": str(v)} for k, v in metrics
         if not (isinstance(v, (int, float)) and v == 0)],
        columns=["Показатель", "Значение"],
    )
    appeals_df = build_appeals_table(group, restaurant_names).drop(columns=["Ключ"], errors="ignore")
    return {"metrics": metrics_df, "appeals": appeals_df}
