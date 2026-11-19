"""
Разбор CRM-выгрузки формата crm-pj-readonly-unified-2 (сборщик 2026-11-10.3).

Структура: registry.items[] (карточки) + dialogs[].entries[] (полные истории)
+ cached_dialogs[]. Все naive-даты API — UTC (time_policy.naive_api_zone),
Москва = UTC+3. Гостевые реплики и ответы бота вложены в сообщения
«Системный пользователь» блоком «Информация клиента: … Клиент (ts): … Бот (ts): …»
с теми же UTC-метками (проверено посекундно на реальном файле 17–18.11.2026).

Технические статусы (is_technical) и внутренние комментарии (is_comment)
не являются ответами ОС. Вложения — только ссылки, двоичные файлы сборщик
не скачивает.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from . import constants as c

MSK_TZ = timezone(timedelta(hours=3))

GUEST_BLOCK_MARKER = "Информация клиента"
_REPLICA_RE = re.compile(
    r"(Клиент|Бот)\s*\(([^)]+)\):\s*(.*?)(?=\n\s*(?:Клиент|Бот)\s*\(|\Z)",
    re.DOTALL,
)
_PHONE_RE = re.compile(r"Телефон:\s*([+()\d\s-]{6,})")
_TS_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")
_TZ_SUFFIX_RE = re.compile(r"(?:Z|[+-]\d{2}:?\d{2})$")


def _parse_ts(value: Any) -> Optional[datetime]:
    """Naive API-дата (UTC) -> МСК (naive). Даты с явной зоной приводятся
    к МСК без повторного сдвига (created_at_moscow уже содержит +03:00)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        dt = None
        if _TZ_SUFFIX_RE.search(text):
            try:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            for fmt in _TS_FORMATS:
                try:
                    dt = datetime.strptime(text[:19], fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                try:
                    dt = datetime.fromisoformat(text)
                except ValueError:
                    return None
    if dt.tzinfo is not None:
        return dt.astimezone(MSK_TZ).replace(tzinfo=None)
    return dt + c.MSK_OFFSET


def _norm_phone(value: str) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits[0] in "78":
        digits = digits[1:]
    return digits[-10:] if len(digits) >= 10 else ""


@dataclass
class Message:
    ts: datetime                 # МСК, naive
    author: str                  # отображаемое имя автора
    kind: str                    # guest | bot | staff | comment | technical | system
    text: str
    card: int
    msg_id: str = ""
    attachments: List[str] = field(default_factory=list)


@dataclass
class Card:
    number: int
    city: str = ""
    restaurant_id: Optional[int] = None
    status: str = ""
    source: str = ""
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    assignee: str = ""
    phone: str = ""
    description: str = ""
    messages: List[Message] = field(default_factory=list)

    def guest_messages(self) -> List[Message]:
        return [m for m in self.messages if m.kind == "guest"]

    def staff_messages(self) -> List[Message]:
        return [m for m in self.messages if m.kind == "staff"]


@dataclass
class CrmExport:
    format: str = ""
    complete: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    coverage: Dict[str, Any] = field(default_factory=dict)
    period_from: Optional[date] = None
    period_to: Optional[date] = None
    stats: Dict[str, Any] = field(default_factory=dict)
    cards: List[Card] = field(default_factory=list)
    registry_total: Optional[int] = None
    excluded: List[Dict[str, Any]] = field(default_factory=list)

    def cards_by_number(self) -> Dict[int, Card]:
        return {card.number: card for card in self.cards}


def _extract_replicas(card_number: int, text: str) -> Tuple[List[Message], str]:
    """Гостевые/ботовые реплики из блока «Информация клиента» + телефон."""
    messages: List[Message] = []
    phone = ""
    pm = _PHONE_RE.search(text)
    if pm:
        phone = _norm_phone(pm.group(1))
    for m in _REPLICA_RE.finditer(text):
        who, ts_raw, body = m.group(1), m.group(2).strip(), m.group(3).strip()
        ts = _parse_ts(ts_raw)
        if ts is None or not body:
            continue
        messages.append(Message(
            ts=ts,
            author="Гость" if who == "Клиент" else "Бот",
            kind="guest" if who == "Клиент" else "bot",
            text=body,
            card=card_number,
        ))
    return messages, phone


def _entry_messages(card_number: int, entry: Dict[str, Any]) -> Tuple[List[Message], str]:
    author = (entry.get("from") or {}).get("name") or "?"
    text = str(entry.get("text") or "")
    ts = _parse_ts(entry.get("created_at"))
    msg_id = str(entry.get("id") or "")
    attachments = []
    for att in entry.get("attachments") or []:
        if isinstance(att, dict):
            attachments.append(str(att.get("url") or att.get("name") or att))
        else:
            attachments.append(str(att))

    if entry.get("is_technical"):
        if ts is None:
            return [], ""
        return [Message(ts, author, "technical", text, card_number, msg_id, attachments)], ""

    if author == c.SYSTEM_AUTHOR:
        if GUEST_BLOCK_MARKER in text:
            replicas, phone = _extract_replicas(card_number, text)
            return replicas, phone
        if ts is None:
            return [], ""
        return [Message(ts, author, "system", text, card_number, msg_id, attachments)], ""

    if ts is None:
        return [], ""
    kind = "comment" if entry.get("is_comment") else "staff"
    return [Message(ts, author, kind, text, card_number, msg_id, attachments)], ""


def parse_crm_export(source: Any) -> CrmExport:
    """source: bytes / str / файловый объект / уже разобранный dict."""
    if isinstance(source, dict):
        data = source
    else:
        raw = source
        if hasattr(raw, "read"):
            raw = raw.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8-sig")
        data = json.loads(raw)

    export = CrmExport()
    export.format = str(data.get("format") or "")
    if not export.format.startswith("crm-pj-readonly-unified"):
        raise ValueError(
            f"Неизвестный формат выгрузки: «{export.format}». Ожидается "
            "crm-pj-readonly-unified-2 (JSON реестра и диалогов CRM)."
        )
    export.complete = bool(data.get("complete"))
    export.errors = [str(e) for e in data.get("errors") or []]
    export.warnings = [str(w) for w in data.get("warnings") or []]
    export.coverage = dict(data.get("coverage") or {})
    export.stats = dict(data.get("stats") or {})

    period = data.get("period") or {}
    try:
        export.period_from = date.fromisoformat(str(period.get("from"))[:10])
        export.period_to = date.fromisoformat(str(period.get("to_inclusive"))[:10])
    except (ValueError, TypeError):
        pass

    registry = data.get("registry") or {}
    export.registry_total = registry.get("total")
    export.excluded = list(registry.get("excluded_in_period") or [])
    items = {int(i["number"]): i for i in registry.get("items") or [] if i.get("number")}

    dialogs = data.get("dialogs") or []
    seen_numbers = set()
    for dialog in dialogs:
        number = int(dialog.get("number") or 0)
        if not number:
            continue
        seen_numbers.add(number)
        item = items.get(number, {})
        status = item.get("status")
        status_value = status.get("value") if isinstance(status, dict) else str(status or "")
        assignee = item.get("assignee")
        assignee_name = assignee.get("name") if isinstance(assignee, dict) else str(assignee or "")
        description = str(item.get("description") or "")

        card = Card(
            number=number,
            city=str(item.get("city") or ""),
            restaurant_id=item.get("restaurant_id"),
            status=status_value,
            source=str(item.get("source") or ""),
            created=_parse_ts(item.get("created_at_moscow") or item.get("created_at")),
            updated=_parse_ts(item.get("updated_at_moscow") or item.get("updated_at")),
            assignee=assignee_name,
            description=description,
        )
        _, desc_phone = _extract_replicas(number, description)
        card.phone = desc_phone

        # Реестр может содержать сообщения новее снапшота диалога (выгрузка
        # собирается не атомарно) — объединяем оба источника с дедупликацией.
        entries = list(dialog.get("entries") or [])
        item_messages = item.get("messages")
        if isinstance(item_messages, list):
            entries.extend(item_messages)

        seen_ids = set()
        seen_replicas = set()
        messages: List[Message] = []
        for entry in entries:
            msgs, phone = _entry_messages(number, entry)
            if phone and not card.phone:
                card.phone = phone
            for m in msgs:
                if m.kind in ("guest", "bot"):
                    dedup_key = (m.ts, m.text)
                    if dedup_key in seen_replicas:
                        continue
                    seen_replicas.add(dedup_key)
                else:
                    if m.msg_id and m.msg_id in seen_ids:
                        continue
                    if m.msg_id:
                        seen_ids.add(m.msg_id)
                messages.append(m)
        messages.sort(key=lambda m: m.ts)
        card.messages = messages
        export.cards.append(card)

    for number, item in items.items():
        if number not in seen_numbers:
            export.warnings.append(
                f"Карточка {number}: есть в реестре, но история диалога не выгружена."
            )

    export.cards.sort(key=lambda card: card.created or datetime.min)
    return export
