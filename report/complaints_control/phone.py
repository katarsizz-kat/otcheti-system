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
