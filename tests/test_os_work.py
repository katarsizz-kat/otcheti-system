# tests/test_os_work.py

"""
Тесты модуля «Работа ОС» (методика v4, ред. 18.11.2026).

Запуск: python tests/test_os_work.py

Данные синтетические: реальные выгрузки и отчёты в репозиторий не попадают.
Все naive-даты в фикстурах — UTC (как в реальном API), Москва = UTC+3.
"""

from __future__ import annotations

import io
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from openpyxl import load_workbook

from report.os_work import constants as c
from report.os_work import crm, restaurants
from report.os_work.builder import build_os_work_report
from report.os_work.merge import appeal_key, build_appeals
from report.os_work.models import OsWorkRequest, OsWorkSettings, OsWorkSourceFiles
from report.os_work.speed import compute_waits, is_closing, mark_first_repeat, work_minutes

OFFICE = "Санкт-Петербург (Офис)"
FEEDBACK = "Санкт-Петербург (Feedback)"
SYSTEM = "Системный пользователь"
MARKETING = "Marketing SPB"


# ==========================================================
# ФИКСТУРЫ СИНТЕТИЧЕСКОЙ ВЫГРУЗКИ unified-2
# ==========================================================
def _guest_block(phone, replicas):
    """replicas: [(who, utc_ts, text)] — блок «Информация клиента»."""
    lines = ["Информация клиента:", f"Телефон: {phone}", "Email: ", ""]
    for who, ts, text in replicas:
        lines.append(f"{who} ({ts}): {text}")
        lines.append("")
    return "\n".join(lines)


def _system_entry(entry_id, utc_ts, text, technical=False):
    return {
        "id": entry_id, "text": text,
        "from": {"id": "sys", "name": SYSTEM, "role_name": "Администратор"},
        "created_at": utc_ts, "is_comment": False, "is_technical": technical,
        "is_successfully": None, "attachments": None, "additional_info": None,
    }


def _staff_entry(entry_id, author, utc_ts, text, comment=False, attachments=None):
    return {
        "id": entry_id, "text": text,
        "from": {"id": author, "name": author, "role_name": "Территориальный управляющий"},
        "created_at": utc_ts, "is_comment": comment, "is_technical": False,
        "is_successfully": None, "attachments": attachments, "additional_info": None,
    }


def make_export(cards, period=("2026-11-17", "2026-11-18"), complete=True):
    """cards: [{number, city, restaurant_id, created_utc, entries}]"""
    items, dialogs = [], []
    for card in cards:
        description = ""
        for e in card["entries"]:
            if "Информация клиента" in e.get("text", ""):
                description = e["text"]
                break
        items.append({
            "id": f"uuid-{card['number']}", "number": card["number"],
            "human_number": str(card["number"]),
            "title": "Бот поддержки создал новое обращение",
            "description": description,
            "assignee": {"name": card.get("assignee", OFFICE)},
            "group": None,
            "status": {"value": card.get("status", "completed")},
            "city": card.get("city", "Санкт-Петербург"),
            "restaurant_id": card.get("restaurant_id"),
            "order_id": None, "cause_type": None, "issue_type": None, "result": None,
            "source": "lia", "priority": None, "client_id": None,
            "created_at": card["created_utc"],
            "created_at_moscow": None,
            "updated_at": card["created_utc"],
            "updated_at_moscow": None,
            "messages": [],
        })
        dialogs.append({
            "id": f"uuid-{card['number']}", "number": card["number"],
            "complete": True, "pages": 1, "total": len(card["entries"]),
            "snapshot_updated_at": card["created_utc"],
            "entries": card["entries"],
        })
    return {
        "format": "crm-pj-readonly-unified-2",
        "collector_version": "2026-11-10.3",
        "complete": complete, "phase": "finished",
        "period": {"from": period[0], "to_inclusive": period[1], "time_zone": "Europe/Moscow"},
        "registry": {
            "items": items, "total": 59001, "in_period": len(items),
            "complete": complete, "boundary_reached": True, "stability_verified": True,
            "excluded_in_period": [], "pages_read": 1, "seen": len(items),
            "last_page": 1967, "order": "updated_at descending",
        },
        "dialogs": dialogs, "cached_dialogs": dialogs,
        "errors": [], "warnings": [],
        "stats": {"selected": len(cards), "attempted": len(cards), "ok": len(cards),
                  "failed": 0, "records": sum(len(x["entries"]) for x in cards)},
        "coverage": {"all_organization": False, "atomic_snapshot": False,
                     "message_period_filter_required": True, "cross_period_ledger_required": True},
        "refresh_rounds": [{"round": 1, "reused": 0, "downloaded": len(cards), "stable": True}],
    }


