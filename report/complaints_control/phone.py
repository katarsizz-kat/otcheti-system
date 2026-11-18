"""
Нормализация телефона — БАГ, НАСТУПИТЬ ЗАНОВО НЕЛЬЗЯ (ТЗ §3).

openpyxl/pandas отдают числовые ячейки как float: `str(79991234567.0)`
даёт `"79991234567.0"`. Наивный `re.sub(r'\\D', '', ...)` вырезает точку,
но оставляет "0" после неё -> 12-значная строка вместо 11 -> номер не
распознаётся -> запись никогда не попадает в индекс для сопоставления.
Поэтому float ЦЕЛОЕ число приводится к int ДО перевода в строку.

Это самостоятельная копия (НЕ импорт из report.complaints.data), потому
что та `normalize_phone` воспроизводит ровно этот баг.
"""
from __future__ import annotations

import re
from typing import Any, List


def normalize_phone(raw: Any) -> str:
    """Возвращает 11-значный телефон вида "7XXXXXXXXXX" или "" (не строку None)."""
    if raw is None:
        return ""
    if isinstance(raw, float):
        if raw != raw:  # NaN
            return ""
        if raw.is_integer():
            raw = int(raw)  # <-- КРИТИЧНО, см. докстринг
        else:
            return ""
    s = str(raw)
    digits = re.sub(r"\D", "", s)
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return "7" + digits[1:]
    if len(digits) == 10 and digits[0] == "9":
        return "7" + digits
    return ""


_PHONE_IN_TEXT_RE = re.compile(
    r"(?:\+?7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}"
)


def find_phones_in_text(text: Any) -> List[str]:
    """Извлекает нормализованные телефоны из произвольного текста (чаты)."""
    if not text:
        return []
    found = set()
    for m in _PHONE_IN_TEXT_RE.finditer(str(text)):
        p = normalize_phone(m.group())
        if p:
            found.add(p)
    return list(found)


# Номера заказов: «tyumen-3-58419236-APD», «sankt-peterburg-20-58383418-APD»,
# «2-4555075-iPD», «15-43250550-APD». Ключевая часть — средний номер (6–9 цифр),
# первое число — номер ресторана. Префикс города и суффикс необязательны.
_ORDER_RE = re.compile(
    r"([a-zа-яё\-]+-)?(\d{1,3})-(\d{6,9})(?:-([a-z]{1,4}))?",
    re.IGNORECASE,
)
_BARE_ORDER_RE = re.compile(r"(?<!\d)(\d{6,9})(?!\d)")


def _city_from_prefix(prefix: str) -> str:
    p = str(prefix or "").lower()
    if "tyumen" in p or "тюмен" in p:
        return "Тюмень"
    if "sankt" in p or "spb" in p or "петербург" in p:
        return "Санкт-Петербург"
    return ""


def find_orders_in_text(text: Any) -> List[dict]:
    """Извлекает заказы из текста сообщений/ячеек. Каждый элемент:
    {"raw", "city", "rest", "order_id"}; order_id — строка цифр."""
    if not text:
        return []
    s = str(text)
    found: dict = {}
    for m in _ORDER_RE.finditer(s):
        order_id = m.group(3)
        if order_id not in found:
            found[order_id] = {
                "raw": m.group(0),
                "city": _city_from_prefix(m.group(1) or ""),
                "rest": int(m.group(2)),
                "order_id": order_id,
            }
    if not found and "-" in s:
        # «8 8-43322343», «-4-43405884-iP» и прочий мусор без полного префикса
        for m in _BARE_ORDER_RE.finditer(s):
            order_id = m.group(1)
            if order_id not in found:
                found[order_id] = {
                    "raw": m.group(0), "city": "", "rest": None,
                    "order_id": order_id,
                }
    return list(found.values())


def parse_key_cell(value: Any) -> dict:
    """Разбирает ключевую ячейку главной таблицы («Номер телефона» СПб /
    «Номер заказа» Тюмень): там вперемешку телефоны и номера заказов.
    Возвращает {"phone", "order_id", "rest"}."""
    phone = normalize_phone(value)
    if phone:
        return {"phone": phone, "order_id": "", "rest": None}
    orders = find_orders_in_text(value)
    if orders:
        first = orders[0]
        return {"phone": "", "order_id": first["order_id"], "rest": first["rest"]}
    return {"phone": "", "order_id": "", "rest": None}
