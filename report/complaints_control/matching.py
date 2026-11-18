"""
Сопоставление жалоб из чатов с главной таблицей — действующие правила
(ред. 18.11.2026):

- ключи: номер заказа, телефон, дата, ресторан, суть (категория учебника);
- одного телефона/даты недостаточно для объединения разных жалоб;
- точное совпадение: номер заказа, либо совокупность телефон+ресторан+дата+
  категория (запись без номера заказа может считаться точной по совокупности);
- вероятное совпадение: частичные ключи (телефон+дата в пределах допуска,
  строка таблицы без даты и т.п.) — требует сверки и НЕ считается невнесённым;
- «запись не найдена» при неполных ключах — не доказанное невнесение;
- сверяется вся таблица, включая старые строки и строки без даты.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from . import constants as c

COMPARISON_COLS = [
    "Ключ", "Источник", "Дата", "Сотрудник", "Тикеты", "Ресторан",
    "Категория жалобы", "Суть обращения", "Телефон Гостя", "Заказ",
    "Статус", "Результат сверки", "№ записи в главной", "Дата в главной",
    "Ресторан (по главной)", "Категория (по главной)", "Основание",
]

_TYUMEN_REST_RE = re.compile(r"тюмен\w*\s*[№#]?\s*(\d+)", re.IGNORECASE)
_SPB_REST_RE = re.compile(
    r"(?:санкт-петербург\w*|петербург\w*|спб)\s*[№#]?\s*(\d+)", re.IGNORECASE
)
_NUM_REST_RE = re.compile(r"№\s*(\d+)")


def extract_restaurant(text: Any, orders: List[dict], source_label: str) -> Tuple[str, Optional[int], str]:
    """(город, номер ресторана, подпись) из заказа/текста/источника.
    Best-effort: если номер не найден — подпись пустая, это не критично."""
    city = ""
    rest: Optional[int] = None
    for o in orders or []:
        if o.get("city"):
            city = o["city"]
        if o.get("rest") is not None and rest is None:
            rest = o["rest"]
    s = str(text or "")
    m = _TYUMEN_REST_RE.search(s)
    if m:
        city, rest = "Тюмень", int(m.group(1))
    else:
        m = _SPB_REST_RE.search(s)
        if m:
            city, rest = "Санкт-Петербург", int(m.group(1))
        elif rest is None:
            m = _NUM_REST_RE.search(s)
            if m:
                rest = int(m.group(1))
    if not city:
        city = "Тюмень" if "Тюмень" in source_label else "Санкт-Петербург"
    label = f"{city} №{rest}" if rest is not None else ""
    return city, rest, label


def build_main_index(main_df: pd.DataFrame) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Индексы по телефону и по номеру заказа — по всей таблице, без
    фильтрации периодом (правило: сверять всю доступную таблицу)."""
    index: Dict[str, Dict[str, List[Dict[str, Any]]]] = {"by_phone": {}, "by_order": {}}
    if main_df is None or main_df.empty:
        return index
    for i, row in main_df.reset_index(drop=True).iterrows():
        record = row.to_dict()
        record["__row_num"] = i + 1
        phone = record.get("Телефон") or ""
        order = record.get("Заказ") or ""
        if phone:
            index["by_phone"].setdefault(phone, []).append(record)
        if order:
            index["by_order"].setdefault(str(order), []).append(record)
    return index


def _date_diff(a: Optional[date], b: Optional[date]) -> Optional[int]:
    if a is None or b is None:
        return None
    return abs((a - b).days)


def _rest_ok(rest: Optional[int], cand: Dict[str, Any]) -> bool:
    cand_rest = cand.get("Номер ресторана")
    if rest is None or cand_rest is None or pd.isna(cand_rest):
        return True
    return int(cand_rest) == int(rest)


def _cat_ok(category: str, cand: Dict[str, Any]) -> bool:
    cand_cat = cand.get("Категория") or ""
    if not category or not cand_cat:
        return True
    return category == cand_cat


def match_complaint(
    phone: str,
    order_id: str,
    rest: Optional[int],
    cdate: Optional[date],
    category: str,
    index: Dict[str, Dict[str, List[Dict[str, Any]]]],
    tolerance_days: int = c.DEFAULT_TOLERANCE_DAYS,
) -> Tuple[str, Optional[Dict[str, Any]], str]:
    """Возвращает (статус, запись таблицы|None, основание)."""
    # 1. Номер заказа — сильный ключ: точное совпадение.
    if order_id:
        candidates = index["by_order"].get(str(order_id), [])
        if candidates:
            best = min(
                candidates,
                key=lambda r: (_date_diff(cdate, r.get("Дата")) is None,
                               _date_diff(cdate, r.get("Дата")) or 0),
            )
            return c.STATUS_EXACT, best, f"номер заказа {order_id}"

    # 2. Телефон + совокупность ключей.
    candidates = index["by_phone"].get(phone, []) if phone else []
    best_exact = None
    best_probable = None
    best_prob_diff = None
    for cand in candidates:
        cand_date = cand.get("Дата")
        diff = _date_diff(cdate, cand_date)
        rest_ok = _rest_ok(rest, cand)
        cat_ok = _cat_ok(category, cand)
        if diff == 0 and rest_ok and cat_ok:
            if best_exact is None:
                best_exact = cand
            continue
        probable = (
            (diff is not None and diff <= tolerance_days)
            or (cand_date is None and rest_ok and cat_ok)
            or (diff == 0 and (rest_ok or cat_ok))
        )
        if probable:
            score = diff if diff is not None else tolerance_days + 1
            if best_probable is None or score < best_prob_diff:
                best_probable, best_prob_diff = cand, score

    if best_exact is not None:
        return c.STATUS_EXACT, best_exact, "телефон + ресторан + дата + категория"
    if best_probable is not None:
        return c.STATUS_PROBABLE, best_probable, "частичные ключи (телефон/дата/ресторан/категория)"

    # 3. Записи нет. Неполные ключи — не доказанное невнесение.
    if not phone and not order_id:
        return c.STATUS_NO_KEYS, None, "нет телефона и номера заказа"
    return c.STATUS_NOT_ENTERED, None, "совпадений по ключам нет"


def result_label(status: str, basis: str) -> str:
    if status == c.STATUS_EXACT:
        return f"{c.RESULT_EXACT}: {basis}"
    if status == c.STATUS_PROBABLE:
        return c.RESULT_PROBABLE
    if status == c.STATUS_NO_KEYS:
        return c.RESULT_NO_KEYS
    return c.RESULT_NOT_FOUND


def complaint_key(source: str, phone: str, order_id: str, cdate: Optional[date], text: str) -> str:
    """Устойчивый ключ жалобы для очереди ручной разметки."""
    digest = hashlib.sha1(str(text or "").encode("utf-8")).hexdigest()[:10]
    day = cdate.isoformat() if cdate else ""
    return f"{source}|{order_id or phone}|{day}|{digest}"


def format_guest_phone(phone: str) -> str:
    """Столбец «Телефон Гостя»: номер из сообщения Битрикс либо явная
    пометка об отсутствии (правило 17.11.2026)."""
    if not phone:
        return c.NO_PHONE_LABEL
    return f"+{phone}"