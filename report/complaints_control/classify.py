"""
Классификация жалоб для проверки внесения (действующие правила, ред. 18.11.2026).

Порядок проверок (важен!):
1. Качество/недоложенные позиции/сервис/приготовление -> жалоба, категория
   учебника (недоложенные > сервис > приготовление > продукт).
2. Промокод/купон за опоздание или долгое ожидание -> жалоба «Опоздания»
   (уточнение 17.11.2026). Обычные бонусы за задержку под это правило не
   попадают, но сама задержка остаётся жалобой «Опоздания».
3. Недовоз заказа целиком («заказ не доставлен») -> не жалоба, «Требует
   внимания» (уточнение 19.11.2026); «не доставлен вовремя» — опоздание.
4. Задержка/«где заказ» без изменения текущего заказа -> «Опоздания».
5. Признание ресторана (компенсация), в т.ч. просьба дать что-то «в качестве
   лояльности» (уточнение 19.11.2026) -> жалоба.
6. Технические сбои, пропавшие заказы, ранний «доставлен», недоступные
   телефоны -> «Требует внимания» (не жалоба для внесения).
7. Изменения текущего заказа, возвраты без жалобы, лояльность/ДР, похвала,
   нейтральные -> не жалобы.

Бессодержательные реплики бота вырезаются до классификации.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from . import constants as c

_CLIENT_BOT_RE = re.compile(
    r"(Клиент|Бот) \([^)]*\):\s*(.*?)(?=(?:Клиент|Бот) \(|$)", re.S
)


def extract_client_lines(text: Any) -> str:
    """Вырезает реплики бота из переписки бот<->гость: у бота в шаблонах
    встречаются слова-триггеры («уточните», «акция», «бонус»), которые
    ломают классификацию."""
    text = text or ""
    if not text or "Клиент (" not in text:
        return text
    segments = _CLIENT_BOT_RE.findall(text)
    client_only = " ".join(seg.strip() for role, seg in segments if role == "Клиент")
    return client_only if client_only.strip() else text


@dataclass
class ClassifyResult:
    is_complaint: bool
    has_quality: bool
    has_compensation: bool
    has_logistics: bool
    is_birthday: bool
    reason_label: str
    category: str = ""


def _match_any_substring(text: str, markers) -> bool:
    return any(m in text for m in markers)


def _match_any_regex(text: str, patterns) -> bool:
    for p in patterns:
        try:
            if re.search(p, text):
                return True
        except re.error:
            continue
    return False


def _quality_category(t: str, has_missing: bool, has_service: bool, has_cooking: bool) -> str:
    if has_missing:
        return c.CAT_MISSING
    if has_service:
        return c.CAT_SERVICE
    if has_cooking:
        return c.CAT_COOKING
    return c.CAT_PRODUCT


def is_delay_promo_request(t: str, is_birthday: bool) -> bool:
    """Промокод/купон за опоздание/долгое ожидание (правило 17.11.2026).
    День рождения исключается; бонусы/баллы не считаются промокодом."""
    if is_birthday:
        return False
    if not re.search(c.DELAY_PROMO_WORD_RE, t):
        return False
    return bool(re.search(c.DELAY_PROMO_REASON_RE, t))


def is_not_delivered(t: str) -> bool:
    """Недовоз заказа целиком — не жалоба (уточнение 19.11.2026).
    «Не доставлен вовремя/в срок» — опоздание, а не недовоз."""
    if re.search(r'не\s+доставлен\w*\s+(?:вовремя|в\s+срок)', t):
        return False
    return _match_any_substring(t, c.NOT_DELIVERED_MARKERS)


def is_loyalty_compensation_request(t: str) -> bool:
    """Просьба дать что-то «в качестве лояльности/компенсации» — жалоба
    (уточнение 19.11.2026): ресторан признаёт проблему и просит компенсацию гостю."""
    return bool(
        re.search(c.LOYALTY_COMP_PHRASE_RE, t)
        and re.search(c.LOYALTY_COMP_WORD_RE, t)
    )


def classify_message(
    text: Any,
    rating: Optional[float] = None,
    allow_compensation: bool = True,
) -> ClassifyResult:
    """Классифицирует сообщение/группу сообщений чата ресторана."""
    raw = extract_client_lines(text)
    t = str(raw or "").lower()

    is_birthday = _match_any_substring(t, c.BIRTHDAY_MARKERS)

    has_missing = _match_any_substring(t, c.MISSING_MARKERS) or _match_any_regex(
        t, c.QUALITY_REGEXES
    )
    has_service = _match_any_substring(t, c.SERVICE_MARKERS)
    has_cooking = _match_any_substring(t, c.COOKING_MARKERS)
    has_quality = (
        _match_any_substring(t, c.QUALITY_MARKERS)
        or _match_any_regex(t, c.QUALITY_REGEXES)
        or has_missing or has_service or has_cooking
    )

    delay_promo = is_delay_promo_request(t, is_birthday)
    not_delivered = is_not_delivered(t)
    has_delay = _match_any_substring(t, c.DELAY_COMPLAINT_MARKERS)
    logistics_change = _match_any_substring(t, c.LOGISTICS_CHANGE_MARKERS)

    has_compensation = False
    if allow_compensation and not is_birthday:
        has_compensation = (
            _match_any_regex(t, c.COMPENSATION_REGEXES)
            or is_loyalty_compensation_request(t)
        )

    attention = _match_any_substring(t, c.ATTENTION_MARKERS)
    loyalty = _match_any_substring(t, c.LOYALTY_MARKERS)
    finance = _match_any_substring(t, c.FINANCE_MARKERS)
    is_praise = _match_any_substring(t, c.PRAISE_MARKERS)
    is_neutral = _match_any_substring(t, c.NEUTRAL_MARKERS)

    if rating is not None:
        try:
            r = float(rating)
        except (TypeError, ValueError):
            r = None
        if r is not None:
            if r >= 4 and not has_quality and not has_compensation and not has_delay:
                is_praise = True
            elif r <= 3:
                has_quality = True

    def result(is_complaint: bool, reason: str, category: str = "") -> ClassifyResult:
        return ClassifyResult(
            is_complaint, has_quality, has_compensation,
            logistics_change, is_birthday, reason, category,
        )

    if has_quality:
        return result(True, "quality", _quality_category(t, has_missing, has_service, has_cooking))

    if delay_promo:
        return result(True, "delay_promo", c.CAT_DELAY)

    if not_delivered:
        return result(False, "not_delivered")

    if has_delay and not logistics_change:
        return result(True, "delay", c.CAT_DELAY)

    if has_compensation and not logistics_change:
        return result(True, "compensation", c.CAT_DELAY if has_delay else c.CAT_PRODUCT)

    if attention:
        return result(False, "attention")

    if logistics_change:
        return result(False, "logistics")

    if finance:
        return result(False, "neutral")

    if is_birthday:
        return result(False, "birthday")

    if loyalty:
        return result(False, "loyalty")

    if is_praise:
        return result(False, "praise")

    if is_neutral:
        return result(False, "neutral")

    return result(False, "not_determined")