def parse(cards, **kwargs):
    return crm.parse_crm_export(json.dumps(make_export(cards, **kwargs)))


def simple_card(number, phone, guest_utc, guest_text, answer_utc=None,
                answer_author=OFFICE, answer_text="Здравствуйте! Уточнили, заказ уже в пути.",
                restaurant_id=198, created_utc=None):
    entries = [_system_entry(
        f"g{number}", created_utc or guest_utc,
        _guest_block(phone, [("Клиент", guest_utc, guest_text)]),
    )]
    if answer_utc:
        entries.append(_staff_entry(f"a{number}", answer_author, answer_utc, answer_text))
    return {
        "number": number, "restaurant_id": restaurant_id,
        "created_utc": created_utc or guest_utc, "entries": entries,
    }


# ==========================================================
# ЧАСОВЫЕ ПОЯСА И РАЗБОР
# ==========================================================
def test_parse_utc_to_msk() -> None:
    export = parse([simple_card(1, "+79111111111", "2026-11-18 10:00:00", "где заказ?",
                                answer_utc="2026-11-18 10:30:00")])
    card = export.cards[0]
    guest = card.guest_messages()[0]
    staff = card.staff_messages()[0]
    assert guest.ts == datetime(2026, 11, 18, 13, 0, 0), guest.ts
    assert staff.ts == datetime(2026, 11, 18, 13, 30, 0), staff.ts
    assert card.phone == "9111111111"


def test_parse_explicit_msk_no_double_shift() -> None:
    data = make_export([simple_card(1, "+79111111111", "2026-11-18 10:00:00", "вопрос")])
    data["registry"]["items"][0]["created_at_moscow"] = "2026-11-18 13:00:00+03:00"
    export = crm.parse_crm_export(json.dumps(data))
    assert export.cards[0].created == datetime(2026, 11, 18, 13, 0, 0)


def test_guest_replicas_dedup_and_bot() -> None:
    block1 = _guest_block("+79111111111", [
        ("Клиент", "2026-11-18 10:00:00", "где заказ?"),
        ("Бот", "2026-11-18 10:00:01", "Здравствуйте! Упс, кажется, что-то пошло не так!"),
    ])
    block2 = _guest_block("+79111111111", [
        ("Клиент", "2026-11-18 10:00:00", "где заказ?"),
        ("Бот", "2026-11-18 10:00:01", "Здравствуйте! Упс, кажется, что-то пошло не так!"),
        ("Клиент", "2026-11-18 10:02:00", "заказ sankt-peterburg-8-58936486-AP опаздывает"),
    ])
    card = {
        "number": 7, "restaurant_id": 198, "created_utc": "2026-11-18 10:00:00",
        "entries": [
            _system_entry("s1", "2026-11-18 10:00:02", block1),
            _system_entry("s2", "2026-11-18 10:02:01", block2),
        ],
    }
    export = parse([card])
    msgs = export.cards[0].messages
    guests = [m for m in msgs if m.kind == "guest"]
    bots = [m for m in msgs if m.kind == "bot"]
    assert len(guests) == 2, guests
    assert len(bots) == 1
    assert guests[1].ts == datetime(2026, 11, 18, 13, 2, 0)


def test_technical_and_comment_not_answers() -> None:
    card = simple_card(2, "+79111111111", "2026-11-18 10:00:00", "где заказ?")
    card["entries"].append(_system_entry("t2", "2026-11-18 10:05:00",
                                         "Офис изменил статус на В ожидании.", technical=True))
    card["entries"].append(_staff_entry("c2", OFFICE, "2026-11-18 10:06:00",
                                        "внутренний комментарий", comment=True))
    export = parse([card])
    waits = compute_waits(export.cards[0].messages)
    assert len(waits) == 1 and not waits[0].answered


