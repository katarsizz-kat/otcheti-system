"""
Модуль настроения: операции с таблицей mood_entries и аналитика.

Использует подключение из utils/supabase_db.py (вариант А).
"""

import calendar
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from utils.supabase_db import get_supabase_client, parse_date

from mood.config import (
    DAYS_OF_WEEK_FULL,
    INSIGHT_TEXTS,
    MOOD_CATEGORIES,
    PARTS_OF_DAY,
    PERSONS,
    get_mood_category,
)

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


def _is_logged(e: Dict) -> bool:
    """Запись — реальная отметка (не пауза)."""
    return e.get("status") == "logged"


# ============================================================
# CRUD
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
    Добавить запись настроения.

    За одну часть дня может быть НЕСКОЛЬКО настроений.
    Обычная запись отменяет статус «пауза» за этот день.
    """
    supabase = get_supabase_client()
    d = _date_str(entry_date)

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
    """Отметить день как «без ответа» (очищает записи дня)."""
    supabase = get_supabase_client()
    d = _date_str(entry_date)

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
    """Все записи за дату (оба человека)."""
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


def get_entries_for_range(start_date, end_date) -> List[Dict]:
    """Все записи в диапазоне дат (оба человека)."""
    supabase = get_supabase_client()
    response = (
        supabase.table(MOOD_TABLE)
        .select("*")
        .gte("date", _date_str(start_date))
        .lte("date", _date_str(end_date))
        .order("date")
        .order("created_at")
        .execute()
    )
    return response.data or []


def get_entries_for_month(year: int, month: int) -> List[Dict]:
    """Все записи за месяц (оба человека)."""
    supabase = get_supabase_client()
    first_day, last_day = _month_bounds(year, month)
    return get_entries_for_range(first_day, last_day)


def get_person_entries_for_month(
    year: int,
    month: int,
    person: str,
) -> List[Dict]:
    """Записи одного человека за месяц."""
    return [
        e for e in get_entries_for_month(year, month)
        if e.get("person") == person
    ]


# ============================================================
# СЧЁТЧИКИ ЭМОЦИЙ ЗА ПЕРИОД
# ============================================================

def get_emotion_counts(start_date, end_date) -> Dict:
    """
    Счётчики эмоций за период: по каждой девушке и всего.

    Returns:
        dict: {
            "злость": {"Катя": 4, "Кристина": 2, "total": 6},
            ...
        }
        Только эмоции с ненулевыми счётчиками.
    """
    counts: Dict[str, Dict] = {}

    for e in get_entries_for_range(start_date, end_date):
        if not _is_logged(e):
            continue
        mood = e.get("mood")
        person = e.get("person")
        if not mood or person not in PERSONS:
            continue
        row = counts.setdefault(mood, {p: 0 for p in PERSONS})
        row[person] += 1

    for row in counts.values():
        row["total"] = sum(row[p] for p in PERSONS)

    return counts


# ============================================================
# БАЗОВАЯ СТАТИСТИКА
# ============================================================

def get_month_stats(year: int, month: int, person: str) -> Dict:
    """Статистика за месяц по одному человеку."""
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


# ============================================================
# ПАЛИТРА И БАЛАНС
# ============================================================

def get_mood_diversity(year: int, month: int, person: str) -> Dict:
    """«Эмоциональная палитра»: разнообразие эмоций за месяц."""
    entries = get_person_entries_for_month(year, month, person)
    moods = sorted({
        e.get("mood") for e in entries if _is_logged(e) and e.get("mood")
    })
    return {"count": len(moods), "moods": moods}


def get_category_balance(year: int, month: int, person: str) -> Dict:
    """«Баланс тепла»: доли категорий эмоций."""
    entries = get_person_entries_for_month(year, month, person)
    counts = {cat: 0 for cat in MOOD_CATEGORIES}

    for e in entries:
        if not _is_logged(e):
            continue
        counts[get_mood_category(e.get("mood"))] += 1

    total = sum(counts.values()) or 1
    return {
        "counts": counts,
        "percents": {
            cat: round(c * 100 / total) for cat, c in counts.items()
        },
        "total": total,
    }


# ============================================================
# РИТМЫ
# ============================================================

def get_weekday_rhythm(year: int, month: int, person: str) -> Dict:
    """«Ритм недели»: тёплые/напряжённые по дням недели."""
    rhythm = {i: {"warm": 0, "tense": 0} for i in range(7)}

    for e in get_person_entries_for_month(year, month, person):
        if not _is_logged(e):
            continue
        cat = get_mood_category(e.get("mood"))
        if cat in ("warm", "tense"):
            wd = parse_date(e.get("date")).weekday()
            rhythm[wd][cat] += 1

    return rhythm


def get_part_rhythm(year: int, month: int, person: str) -> Dict:
    """«Время суток»: тёплые/напряжённые по частям дня."""
    rhythm = {part: {"warm": 0, "tense": 0} for part in PARTS_OF_DAY}

    for e in get_person_entries_for_month(year, month, person):
        if not _is_logged(e):
            continue
        part = e.get("part_of_day")
        cat = get_mood_category(e.get("mood"))
        if part in rhythm and cat in ("warm", "tense"):
            rhythm[part][cat] += 1

    return rhythm


# ============================================================
# ПАРА
# ============================================================

def get_pair_stats(year: int, month: int) -> Dict:
    """«Вы вдвоём»: синхронность, поддержка, ресурсные дни."""
    entries = get_entries_for_month(year, month)

    by_date: Dict[str, Dict[str, Dict]] = {}
    for e in entries:
        if not _is_logged(e):
            continue
        day = by_date.setdefault(
            e["date"], {p: {"moods": set(), "cats": set()} for p in PERSONS}
        )
        person_data = day.get(e.get("person"))
        if person_data is None:
            continue
        person_data["moods"].add(e.get("mood"))
        person_data["cats"].add(get_mood_category(e.get("mood")))

    both_days = []
    matched_days = []
    support_days = []
    resource_days = []

    for d in sorted(by_date.keys()):
        a = by_date[d].get(PERSONS[0], {"moods": set(), "cats": set()})
        b = by_date[d].get(PERSONS[1], {"moods": set(), "cats": set()})

        if not a["moods"] or not b["moods"]:
            continue

        both_days.append(d)
        if a["moods"] & b["moods"]:
            matched_days.append(d)

        a_tense = "tense" in a["cats"]
        b_tense = "tense" in b["cats"]
        a_warm = "warm" in a["cats"]
        b_warm = "warm" in b["cats"]

        if (a_tense and b_warm) or (b_tense and a_warm):
            support_days.append(d)

        if a_warm and b_warm and not a_tense and not b_tense:
            resource_days.append(d)

    return {
        "both_days": both_days,
        "matched_days": matched_days,
        "support_days": support_days,
        "resource_days": resource_days,
    }


def get_shared_info(year: int, month: int) -> Dict:
    """Совместные дни (для календаря)."""
    info = get_pair_stats(year, month)
    return {
        "both_days": info["both_days"],
        "matched_days": info["matched_days"],
    }


# ============================================================
# ГЕНЕРАТОР МЯГКИХ ИНСАЙТОВ
# ============================================================

def get_month_insights(year: int, month: int) -> List[str]:
    """Сгенерировать 2–7 бережных наблюдений за месяц."""
    insights: List[str] = []
    entries = get_entries_for_month(year, month)
    logged = [e for e in entries if _is_logged(e)]

    if len(logged) < 5:
        return [
            "Пока записей немного — инсайты появятся, "
            "когда накопится материал 🌱"
        ]

    # Тренд: первая половина месяца против второй
    _, last_day = _month_bounds(year, month)
    mid = last_day.day // 2
    warm1 = warm2 = tense1 = tense2 = 0
    for e in logged:
        cat = get_mood_category(e.get("mood"))
        half1 = parse_date(e.get("date")).day <= mid
        if cat == "warm":
            warm1 += 1 if half1 else 0
            warm2 += 0 if half1 else 1
        elif cat == "tense":
            tense1 += 1 if half1 else 0
            tense2 += 0 if half1 else 1

    if warm2 > warm1 and warm2 >= 3:
        insights.append(INSIGHT_TEXTS["trend_up"])
    elif tense2 > tense1 and tense2 >= 3:
        insights.append(INSIGHT_TEXTS["trend_down"])

    # Паузы как забота
    pauses = sum(1 for e in entries if e.get("status") == "pause")
    if pauses >= 4:
        insights.append(INSIGHT_TEXTS["many_pauses"])

    # Сила эмоций
    intensities = [
        int(e["intensity"]) for e in logged
        if e.get("intensity") is not None
    ]
    if intensities and sum(intensities) / len(intensities) >= 3.5:
        insights.append(INSIGHT_TEXTS["high_intensity"])

    # Палитра
    wide_found = False
    for person in PERSONS:
        diversity = get_mood_diversity(year, month, person)
        stats = get_month_stats(year, month, person)
        if diversity["count"] >= 6 and not wide_found:
            insights.append(INSIGHT_TEXTS["wide_palette"])
            wide_found = True
        if diversity["count"] <= 2 and stats["logged_days"] >= 5:
            insights.append(
                INSIGHT_TEXTS["narrow_palette"].format(person=person)
            )

    # Пара
    pair = get_pair_stats(year, month)
    if len(pair["matched_days"]) >= 5:
        insights.append(INSIGHT_TEXTS["high_sync"])
    if len(pair["support_days"]) >= 3:
        insights.append(
            INSIGHT_TEXTS["support_days"].format(
                count=len(pair["support_days"])
            )
        )
    if pair["resource_days"]:
        dates = ", ".join(
            str(parse_date(d).day) for d in pair["resource_days"]
        )
        insights.append(
            INSIGHT_TEXTS["resource_days"].format(dates=dates)
        )

    # Ритмы по людям
    for person in PERSONS:
        rhythm = get_weekday_rhythm(year, month, person)
        hardest = max(rhythm.items(), key=lambda kv: kv[1]["tense"])
        warmest = max(rhythm.items(), key=lambda kv: kv[1]["warm"])

        if hardest[1]["tense"] >= 3:
            insights.append(
                INSIGHT_TEXTS["hard_weekday"].format(
                    person=person,
                    weekday=DAYS_OF_WEEK_FULL[hardest[0]],
                )
            )
        if warmest[1]["warm"] >= 3:
            insights.append(
                INSIGHT_TEXTS["warm_weekday"].format(
                    person=person,
                    weekday=DAYS_OF_WEEK_FULL[warmest[0]],
                )
            )

        part_rhythm = get_part_rhythm(year, month, person)
        tense_part = max(
            part_rhythm.items(), key=lambda kv: kv[1]["tense"]
        )
        warm_part = max(
            part_rhythm.items(), key=lambda kv: kv[1]["warm"]
        )
        if tense_part[1]["tense"] >= 3:
            insights.append(
                INSIGHT_TEXTS["tense_part"].format(
                    person=person, part=tense_part[0]
                )
            )
        if warm_part[1]["warm"] >= 3:
            insights.append(
                INSIGHT_TEXTS["warm_part"].format(
                    person=person, part=warm_part[0]
                )
            )

    return insights[:7]


# ============================================================
# ДОСТИЖЕНИЯ И УЗОРЫ
# ============================================================

def get_achievements(year: int, month: int, person: str) -> List[Dict]:
    """Достижения за месяц (проверка по неделям)."""
    from mood.config import ACHIEVEMENTS

    entries = get_person_entries_for_month(year, month, person)

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
                    if _is_logged(e)
                    and e.get("mood") == cond.get("mood")
                )

            if count >= need:
                earned.append(ach)
                break

    return earned


def get_month_pattern(year: int, month: int, person: str) -> List[Dict]:
    """«Узор месяца»: по одной точке на каждый день."""
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
            logged = [e for e in day_entries if _is_logged(e)]
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


def get_week_pattern(person: str) -> List[Dict]:
    """Узор последних 7 дней (для пятиминутки)."""
    today = date.today()
    pattern = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        entries = [
            e for e in get_entries_for_date(d)
            if e.get("person") == person
        ]
        item = {"date": d, "mood": None, "pause": False}
        logged = [e for e in entries if _is_logged(e)]
        if logged:
            counts: Dict[str, int] = {}
            for e in logged:
                counts[e["mood"]] = counts.get(e["mood"], 0) + 1
            item["mood"] = max(counts.items(), key=lambda kv: kv[1])[0]
        elif entries:
            item["pause"] = True
        pattern.append(item)
    return pattern
# ============================================================
# РЕФЛЕКСИЯ ДНЯ (ответы на вопрос дня)
# ============================================================

REFLECTION_TABLE = "mood_reflections"


def save_reflection(
    person: str,
    reflection_date,
    question: str,
    answer: str,
):
    """
    Сохранить ответ на вопрос дня (один на человека на день).

    Пустой ответ = удалить прежний (рефлексия не навязывается).
    """
    supabase = get_supabase_client()
    d = _date_str(reflection_date)

    (
        supabase.table(REFLECTION_TABLE)
        .delete()
        .eq("person", person)
        .eq("date", d)
        .execute()
    )

    answer = (answer or "").strip()
    if not answer:
        return None

    data = {
        "person": person,
        "date": d,
        "question": question,
        "answer": answer,
    }
    response = (
        supabase.table(REFLECTION_TABLE).insert(data).execute()
    )
    return response.data[0]["id"]


def get_reflections_for_date(target_date) -> List[Dict]:
    """Получить ответы на вопрос дня за дату."""
    supabase = get_supabase_client()
    d = _date_str(target_date)
    response = (
        supabase.table(REFLECTION_TABLE)
        .select("*")
        .eq("date", d)
        .execute()
    )
    return response.data or []