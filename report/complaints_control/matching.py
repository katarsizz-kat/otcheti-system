"""
Сопоставление источников с главной таблицей — ТЗ §5.

find_match: телефон + допуск по дате (по умолчанию 3 дня). Если телефон
совпал, но ближайшая по дате запись всё равно за пределами допуска —
возвращается лучшая по разнице дат запись, помеченная статусом «проверить
дату» через отдельный флаг (в отчёте это видно по большому расхождению
дат в колонках "Дата обращения" / "Дата в главной").
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd

from . import constants as c

COMPARISON_COLS = [
    "Источник", "Телефон", "Дата обращения", "Кол-во сообщений", "Сотрудник",
    "Ресторан (по источнику)", "Текст жалобы", "Статус",
    "№ записи в главной", "Дата в главной", "Ресторан (по главной)",
    "Тип жалобы (по главной)", "Ответственный (по главной)",
]

_RESTAURANT_NUM_RE = re.compile(r"№\s*(\d+)")
_TYUMEN_RE = re.compile(r"тюмен[ьи]?\D{0,3}(\d+)", re.IGNORECASE)


def extract_restaurant_from_text(text: Any) -> Optional[str]:
    """Best-effort: ресторан по источнику часто упоминается в свободном
    тексте как "№4" или "tyumen-2-..." (ТЗ §6, колонка "Ресторан (по
    источнику)"). Если не найдено — оставляем пустым, это не критично
    для статуса сопоставления."""
    if not text:
        return None
    s = str(text)
    m = _RESTAURANT_NUM_RE.search(s)
    if m:
        return f"№{m.group(1)}"
    m = _TYUMEN_RE.search(s)
    if m:
        return f"Тюмень {m.group(1)}"
    return None


def build_main_index(main_df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
    """{телефон: [строки главной таблицы]} — строится один раз на город/период."""
    index: Dict[str, List[Dict[str, Any]]] = {}
    if main_df is None or main_df.empty:
        return index
    for i, row in main_df.reset_index(drop=True).iterrows():
        phone = row.get("Телефон") or ""
        if not phone:
            continue
        record = row.to_dict()
        record["__row_num"] = i + 1
        index.setdefault(phone, []).append(record)
    return index


def find_match(
    phone: str,
    complaint_date: Optional[date],
    main_index: Dict[str, List[Dict[str, Any]]],
    tolerance_days: int = c.DEFAULT_TOLERANCE_DAYS,
) -> Optional[Dict[str, Any]]:
    candidates = main_index.get(phone, [])
    if not candidates:
        return None
    if complaint_date is None:
        return candidates[0]

    best, best_diff = None, None
    for cand in candidates:
        cand_date = cand.get("Дата")
        if cand_date is None:
            continue
        diff = abs((cand_date - complaint_date).days)
        if diff <= tolerance_days and (best is None or diff < best_diff):
            best, best_diff = cand, diff
    return best or candidates[0]


def match_source_to_main(
    complaints: pd.DataFrame,
    no_phone: pd.DataFrame,
    main_index: Dict[str, List[Dict[str, Any]]],
    source_label: str,
    tolerance_days: int = c.DEFAULT_TOLERANCE_DAYS,
    phone_col: str = "Телефон",
    date_col: str = "Дата",
    author_col: Optional[str] = None,
    count_col: Optional[str] = None,
    text_col: str = "Текст",
) -> pd.DataFrame:
    """Строит таблицу сравнения (13 колонок, ТЗ §6) для одного источника."""
    rows: List[Dict[str, Any]] = []

    for _, r in complaints.iterrows():
        phone = r.get(phone_col) or ""
        cdate = r.get(date_col)
        cdate = cdate.date() if hasattr(cdate, "date") and not isinstance(cdate, date) else cdate
        match = find_match(phone, cdate, main_index, tolerance_days)
        text = str(r.get(text_col) or "")[:500]

        status = c.STATUS_FOUND if match else c.STATUS_NOT_ENTERED

        rows.append({
            "Источник": source_label,
            "Телефон": phone,
            "Дата обращения": cdate,
            "Кол-во сообщений": r.get(count_col) if count_col else 1,
            "Сотрудник": r.get(author_col) if author_col else None,
            "Ресторан (по источнику)": extract_restaurant_from_text(text),
            "Текст жалобы": text,
            "Статус": status,
            "№ записи в главной": match.get("__row_num") if match else None,
            "Дата в главной": match.get("Дата") if match else None,
            "Ресторан (по главной)": match.get("Ресторан") if match else None,
            "Тип жалобы (по главной)": match.get("Вид жалобы") if match else None,
            "Ответственный (по главной)": match.get("Сотрудник") if match else None,
        })

    for _, r in no_phone.iterrows():
        text = str(r.get(text_col) or "")[:500]
        rows.append({
            "Источник": source_label,
            "Телефон": "",
            "Дата обращения": r.get(date_col),
            "Кол-во сообщений": 1,
            "Сотрудник": r.get(author_col) if author_col else None,
            "Ресторан (по источнику)": extract_restaurant_from_text(text),
            "Текст жалобы": text,
            "Статус": c.STATUS_NO_PHONE,
            "№ записи в главной": None,
            "Дата в главной": None,
            "Ресторан (по главной)": None,
            "Тип жалобы (по главной)": None,
            "Ответственный (по главной)": None,
        })

    return pd.DataFrame(rows, columns=COMPARISON_COLS) if rows else pd.DataFrame(columns=COMPARISON_COLS)


def match_issues_to_main(
    issues_df: pd.DataFrame,
    main_index_spb: Dict[str, List[Dict[str, Any]]],
    main_index_tmn: Dict[str, List[Dict[str, Any]]],
    tolerance_days: int = c.DEFAULT_TOLERANCE_DAYS,
) -> pd.DataFrame:
    """issues_report покрывает обе главные таблицы сразу — по каждой строке
    выбирается индекс своего города (ТЗ §2.5, §5). Ресторан и дата берутся
    из готовых столбцов файла, а не из текста (в отличие от чатов)."""
    rows: List[Dict[str, Any]] = []
    if issues_df is None or issues_df.empty:
        return pd.DataFrame(columns=COMPARISON_COLS)

    for _, r in issues_df.iterrows():
        phone = r.get("Телефон") or ""
        raw_date = r.get("Дата отзыва")
        cdate = raw_date.date() if hasattr(raw_date, "date") else None
        city = str(r.get("Город") or "").strip()
        index = main_index_spb if city == "Санкт-Петербург" else main_index_tmn

        text = str(r.get("Первичное сообщение") or "")[:500]

        if not phone:
            rows.append({
                "Источник": "issues_report", "Телефон": "", "Дата обращения": cdate,
                "Кол-во сообщений": 1, "Сотрудник": None,
                "Ресторан (по источнику)": r.get("Ресторан"), "Текст жалобы": text,
                "Статус": c.STATUS_NO_PHONE,
                "№ записи в главной": None, "Дата в главной": None,
                "Ресторан (по главной)": None, "Тип жалобы (по главной)": None,
                "Ответственный (по главной)": None,
            })
            continue

        match = find_match(phone, cdate, index, tolerance_days)
        status = c.STATUS_FOUND if match else c.STATUS_NOT_ENTERED

        rows.append({
            "Источник": "issues_report",
            "Телефон": phone,
            "Дата обращения": cdate,
            "Кол-во сообщений": 1,
            "Сотрудник": None,  # «Исполнитель» — очередь/отдел, не сотрудник (ТЗ §2.5, п.5)
            "Ресторан (по источнику)": r.get("Ресторан"),
            "Текст жалобы": text,
            "Статус": status,
            "№ записи в главной": match.get("__row_num") if match else None,
            "Дата в главной": match.get("Дата") if match else None,
            "Ресторан (по главной)": match.get("Ресторан") if match else None,
            "Тип жалобы (по главной)": match.get("Вид жалобы") if match else None,
            "Ответственный (по главной)": match.get("Сотрудник") if match else None,
        })

    return pd.DataFrame(rows, columns=COMPARISON_COLS) if rows else pd.DataFrame(columns=COMPARISON_COLS)


def find_unconfirmed_main_rows(main_df: pd.DataFrame, confirmed_phones: set) -> pd.DataFrame:
    """НЕ ПОДТВЕРЖДЕНО ИСТОЧНИКОМ (§5, обратная проверка): запись есть в
    главной таблице, но её телефон не встретился ни в одном из проверяемых
    источников за период."""
    if main_df is None or main_df.empty:
        return main_df.iloc[0:0] if main_df is not None else pd.DataFrame()
    mask = main_df["Телефон"].map(lambda p: bool(p) and p not in confirmed_phones)
    result = main_df[mask].copy()
    result["Статус"] = c.STATUS_NOT_CONFIRMED
    return result