def test_registry_messages_newer_than_dialog() -> None:
    # Реестр содержит ответ новее снапшота диалога — он должен попасть в историю.
    card = simple_card(50, "+79111111111", "2026-11-18 10:00:00", "где заказ?")
    data = make_export([card])
    data["registry"]["items"][0]["messages"] = [
        _staff_entry("newer", MARKETING, "2026-11-18 10:40:00", "Заказ в пути."),
    ]
    export = crm.parse_crm_export(json.dumps(data))
    msgs = export.cards[0].messages
    assert any(m.kind == "staff" and m.author == MARKETING for m in msgs)
    waits = compute_waits(msgs)
    assert len(waits) == 1 and waits[0].answered
    assert waits[0].minutes == 40.0  # 13:00 -> 13:40 МСК


def test_old_card_thanks_is_continuation() -> None:
    # Вопрос и ответ 16.11, благодарность 17.11 — продолжение, не новое обращение.
    card = {
        "number": 51, "restaurant_id": 198, "created_utc": "2026-11-16 10:00:00",
        "entries": [
            _system_entry("g51", "2026-11-16 10:00:00", _guest_block("+79111111111", [
                ("Клиент", "2026-11-16 10:00:00", "где заказ?"),
            ])),
            _staff_entry("a51", OFFICE, "2026-11-16 10:10:00", "Заказ в пути."),
            _system_entry("g51b", "2026-11-17 10:00:00", _guest_block("+79111111111", [
                ("Клиент", "2026-11-16 10:00:00", "где заказ?"),
                ("Клиент", "2026-11-17 10:00:00", "спасибо, всё получили!"),
            ])),
        ],
    }
    files = OsWorkSourceFiles(crm_json=json.dumps(make_export([card])))
    settings = OsWorkSettings(True, date(2026, 11, 17), date(2026, 11, 18))
    result = build_os_work_report(OsWorkRequest(files=files, settings=settings, check_not_entered=False))
    assert result.success, result.error
    assert result.data.totals["обращений"] == 0


# ==========================================================
# СКОРОСТЬ
# ==========================================================
def test_work_minutes_window() -> None:
    # 22:50 -> завтра 11:20 = 8 + 10 = 18 минут (пример из правил).
    t1 = datetime(2026, 11, 17, 22, 50)
    t2 = datetime(2026, 11, 18, 11, 20)
    assert work_minutes(t1, t2) == 18.0
    # Внутри окна.
    assert work_minutes(datetime(2026, 11, 18, 11, 20), datetime(2026, 11, 18, 11, 50)) == 30.0
    # Полностью вне окна.
    assert work_minutes(datetime(2026, 11, 17, 23, 30), datetime(2026, 11, 18, 10, 0)) == 0.0
    # Ответ после полуночи до открытия — только минуты до 22:58.
    assert work_minutes(datetime(2026, 11, 17, 22, 50), datetime(2026, 11, 18, 0, 30)) == 8.0
    # Ровно в 22:58 доступных минут текущего дня уже нет.
    assert work_minutes(datetime(2026, 11, 17, 22, 58), datetime(2026, 11, 17, 23, 30)) == 0.0
    # Минуты до открытия окна 11:10 не считаются.
    assert work_minutes(datetime(2026, 11, 18, 11, 4), datetime(2026, 11, 18, 11, 20)) == 10.0


def test_series_and_one_wait() -> None:
    card = {
        "number": 3, "restaurant_id": 198, "created_utc": "2026-11-18 08:20:00",
        "entries": [_system_entry("g3", "2026-11-18 08:24:00", _guest_block("+79111111111", [
            ("Клиент", "2026-11-18 08:20:00", "где заказ?"),
            ("Клиент", "2026-11-18 08:22:00", "дополняю: заказ ко времени"),
            ("Клиент", "2026-11-18 08:24:00", "и соус забыли"),
        ]))],
    }
    card["entries"].append(_staff_entry("a3", OFFICE, "2026-11-18 08:40:00", "Уточняем."))
    export = parse([card])
    waits = compute_waits(export.cards[0].messages)
    assert len(waits) == 1
    # Отсчёт от последнего сообщения серии: 11:24 -> 11:40 = 16 минут.
    assert waits[0].minutes == 16.0, waits[0].minutes
    assert waits[0].question_ts == datetime(2026, 11, 18, 11, 20, 0)


