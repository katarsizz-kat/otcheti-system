"""
Объединение тикетов в обращения (единица подсчёта по методике v4).

Несколько тикетов одного Гостя по одному вопросу — одно обращение; номера
всех связанных тикетов сохраняются. Автоматически объединяются только
карточки с общим номером заказа и совместимым телефоном — разные вопросы
по одному телефону/дате не объединяются. Возможные повторы (один телефон,
разные заказы, близкие даты) уходят в очередь ручной разметки.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from report.complaints_control.phone import find_orders_in_text
from report.os_report import categorize_complaint_detailed, get_aggregated_category

from . import constants as c
from .crm import Card, Message
from .speed import Wait, compute_waits, mark_first_repeat

MERGE_WINDOW_DAYS = 7


def appeal_key(tickets: List[int]) -> str:
    """Устойчивый идентификатор объединённого вопроса (для реестра повторов)."""
    raw = ",".join(str(t) for t in sorted(tickets))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


@dataclass
class Appeal:
    key: str
    tickets: List[int]
    phone: str
    city: str
    restaurant_id: Optional[int]
    cards: List[Card]
    orders: List[str] = field(default_factory=list)
    order_raws: List[str] = field(default_factory=list)
    first_question: Optional[datetime] = None
    summary: str = ""
    category: str = ""
    agg_category: str = ""
    messages: List[Message] = field(default_factory=list)
    waits: List[Wait] = field(default_factory=list)
    outcome: str = c.OUTCOME_UNMARKED
    tone: bool = False
    wrong: bool = False
    abuse: bool = False
    active: bool = True
    outcome_hint: str = ""
    employees: List[str] = field(default_factory=list)

    def in_period_waits(self, start, end) -> List[Wait]:
        return [w for w in self.waits if w.in_period]

    def last_staff_message(self) -> Optional[Message]:
        staff = [m for m in self.messages if m.kind == "staff"]
        return staff[-1] if staff else None

    def last_guest_message(self) -> Optional[Message]:
        guests = [m for m in self.messages if m.kind == "guest"]
        return guests[-1] if guests else None


def _card_orders(card: Card) -> Tuple[List[str], List[str]]:
    texts = [card.description] + [m.text for m in card.messages if m.kind == "guest"]
    ids, raws = [], []
    for text in texts:
        for o in find_orders_in_text(text):
            if o["order_id"] not in ids:
                ids.append(o["order_id"])
                raws.append(o["raw"])
    return ids, raws


def _compatible_phones(phones: List[str]) -> bool:
    known = {p for p in phones if p}
    return len(known) <= 1


def build_appeals(cards: List[Card]) -> Tuple[List[Appeal], List[dict]]:
    """Возвращает (обращения, кандидаты на объединение для ручной разметки)."""
    card_orders: Dict[int, Tuple[List[str], List[str]]] = {}
    for card in cards:
        card_orders[card.number] = _card_orders(card)

    parent: Dict[int, int] = {card.number: card.number for card in cards}

    def find(n: int) -> int:
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            lo, hi = sorted([ra, rb])
            parent[hi] = lo

    by_order: Dict[str, List[Card]] = {}
    for card in cards:
        for oid in card_orders[card.number][0]:
            by_order.setdefault(oid, []).append(card)
    for group in by_order.values():
        if len(group) < 2:
            continue
        if _compatible_phones([card.phone for card in group]):
            for other in group[1:]:
                union(group[0].number, other.number)

    clusters: Dict[int, List[Card]] = {}
    for card in cards:
        clusters.setdefault(find(card.number), []).append(card)

    appeals: List[Appeal] = []
    for group in clusters.values():
        group.sort(key=lambda card: card.created or datetime.min)
        tickets = sorted(card.number for card in group)
        phone = next((card.phone for card in group if card.phone), "")
        city = next((card.city for card in group if card.city), "")
        restaurant_id = next((card.restaurant_id for card in group if card.restaurant_id), None)
        orders, raws = [], []
        for card in group:
            ids, rs = card_orders[card.number]
            for oid, raw in zip(ids, rs):
                if oid not in orders:
                    orders.append(oid)
                    raws.append(raw)

        messages = sorted(
            (m for card in group for m in card.messages),
            key=lambda m: m.ts,
        )
        guests = [m for m in messages if m.kind == "guest"]
        first_question = guests[0].ts if guests else None
        first_text = guests[0].text if guests else ""
        category = categorize_complaint_detailed(first_text, "")
        waits = compute_waits(messages)
        mark_first_repeat(waits)

        employees = []
        for m in messages:
            if m.kind != "staff":
                continue
            emp = c.OS_CRM_ACCOUNTS.get(m.author)
            if emp and emp not in employees:
                employees.append(emp)
        # Назначенный сотрудник учитывается только если живых ответов вообще
        # не было: чужой реальный ответ (Marketing, менеджер) не приписываем.
        if not employees and not any(m.kind == "staff" for m in messages):
            for card in group:
                emp = c.OS_CRM_ACCOUNTS.get(card.assignee)
                if emp and emp not in employees:
                    employees.append(emp)

        appeals.append(Appeal(
            key=appeal_key(tickets),
            tickets=tickets,
            phone=phone,
            city=city,
            restaurant_id=restaurant_id,
            cards=group,
            orders=orders,
            order_raws=raws,
            first_question=first_question,
            summary=first_text[:300],
            category=category,
            agg_category=get_aggregated_category(category),
            messages=messages,
            waits=waits,
            employees=employees,
        ))

    appeals.sort(key=lambda a: a.first_question or datetime.min)
    candidates = _merge_candidates(appeals)
    return appeals, candidates


def _merge_candidates(appeals: List[Appeal]) -> List[dict]:
    """Один телефон, разные заказы/вопросы, близкие даты — возможный повтор."""
    by_phone: Dict[str, List[Appeal]] = {}
    for a in appeals:
        if a.phone:
            by_phone.setdefault(a.phone, []).append(a)
    candidates = []
    for phone, group in by_phone.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda a: a.first_question or datetime.min)
        for i in range(len(group) - 1):
            a, b = group[i], group[i + 1]
            if set(a.orders) & set(b.orders):
                continue  # уже объединены по заказу
            if not a.first_question or not b.first_question:
                continue
            if b.first_question - a.first_question > timedelta(days=MERGE_WINDOW_DAYS):
                continue
            candidates.append({
                "Ключ": f"{a.key}|{b.key}",
                "Телефон": phone,
                "Тикеты А": ", ".join(map(str, a.tickets)),
                "Тикеты Б": ", ".join(map(str, b.tickets)),
                "Дата А": a.first_question.strftime("%d.%m.%Y %H:%M"),
                "Дата Б": b.first_question.strftime("%d.%m.%Y %H:%M"),
                "Суть А": a.summary[:150],
                "Суть Б": b.summary[:150],
                "Решение": c.MERGE_DEFAULT,
            })
    return candidates


def apply_merge_overrides(
    appeals: List[Appeal], candidates: List[dict], overrides: Dict[str, str],
) -> List[Appeal]:
    """Ручное решение «Объединить» склеивает два обращения в одно."""
    if not overrides:
        return appeals
    by_key = {a.key: a for a in appeals}
    parent = {a.key: a.key for a in appeals}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for cand in candidates:
        if overrides.get(cand["Ключ"]) != "merge":
            continue
        ka, kb = cand["Ключ"].split("|")
        if ka in parent and kb in parent:
            ra, rb = find(ka), find(kb)
            if ra != rb:
                parent[rb] = ra

    clusters: Dict[str, List[Appeal]] = {}
    for a in appeals:
        clusters.setdefault(find(a.key), []).append(a)

    merged: List[Appeal] = []
    for group in clusters.values():
        if len(group) == 1:
            merged.append(group[0])
            continue
        group.sort(key=lambda a: a.first_question or datetime.min)
        tickets = sorted(t for a in group for t in a.tickets)
        messages = sorted((m for a in group for m in a.messages), key=lambda m: m.ts)
        orders, raws = [], []
        for a in group:
            for oid, raw in zip(a.orders, a.order_raws):
                if oid not in orders:
                    orders.append(oid)
                    raws.append(raw)
        guests = [m for m in messages if m.kind == "guest"]
        waits = compute_waits(messages)
        mark_first_repeat(waits)
        employees = []
        for a in group:
            for emp in a.employees:
                if emp not in employees:
                    employees.append(emp)
        base = group[0]
        merged.append(Appeal(
            key=appeal_key(tickets),
            tickets=tickets,
            phone=base.phone,
            city=base.city,
            restaurant_id=base.restaurant_id,
            cards=[card for a in group for card in a.cards],
            orders=orders,
            order_raws=raws,
            first_question=guests[0].ts if guests else base.first_question,
            summary=base.summary,
            category=base.category,
            agg_category=base.agg_category,
            messages=messages,
            waits=waits,
            employees=employees,
            outcome=base.outcome,
            tone=base.tone,
            wrong=base.wrong,
            abuse=base.abuse,
        ))
    merged.sort(key=lambda a: a.first_question or datetime.min)
    return merged


def outcome_hint(appeal: Appeal) -> str:
    """Детерминированная ПОДСКАЗКА-ПРОБЛЕМА для очереди разметки (не решение).
    Возвращает только сигналы риска; чистые обращения с ответом подсказки не
    имеют и отмечаются решёнными массовой кнопкой, без ручной проверки."""
    last_staff = appeal.last_staff_message()
    unanswered = [w for w in appeal.waits if not w.answered]
    if unanswered and last_staff:
        from .speed import staff_requested_data, staff_promised
        if staff_requested_data(last_staff.text):
            return "ОС запросило данные, Гость молчит — ожидаются данные Гостя"
        if staff_promised(last_staff.text):
            return "Обещание уточнить без продолжения — проверьте, вернулись ли с ответом"
    return ""
