"""
Модуль настроения: операции с таблицей mood_entries и аналитика.

Использует подключение из utils/supabase_db.py (вариант А).
"""

import calendar
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from utils.supabase_db import get_supabase_client, parse_date

# Название таблицы в Supabase
MOOD_TABLE = "mood_entries"


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def _date_str(d) -> str:
    """Привести дату/строку к формату 'YYYY-MM-DD'."""
    return parse_date(d).isoformat()


def _month_bounds(year: int, month: int):
    """Вернуть (первый_день, последний_день) месяца."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


# ============================================================
# CRUD: СОХРАНЕНИЕ / ОБНОВЛЕНИЕ / УДАЛЕНИЕ
# ============================================================

def save_entry(
    person: str,
    entry_date,
    part_of_day: str,
    mood: str,
    intensity: int,
    note: str = "",
) -> int:
    """
    Сохранить запись настроения.

    Одна запись на человека на часть дня:
    если запись за эту часть дня уже есть — она заменяется.
    Обычная запись отменяет статус «пауза» за этот день.
    """
    supabase = get_supabase_client()
    d = _date_str(entry_date)

    # Заменяем запись за эту же часть дня
    (
        supabase.table(MOOD_TABLE)
        .delete()
        .eq("person", person)
        .eq("date", d)
        .eq("part_of_day", part_of_day)
        .eq("status", "logged")
        .execute()
    )

    # Обычная запись отменяет паузу
    (
        supabase.table(MOOD_TABLE)
        .delete()
        .eq("person", person)
        .eq("date", d)
        .eq("status", "pause")
        .execute()
    )

    data = {
        "person": person,
        "date": d,
        "part_of_day": part_of_day,
        "mood": mood,
        "intensity": int(intensity),
        "note": note or "",
        "status": "logged",
    }
    response = supabase.table(MOOD_TABLE).insert(data).execute()
    return response.data[0]["id"]


def save_pause(person: str, entry_date) -> int:
    """
    Отметить день как «без ответа».

    Пауза очищает все записи человека за этот день.
    """
    supabase = get_supabase_client()
    d = _date_str(entry_date)

    # Очищаем день полностью
    (
        supabase.table(MOOD_TABLE)
        .delete()
        .eq("person", person)
        .eq("date", d)
        .execute()
    )

    data = {
        "person": person,
        "date": d,
        "part_of_day": None,
        "mood": None,
        "intensity": None,
        "note": "",
        "status": "pause",
    }
    response = supabase.table(MOOD_TABLE).insert(data).execute()
    return response.data[0]["id"]


def update_entry(
    entry_id: int,
    part_of_day: str,
    mood: str,
    intensity: int,
    note: str = "",
) -> None:
    """Обновить существующую запись."""
    supabase = get_supabase_client()
    data = {
        "part_of_day": part_of_day,
        "mood": mood,
        "intensity": int(intensity),
        "note": note or "",
        "updated_at": datetime.now().isoformat(),
    }
    (
        supabase.table(MOOD_TABLE)
        .update(data)
        .eq("id", entry_id)
        .execute()
    )


def delete_entry(entry_id: int) -> None:
    """Удалить запись по ID."""
    supabase = get_supabase_client()
    (
        supabase.table(MOOD_TABLE)
        .delete()
        .eq("id", entry_id)
        .execute()
    )


# ============================================================
# ЧТЕНИЕ ДАННЫХ
# ============================================================

def get_entries_for_date(target_date) -> List[Dict]:
    """Получить все записи за конкретную дату (оба человека)."""
    supabase = get_supabase_client()
    d = _date_str(target_date)
    response = (
        supabase.table(MOOD_TABLE)
        .select("*")
        .eq("date", d)
        .order("created_at")
        .execute()
    )
    return response.data or []


def get_entries_for_month(year: int, month: int) -> List[Dict]:
    """Получить все записи за месяц (оба человека)."""
    supabase = get_supabase_client()
    first_day, last_day = _month_bounds(year, month)
    response = (
        supabase.table(MOOD_TABLE)
        .select("*")
        .gte("date", first_day.isoformat())
        .lte("date", last_day.isoformat())
        .order("date")
        .order("created_at")
        .execute()
    )
    return response.data or []


def get_person_entries_for_month(
    year: int,
    month: int,
    person: str,
) -> List[Dict]:
    """Получить записи одного человека за месяц."""
    return [
        e for e in get_entries_for_month(year, month)
        if e.get("person") == person
    ]


# ============================================================
# АНАЛИТИКА
# ============================================================

def get_month_stats(year: int, month: int, person: str) -> Dict:
    """
    Статистика за месяц по одному человеку.

    Returns:
        dict с ключами:
        - logged_days: дней с записями
        - pause_days: дней-пауз
        - mood_counts: частота эмоций
        - top_mood: самая частая эмоция
        - avg_intensity: средняя интенсивность
        - total_entries: всего записей
    """
    entries = get_person_entries_for_month(year, month, person)

    logged_days = set()
    pause_days = set()
    mood_counts: Dict[str, int] = {}
    intensity_sum = 0
    intensity_count = 0
    total_entries = 0

    for e in entries:
        d = e.get("date")
        if e.get("status") == "pause":
            pause_days.add(d)
            continue

        logged_days.add(d)
        total_entries += 1

        mood = e.get("mood")
        if mood:
            mood_counts[mood] = mood_counts.get(mood, 0) + 1

        if e.get("intensity") is not None:
            intensity_sum += int(e["intensity"])
            intensity_count += 1

    top_mood = None
    if mood_counts:
        top_mood = max(mood_counts.items(), key=lambda kv: kv[1])[0]

    return {
        "logged_days": len(logged_days),
        "pause_days": len(pause_days),
        "mood_counts": mood_counts,
        "top_mood": top_mood,
        "avg_intensity": (
            round(intensity_sum / intensity_count, 1)
            if intensity_count else 0
        ),
        "total_entries": total_entries,
    }


def get_shared_info(year: int, month: int) -> Dict:
    """
    Информация о совместных днях пары.

    Returns:
        dict с ключами:
        - both_days: дни, когда отмечали обе
        - matched_days: дни с совпавшими эмоциями
    """
    entries = get_entries_for_month(year, month)

    by_date: Dict[str, Dict[str, set]] = {}
    for e in entries:
        if e.get("status") != "logged":
            continue
        d = e.get("date")
        person = e.get("person")
        by_date.setdefault(d, {}).setdefault(person, set()).add(
            e.get("mood")
        )

    both_days = []
    matched_days = []
    for d in sorted(by_date.keys()):
        persons = by_date[d]
        if len(persons) >= 2:
            both_days.append(d)
            mood_sets = list(persons.values())
            if set.intersection(*mood_sets):
                matched_days.append(d)

    return {
        "both_days": both_days,
        "matched_days": matched_days,
    }


def get_achievements(year: int, month: int, person: str) -> List[Dict]:
    """
    Получить список заработанных достижений за месяц.

    Достижения проверяются по неделям: если условие выполнено
    хотя бы в одной неделе месяца — достижение засчитано.
    """
    from mood.config import ACHIEVEMENTS

    entries = get_person_entries_for_month(year, month, person)

    # Группируем записи по неделям (год, номер_недели)
    weeks: Dict[tuple, List[Dict]] = {}
    for e in entries:
        d = parse_date(e.get("date"))
        key = d.isocalendar()[:2]
        weeks.setdefault(key, []).append(e)

    earned = []
    for ach_id, ach in ACHIEVEMENTS.items():
        cond = ach["condition"]
        need = cond.get("count", 1)

        for week_entries in weeks.values():
            if cond.get("pause"):
                count = sum(
                    1 for e in week_entries
                    if e.get("status") == "pause"
                )
            else:
                count = sum(
                    1 for e in week_entries
                    if e.get("status") == "logged"
                    and e.get("mood") == cond.get("mood")
                )

            if count >= need:
                earned.append(ach)
                break

    return earned


def get_month_pattern(year: int, month: int, person: str) -> List[Dict]:
    """
    «Эмоциональный узор» месяца: по одной точке на каждый день.

    Returns:
        список dict по дням месяца:
        - date: 'YYYY-MM-DD'
        - mood: главная эмоция дня (или None)
        - pause: True, если день-пауза
    """
    entries = get_person_entries_for_month(year, month, person)

    by_date: Dict[str, List[Dict]] = {}
    for e in entries:
        by_date.setdefault(e.get("date"), []).append(e)

    first_day, last_day = _month_bounds(year, month)

    pattern = []
    current = first_day
    while current <= last_day:
        d = current.isoformat()
        day_entries = by_date.get(d, [])

        item = {"date": d, "mood": None, "pause": False}

        if day_entries:
            logged = [
                e for e in day_entries
                if e.get("status") == "logged"
            ]
            if not logged:
                item["pause"] = True
            else:
                counts: Dict[str, int] = {}
                for e in logged:
                    counts[e["mood"]] = counts.get(e["mood"], 0) + 1
                item["mood"] = max(
                    counts.items(), key=lambda kv: kv[1]
                )[0]

        pattern.append(item)
        current += timedelta(days=1)

    return pattern