def test_late_reminder_does_not_reset() -> None:
    card = {
        "number": 4, "restaurant_id": 198, "created_utc": "2026-11-18 08:20:00",
        "entries": [_system_entry("g4", "2026-11-18 08:45:00", _guest_block("+79111111111", [
            ("Клиент", "2026-11-18 08:20:00", "где заказ?"),
            ("Клиент", "2026-11-18 08:22:00", "жду"),
            ("Клиент", "2026-11-18 08:45:00", "напоминание: где заказ?"),
        ]))],
    }
    card["entries"].append(_staff_entry("a4", OFFICE, "2026-11-18 09:00:00", "Курьер в пути."))
    export = parse([card])
    waits = compute_waits(export.cards[0].messages)
    assert len(waits) == 1
    # 11:22 -> 12:00 = 38 минут, напоминание в 11:45 не обнулило ожидание.
    assert waits[0].minutes == 38.0, waits[0].minutes


def test_thanks_and_consent() -> None:
    assert is_closing("Спасибо!!! 😊")
    assert is_closing("ок")
    assert not is_closing("давайте промокод")
    # Согласие на компенсацию требует действия ОС — не завершение.
    assert not is_closing("да, давайте", prev_staff_text="Начислим промокод за опоздание.")

    card = {
        "number": 5, "restaurant_id": 198, "created_utc": "2026-11-18 08:00:00",
        "entries": [_system_entry("g5", "2026-11-18 08:06:00", _guest_block("+79111111111", [
            ("Клиент", "2026-11-18 08:00:00", "где заказ?"),
        ]))],
    }
    card["entries"].append(_staff_entry("a5", OFFICE, "2026-11-18 08:05:00", "Курьер в пути."))
    card["entries"].append(_system_entry("g5b", "2026-11-18 08:06:00", _guest_block("+79111111111", [
        ("Клиент", "2026-11-18 08:00:00", "где заказ?"),
        ("Клиент", "2026-11-18 08:06:00", "спасибо!"),
    ])))
    export = parse([card])
    waits = compute_waits(export.cards[0].messages)
    assert len(waits) == 1 and waits[0].answered


def test_bot_not_os_answer() -> None:
    card = {
        "number": 6, "restaurant_id": 198, "created_utc": "2026-11-18 08:20:00",
        "entries": [_system_entry("g6", "2026-11-18 08:21:00", _guest_block("+79111111111", [
            ("Клиент", "2026-11-18 08:20:00", "где заказ?"),
            ("Бот", "2026-11-18 08:21:00", "Уточнить можно у оператора по телефону."),
        ]))],
    }
    card["entries"].append(_staff_entry("a6", OFFICE, "2026-11-18 08:50:00", "Заказ в пути."))
    export = parse([card])
    waits = compute_waits(export.cards[0].messages)
    assert len(waits) == 1 and waits[0].minutes == 30.0
    assert waits[0].author == OFFICE


def test_marketing_closes_wait_not_personal() -> None:
    export = parse([simple_card(8, "+79111111111", "2026-11-18 08:20:00", "почему опоздание?",
                                answer_utc="2026-11-18 08:30:00", answer_author=MARKETING)])
    appeals, _ = build_appeals(export.cards)
    a = appeals[0]
    assert len(a.waits) == 1 and a.waits[0].answered and a.waits[0].minutes == 10.0
    from report.os_work.stats import employee_waits
    assert len(employee_waits(appeals, None)) == 1
    assert len(employee_waits(appeals, "Женя")) == 0
    assert a.employees == []  # Marketing не сотрудник ОС


def test_first_repeat() -> None:
    card = {
        "number": 9, "restaurant_id": 198, "created_utc": "2026-11-18 08:20:00",
        "entries": [_system_entry("g9", "2026-11-18 08:40:00", _guest_block("+79111111111", [
            ("Клиент", "2026-11-18 08:20:00", "где заказ?"),
            ("Клиент", "2026-11-18 08:40:00", "а соус вернёте?"),
        ]))],
    }
    card["entries"].append(_staff_entry("a9", OFFICE, "2026-11-18 08:30:00", "Заказ в пути."))
    card["entries"].append(_staff_entry("a9b", OFFICE, "2026-11-18 08:45:00", "Начислим бонусы."))
    export = parse([card])
    waits = compute_waits(export.cards[0].messages)
    mark_first_repeat(waits)
    assert [w.kind for w in waits] == ["first", "repeat"]
    assert waits[0].minutes == 10.0 and waits[1].minutes == 5.0


