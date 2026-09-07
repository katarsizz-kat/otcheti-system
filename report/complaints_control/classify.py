"""
Классификация жалоб — ТЗ §4.

Порядок проверок (§4.2, важен порядок!):
1. День рождения -> has_compensation принудительно False.
2. has_quality = QUALITY_MARKERS (подстроки) ИЛИ QUALITY_REGEXES.
3. has_compensation = (только если allow_compensation) COMPENSATION_REGEXES
   И не день рождения.
4. has_compensation истинно, но нет has_quality, и есть DELAY_ONLY_MARKERS
   -> гасим has_compensation (компенсация за опоздание = логистика).
5. has_logistics = LOGISTICS_EXCLUDE_MARKERS.
6. Рейтинг: 4-5⭐ без quality/compensation -> похвала, не жалоба.
   1-3⭐ -> has_quality = True.
7. Решение: has_quality or has_compensation -> жалоба. Иначе по порядку:
   birthday -> logistics -> praise -> neutral -> «не определено».
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
    """Вырезает реплики бота из переписки бот<->гость (§4.1).

    У бота в шаблонах встречаются слова-триггеры («уточните», «акция»,
    «бонус» и т.д.), которые ломают классификацию, если их не отфильтровать.
    """
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
    reason_label: str  # 'quality' | 'compensation' | 'birthday' | 'logistics' | 'praise' | 'neutral' | 'not_determined'


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


def classify_message(
    text: Any,
    rating: Optional[float] = None,
    allow_compensation: bool = True,
) -> ClassifyResult:
    """Классифицирует одно сообщение/жалобу. `rating` — если известна оценка
    гостя (1-5), иначе None."""
    raw = extract_client_lines(text)
    t = str(raw or "").lower()

    is_birthday = _match_any_substring(t, c.BIRTHDAY_MARKERS)

    has_quality = _match_any_substring(t, c.QUALITY_MARKERS) or _match_any_regex(
        t, c.QUALITY_REGEXES
    )

    has_compensation = False
    if allow_compensation and not is_birthday:
        has_compensation = _match_any_regex(t, c.COMPENSATION_REGEXES)

    if has_compensation and not has_quality and _match_any_substring(
        t, c.DELAY_ONLY_MARKERS
    ):
        has_compensation = False

    has_logistics = _match_any_substring(t, c.LOGISTICS_EXCLUDE_MARKERS)

    is_praise = _match_any_substring(t, c.PRAISE_MARKERS)
    is_neutral = _match_any_substring(t, c.NEUTRAL_MARKERS)

    if rating is not None:
        try:
            r = float(rating)
        except (TypeError, ValueError):
            r = None
        if r is not None:
            if r >= 4 and not has_quality and not has_compensation:
                is_praise = True
            elif r <= 3:
                has_quality = True

    if has_quality or has_compensation:
        reason_label = "quality" if has_quality else "compensation"
        return ClassifyResult(True, has_quality, has_compensation, has_logistics, is_birthday, reason_label)

    if is_birthday:
        reason_label = "birthday"
    elif has_logistics:
        reason_label = "logistics"
    elif is_praise:
        reason_label = "praise"
    elif is_neutral:
        reason_label = "neutral"
    else:
        reason_label = "not_determined"

    return ClassifyResult(False, has_quality, has_compensation, has_logistics, is_birthday, reason_label)


def classify_issue_row(text: Any, reason: Any) -> ClassifyResult:
    """Классификация строки issues_report (§4.4): категория «Причина обращения»
    важнее текстового анализа. `allow_compensation=False` — та же просьба
    «начислите бонусы» в issues_report почти всегда пишет ГОСТЬ про бонусную
    программу вообще, а не признание вины ресторана (§4.2)."""
    reason_norm = str(reason or "").strip().lower()

    if reason_norm in c.NONCOMPLAINT_REASONS:
        return ClassifyResult(False, False, False, False, False, "noncomplaint_reason")

    if reason_norm in c.QUALITY_REASONS:
        return ClassifyResult(True, True, False, False, False, "quality_reason")

    return classify_message(text, rating=None, allow_compensation=False)
