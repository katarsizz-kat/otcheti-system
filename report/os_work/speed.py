"""
Скорость ответа ОС по методике v4.

- Окно 11:10–22:58 МСК каждого дня; суммируются только рабочие минуты
  ожидания, включая промежуточные дни (22:50 -> завтра 11:20 = 18 минут).
- Плотная начальная серия дополнений (промежутки ≤5 минут): отсчёт от
  последнего сообщения серии. Позднее напоминание не обнуляет ожидание.
- До одного ответа — одно ожидание.
- Ответы бота до передачи оператору не являются ответами ОС. Реальный
  ответ любого сотрудника (включая менеджера ресторана и Marketing SPB)
  прекращает ожидание; скорость относится к фактическому автору.
- Благодарности и короткие завершения без вопроса не требуют ответа;
  согласие на предложенную компенсацию действием ОС — требует.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from . import constants as c
from .crm import Message

_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\u200d\u2640-\u2642\u2665\u2764\ufe0f]+"
)
_CLOSING_RE = re.compile(
    r"^(?:спасибо|спс|благодарю|благодарствую|ок|окей|ok|okay|хорошо|ладно|"
    r"понятно|ясно|до свидания|всего доброго|всего хорошего|доброго дня|"
    r"не нужно|не надо|отбой|уже не актуально|не актуально|решено|разобрались|"
    r"вопрос решен|вопрос решён|отменяется|забудьте)[!.\s]*$"
)
_THANKS_PREFIX_RE = re.compile(r"^(?:спасибо|благодарю|спс|благодарствую)\b")
_CONSENT_RE = re.compile(r"^(?:ок|окей|ok|okay|хорошо|ладно|да)[!.\s]*$")
_ACTION_RE = re.compile(
    r"давайте|пришлите|вышлите|жду|ждём|ждем|нужно|можно|промокод|бонус|купон|"
    r"компенсац|верните|возврат|когда|почему|где|как|что|\?"
)
_PROMISE_RE = re.compile(
    r"уточн\w*|вернусь|вернёмся|вернемся|свяжемся|свяжутся|перезвон\w*|"
    r"сообщим дополнительно|ответим позже|напишем позже"
)
_DATA_REQUEST_RE = re.compile(
    r"пришлите|скриншот|уточните|напишите номер|номер заказа|подскажите номер|"
    r"приложите|фото|чек"
)
_COMP_OFFER_RE = re.compile(r"промокод|бонус|купон|компенсац|начислим|вернём|вернем")


def clean_short(text: str) -> str:
    """Очистка эмодзи/пунктуации/пробелов перед распознаванием завершений."""
    t = _EMOJI_RE.sub("", str(text or ""))
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip().lower()


def is_closing(text: str, prev_staff_text: str = "") -> bool:
    """Благодарность/короткое завершение без вопроса. Согласие на
    компенсацию («давайте промокод», «ок» после предложения начислить)
    завершением не считается — оно предполагает действие ОС."""
    t = clean_short(text)
    if not t or len(t) > 40:
        return False
    if _ACTION_RE.search(t):
        return False
    if _THANKS_PREFIX_RE.match(t):
        return True
    if _CLOSING_RE.match(t):
        if (
            prev_staff_text and _CONSENT_RE.match(t)
            and _COMP_OFFER_RE.search(prev_staff_text.lower())
        ):
            return False
        return True
    return False


def staff_promised(text: str) -> bool:
    return bool(_PROMISE_RE.search(str(text or "").lower()))


def staff_requested_data(text: str) -> bool:
    return bool(_DATA_REQUEST_RE.search(str(text or "").lower()))


def work_minutes(t1: datetime, t2: datetime) -> float:
    """Рабочие минуты ожидания между двумя МСК-моментами (окно 11:10–22:58)."""
    if t2 <= t1:
        return 0.0
    total = 0.0
    day = t1.date()
    last_day = t2.date()
    while day <= last_day:
        start = datetime.combine(day, datetime.min.time()) + timedelta(minutes=c.WINDOW_START_MIN)
        end = datetime.combine(day, datetime.min.time()) + timedelta(minutes=c.WINDOW_END_MIN)
        a, b = max(t1, start), min(t2, end)
        if b > a:
            total += (b - a).total_seconds() / 60.0
        day += timedelta(days=1)
    return round(total, 4)


@dataclass
class Wait:
    card: int
    question_ts: datetime        # первое сообщение начальной серии
    start_ts: datetime           # последнее сообщение серии (начало отсчёта)
    answer_ts: Optional[datetime]
    author: str                  # фактический автор ответа ("" если нет)
    minutes: float
    answered: bool
    kind: str = "repeat"         # first | repeat — проставляется в merge
    in_period: bool = True


def compute_waits(messages: List[Message]) -> List[Wait]:
    """Хронология guest/staff одной карточки (или объединённого обращения).
    Комментарии и технические сообщения ответами не считаются."""
    events = [m for m in messages if m.kind in ("guest", "staff")]
    events.sort(key=lambda m: m.ts)

    waits: List[Wait] = []
    question_ts: Optional[datetime] = None
    series_last: Optional[datetime] = None
    last_staff_text = ""

    for m in events:
        if m.kind == "guest":
            if question_ts is None:
                if is_closing(m.text, last_staff_text):
                    continue
                question_ts = m.ts
                series_last = m.ts
            else:
                if m.ts - series_last <= timedelta(minutes=c.SERIES_GAP_MIN):
                    series_last = m.ts
                # позднее напоминание ожидание не обнуляет
        else:
            last_staff_text = m.text
            if question_ts is not None:
                waits.append(Wait(
                    card=m.card,
                    question_ts=question_ts,
                    start_ts=series_last,
                    answer_ts=m.ts,
                    author=m.author,
                    minutes=work_minutes(series_last, m.ts),
                    answered=True,
                ))
                question_ts = None
                series_last = None

    if question_ts is not None:
        waits.append(Wait(
            card=events[-1].card if events else 0,
            question_ts=question_ts,
            start_ts=series_last,
            answer_ts=None,
            author="",
            minutes=0.0,
            answered=False,
        ))
    return waits


def mark_first_repeat(waits: List[Wait]) -> None:
    """Первый ответ по вопросу — first, продолжение — repeat. Новый
    самостоятельный вопрос в старой карточке хронологически не отличим —
    спорные случаи уходят в очередь ручной разметки."""
    first_seen = False
    for w in waits:
        if not w.answered:
            if not first_seen:
                w.kind = "first"
            continue
        if not first_seen:
            w.kind = "first"
            first_seen = True
        else:
            w.kind = "repeat"


def speed_groups(minutes: List[float]) -> Tuple[int, int, int]:
    """Группы ≤10, >10–30, >30 минут."""
    lo, hi = c.GROUP_BOUNDS
    return (
        sum(1 for v in minutes if v <= lo),
        sum(1 for v in minutes if lo < v <= hi),
        sum(1 for v in minutes if v > hi),
    )