def test_period_attribution() -> None:
    # Вопрос 16.11 23:00 МСК (прошлый период), ответ 17.11 11:30 МСК.
    export = parse([simple_card(10, "+79111111111", "2026-11-16 20:00:00", "где заказ?",
                                answer_utc="2026-11-17 08:30:00", created_utc="2026-11-16 20:00:00")])
    appeals, _ = build_appeals(export.cards)
    a = appeals[0]
    for w in a.waits:
        w.in_period = date(2026, 11, 17) <= w.question_ts.date() <= date(2026, 11, 18)
    assert len(a.waits) == 1
    assert not a.waits[0].in_period
    assert a.waits[0].minutes == 20.0  # 11:10 -> 11:30 следующего дня
    from report.os_work.stats import build_old_period_closed
    old = build_old_period_closed(appeals, date(2026, 11, 17), date(2026, 11, 18))
    assert len(old) == 1


# ==========================================================
# ОБЪЕДИНЕНИЕ И РЕСТОРАНЫ
# ==========================================================
def test_merge_same_phone_order() -> None:
    c1 = simple_card(11, "+79111111111", "2026-11-17 08:00:00",
                     "заказ sankt-peterburg-8-58936486-AP не привезли соус",
                     answer_utc="2026-11-17 08:10:00")
    c2 = simple_card(12, "+79111111111", "2026-11-17 09:00:00",
                     "по заказу 58936486 соус так и не вернули",
                     answer_utc="2026-11-17 09:05:00", created_utc="2026-11-17 09:00:00")
    export = parse([c1, c2])
    appeals, candidates = build_appeals(export.cards)
    assert len(appeals) == 1
    assert appeals[0].tickets == [11, 12]
    assert appeals[0].key == appeal_key([11, 12])
    assert not candidates


def test_same_phone_different_questions_not_merged() -> None:
    c1 = simple_card(13, "+79111111111", "2026-11-17 08:00:00", "где заказ 58936486?",
                     answer_utc="2026-11-17 08:10:00")
    c2 = simple_card(14, "+79111111111", "2026-11-17 12:00:00", "как списать бонусы?",
                     answer_utc="2026-11-17 12:05:00", created_utc="2026-11-17 12:00:00")
    export = parse([c1, c2])
    appeals, candidates = build_appeals(export.cards)
    assert len(appeals) == 2
    assert len(candidates) == 1  # возможный повтор — в очередь разметки


def test_restaurants_resolve() -> None:
    ref = restaurants.load_reference()
    name, known = restaurants.resolve_name(198, "Санкт-Петербург", ref)
    assert known and name == "Санкт-Петербург №8"
    name, known = restaurants.resolve_name(198, "Санкт-Петербург", ref, {8: "Серебристый"})
    assert known and "Серебристый" in name
    name, known = restaurants.resolve_name(214, "Тюмень", ref)
    assert not known and "ID 214" in name
    name, known = restaurants.resolve_name(999, "Санкт-Петербург", ref)
    assert not known


# ==========================================================
# НАСТРОЙКИ И ИМЕНА ФАЙЛОВ
# ==========================================================
def test_file_names() -> None:
    weekly = OsWorkSettings(True, date(2026, 11, 9), date(2026, 11, 15))
    assert weekly.period_kind == "недельная"
    assert weekly.file_name == "Проверка_работы_ОС_2026-11-09—2026-11-15_недельная_руководителю.xlsx"
    monthly = OsWorkSettings(True, date(2026, 10, 1), date(2026, 10, 31))
    assert monthly.period_kind == "месячная"
    assert monthly.file_name.endswith("_месячная_руководителю.xlsx")
    custom = OsWorkSettings(True, date(2026, 11, 17), date(2026, 11, 18))
    assert custom.period_kind == ""
    assert custom.file_name == "Проверка_работы_ОС_2026-11-17—2026-11-18_руководителю.xlsx"
    assert custom.personal_file_name("Женя").endswith("_Женя.xlsx")


# ==========================================================
# БИТРИКС: РАБОТА С РЕСТОРАНАМИ
# ==========================================================
def _bitrix_csv(rows):
    df = pd.DataFrame(rows, columns=["Дата", "Автор", "Текст сообщения"])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf


def test_bitrix_restaurant_work() -> None:
    from report.os_work.bitrix import load_bitrix, restaurant_work
    chat = _bitrix_csv([
        ["2026-11-17 12:00:00", "Евгений Яковлев", "по заказу 58936486 гость жалуется на холодную пиццу, проверьте"],
        ["2026-11-17 12:20:00", "Мария Сухова", "проверили, курьер задержался, гостю передадим промокод"],
        ["2026-11-17 13:00:00", "Евгений Яковлев", "измените адрес доставки по заказу 58936487, ул. Ленина 5"],
        ["2026-11-17 09:00:00", "Аня Копач", "прошу отправить промокод на др гостю"],
    ])
    df = load_bitrix(chat, None, [])
    assert len(df) == 4

    c1 = simple_card(21, "+79111111111", "2026-11-17 08:00:00",
                     "заказ sankt-peterburg-8-58936486-AP холодная пицца",
                     answer_utc="2026-11-17 08:10:00")
    c2 = simple_card(22, "+79222222222", "2026-11-17 08:30:00",
                     "заказ sankt-peterburg-8-58936487-AP измените адрес",
                     answer_utc="2026-11-17 08:40:00", created_utc="2026-11-17 08:30:00")
    export = parse([c1, c2])
    appeals, _ = build_appeals(export.cards)
    names = {a.key: "Санкт-Петербург №8" for a in appeals}
    work, transfers, reverse, dr_off = restaurant_work(appeals, df, names)
    assert len(work) == 2
    complaint_row = work[work["Заказ"].str.contains("58936486")].iloc[0]
    assert complaint_row["Ответ ресторана"] == "Найден"
    # Ответ ресторана без номера заказа найден по времени и помечен для сверки.
    assert "по времени" in complaint_row["Основание ответа"]
    assert complaint_row["Тип вопроса"] == "Жалоба/вопрос по заказу"
    change_row = work[work["Заказ"].str.contains("58936487")].iloc[0]
    assert change_row["Тип вопроса"] == "Изменение текущего заказа"
    assert transfers == {"Женя": 1}  # изменение заказа не считается передачей жалобы
    assert dr_off == 1  # ДР-просьба в 09:00 вне часов 11:00–23:00
    assert len(reverse) == 1


# ==========================================================
# СКВОЗНОЙ СЦЕНАРИЙ
# ==========================================================
def _end_to_end_request(overrides=None, check_not_entered=False):
    cards = [
        simple_card(31, "+79111111111", "2026-11-17 08:00:00",
                    "заказ sankt-peterburg-8-58936486-AP привезли холодную пиццу",
                    answer_utc="2026-11-17 08:10:00"),
        simple_card(32, "+79222222222", "2026-11-17 09:00:00", "где мой заказ?",
                    answer_utc="2026-11-17 09:40:00", created_utc="2026-11-17 09:00:00"),
        simple_card(33, "+79333333333", "2026-11-18 08:00:00", "как списать бонусы?",
                    answer_utc=None, created_utc="2026-11-18 08:00:00"),
    ]
    files = OsWorkSourceFiles(crm_json=json.dumps(make_export(cards)))
    settings = OsWorkSettings(True, date(2026, 11, 17), date(2026, 11, 18))
    return OsWorkRequest(files=files, settings=settings,
                         overrides=overrides or {}, check_not_entered=check_not_entered)


def test_builder_end_to_end() -> None:
    result = build_os_work_report(_end_to_end_request())
    assert result.success, result.error
    data = result.data
    assert data.totals["обращений"] == 3
    assert data.totals["без ответа"] == 1
    assert data.totals["дольше 20"] == 1  # 40 минут по карточке 32
    assert len(data.review_queue) == 3
    assert "Подсказка" in data.review_queue.columns

    wb = load_workbook(result.excels["руководителю"])
    assert c.SHEET_DASHBOARD in wb.sheetnames
    assert c.SHEET_NO_ANSWER in wb.sheetnames
    # Без Битрикса пустые разделы не создаются.
    assert c.SHEET_RESTAURANTS not in wb.sheetnames
    assert c.SHEET_NOT_ENTERED not in wb.sheetnames
    assert c.SHEET_REMARKS not in wb.sheetnames

    # Личная книга Жени есть, Полины нет (нет её сообщений).
    assert "Женя" in result.excels
    assert "Полина" not in result.excels
    pwb = load_workbook(result.excels["Женя"])
    assert pwb.sheetnames == [c.PERSONAL_SHEET_METRICS, c.PERSONAL_SHEET_APPEALS]
    metrics = data.personal["Женя"]["metrics"]
    assert "Полина" not in metrics.columns  # без сравнения с коллегой

    # Дашборд: строки с нулевым основным показателем не выводятся.
    labels = set(data.dashboard["Показатель"])
    assert "Нарушение тона" not in labels
    assert "Количество обращений" in labels


def test_manual_marking_changes_dashboard() -> None:
    base = build_os_work_report(_end_to_end_request())
    assert base.success, base.error
    keys = list(base.data.review_queue["Ключ"])
    overrides = {
        "outcome": {keys[0]: c.OUTCOME_SOLVED, keys[1]: c.OUTCOME_UNSOLVED},
        "tone": {keys[1]: "tone"},
        "wrong": {keys[0]: "wrong"},
    }
    marked = build_os_work_report(_end_to_end_request(overrides))
    assert marked.success, marked.error
    dash = marked.data.dashboard.set_index("Показатель")
    assert dash.loc["Вопрос решён, % (X из Y)", "Отдел"] == "50.0% (1 из 2)"
    assert dash.loc["Вопрос не решён", "Отдел"] == "1"
    assert dash.loc["Нарушение тона", "Отдел"] == "1"
    assert dash.loc["Ответ не к месту / неверная информация", "Отдел"] == "1"
    assert marked.data.totals["размечено"] == 2
    wb = load_workbook(marked.excels["руководителю"])
    assert c.SHEET_REMARKS in wb.sheetnames


def test_merge_override() -> None:
    cards = [
        simple_card(41, "+79111111111", "2026-11-17 08:00:00", "где заказ 58936486?",
                    answer_utc="2026-11-17 08:10:00"),
        simple_card(42, "+79111111111", "2026-11-17 12:00:00", "заказ 58936486 всё ещё не доставлен",
                    answer_utc="2026-11-17 12:05:00", created_utc="2026-11-17 12:00:00"),
    ]
    # Один телефон, разные вопросы без общего номера заказа — автоматически
    # не объединяются; пара уходит в очередь разметки.
    cards[1]["entries"][0]["text"] = _guest_block("+79111111111", [
        ("Клиент", "2026-11-17 12:00:00", "опять вопрос по доставке"),
    ])
    files = OsWorkSourceFiles(crm_json=json.dumps(make_export(cards)))
    settings = OsWorkSettings(True, date(2026, 11, 17), date(2026, 11, 18))
    base = build_os_work_report(OsWorkRequest(files=files, settings=settings, check_not_entered=False))
    assert base.success, base.error
    assert base.data.totals["обращений"] == 2
    assert len(base.data.merge_queue) == 1
    pair_key = base.data.merge_queue.iloc[0]["Ключ"]
    merged = build_os_work_report(OsWorkRequest(
        files=files, settings=settings,
        overrides={"merge": {pair_key: "merge"}}, check_not_entered=False,
    ))
    assert merged.success, merged.error
    assert merged.data.totals["обращений"] == 1


def main() -> None:
    tests = [
        test_parse_utc_to_msk,
        test_parse_explicit_msk_no_double_shift,
        test_guest_replicas_dedup_and_bot,
        test_technical_and_comment_not_answers,
        test_registry_messages_newer_than_dialog,
        test_old_card_thanks_is_continuation,
        test_work_minutes_window,
        test_series_and_one_wait,
        test_late_reminder_does_not_reset,
        test_thanks_and_consent,
        test_bot_not_os_answer,
        test_marketing_closes_wait_not_personal,
        test_first_repeat,
        test_period_attribution,
        test_merge_same_phone_order,
        test_same_phone_different_questions_not_merged,
        test_restaurants_resolve,
        test_file_names,
        test_bitrix_restaurant_work,
        test_builder_end_to_end,
        test_manual_marking_changes_dashboard,
        test_merge_override,
    ]
    for test in tests:
        test()
        print(f"OK  {test.__name__}")
    print(f"\nВсе тесты пройдены: {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    main()
