"""
Работа с ресторанами по Битрикс-чатам (методика v4).

В проверку ответов ресторанов включаются вопросы ОС по выполненным
заказам, оплате/возвратам и жалобы на сотрудников. Изменения текущего
заказа (адрес/время/состав/отмена) из ожидающих ответа исключаются —
отсутствие ответа ресторана на них не проблема. Разделяются: ответ не
найден, повторный запрос, обещанный ответ Гостю. Обратное направление —
«Запросы ресторанов к ОС» (промокод/бонусы), отдельно просьбы промокода
на ДР вне официальных часов 11:00–23:00.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

from report.complaints_control import constants as cc
from report.complaints_control.data import load_chat_messages
from report.complaints_control.phone import find_phones_in_text

from . import constants as c
from .merge import Appeal

RESTAURANT_WORK_COLS = [
    "Тикеты", "Заказ", "Ресторан", "Тип вопроса", "Дата вопроса ОС",
    "Вопрос ОС", "Ответ ресторана", "Основание ответа", "Ответ (фрагмент)",
    "Повторных запросов", "Сотрудник ОС",
]
REVERSE_COLS = ["Дата", "Источник", "Автор", "Текст", "Вне часов ОС (ДР)"]

# Ответ ресторана часто не повторяет номер заказа — тогда ищем ближайшую
# реплику ресторана в том же чате после вопроса ОС и честно помечаем её
# как требующую сверки (отсутствие однозначной ветки не доказывает молчание).
REPLY_PROXIMITY_MIN = 120

_REVERSE_RE = re.compile(
    r"прошу\s+(?:отправить|выдать|начислить|выслать)|отправьте\s+промокод|"
    r"начислите\s+бонусы|выдайте\s+промокод|промокод\s+на\s+(?:др|день)|"
    r"скидк\w*\s+на\s+(?:др|день)"
)


def load_bitrix(chat_spb, chat_tmn, warnings: List[str]) -> pd.DataFrame:
    frames = []
    for file, label in ((chat_spb, "Обратная связь Гости"), (chat_tmn, "Гости ОС Тюмень")):
        if file is None:
            continue
        df = load_chat_messages(file, label, warnings)
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["Дата", "Автор", "Текст", "Источник", "Сотрудник ОС"])
    out = pd.concat(frames, ignore_index=True)
    out["Сотрудник ОС"] = out["Автор"].map(lambda a: c.OS_BITRIX_AUTHORS.get(str(a).strip(), ""))
    return out.sort_values("Дата").reset_index(drop=True)


def _is_change_request(text: str) -> bool:
    t = str(text or "").lower()
    return any(marker in t for marker in cc.LOGISTICS_CHANGE_MARKERS)


def _snippet(text: str, limit: int = 160) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]


def restaurant_work(
    appeals: List[Appeal],
    bitrix: pd.DataFrame,
    restaurant_names: Dict[str, str],
) -> Tuple[pd.DataFrame, Dict[str, int], pd.DataFrame, int]:
    """Возвращает (таблица работы с ресторанами, передачи жалоб по сотрудникам,
    обратные запросы ресторанов, число ДР-просьб вне часов ОС)."""
    empty_work = pd.DataFrame(columns=RESTAURANT_WORK_COLS)
    empty_reverse = pd.DataFrame(columns=REVERSE_COLS)
    if bitrix is None or bitrix.empty:
        return empty_work, {}, empty_reverse, 0

    rows = []
    transfers: Dict[str, int] = {}
    # Передача жалобы ищется по НОМЕРУ ТЕЛЕФОНА Гостя (правило 25.11.2026),
    # а не по номеру заказа: телефон в чатах встречается чаще заказа.
    bitrix = bitrix.copy()
    bitrix["_phones"] = bitrix["Текст"].map(
        lambda t: {p[-10:] for p in find_phones_in_text(t)}
    )
    for appeal in appeals:
        if not appeal.phone:
            continue
        mask = bitrix["_phones"].map(lambda phones: appeal.phone in phones)
        matched = bitrix[mask]
        if matched.empty:
            continue
        os_msgs = matched[matched["Сотрудник ОС"] != ""]
        rest_msgs = matched[matched["Сотрудник ОС"] == ""]
        if os_msgs.empty:
            continue

        first_os = os_msgs.iloc[0]
        change_only = all(_is_change_request(t) for t in os_msgs["Текст"])
        qtype = "Изменение текущего заказа" if change_only else "Жалоба/вопрос по заказу"
        later_rest = rest_msgs[rest_msgs["Дата"] >= first_os["Дата"]]
        basis = ""
        if not later_rest.empty:
            answered = True
            basis = "по телефону Гостя"
            reply_row = later_rest.iloc[0]
        else:
            same_chat = bitrix[
                (bitrix["Источник"] == first_os["Источник"])
                & (bitrix["Сотрудник ОС"] == "")
            ]
            near = same_chat[
                (same_chat["Дата"] >= first_os["Дата"])
                & (same_chat["Дата"] <= first_os["Дата"] + pd.Timedelta(minutes=REPLY_PROXIMITY_MIN))
            ]
            answered = not near.empty
            if answered:
                basis = "по времени в том же чате (требует сверки)"
                reply_row = near.iloc[0]
            else:
                reply_row = None
        employee = str(first_os["Сотрудник ОС"])
        if not change_only:
            transfers[employee] = transfers.get(employee, 0) + 1

        rows.append({
            "Тикеты": ", ".join(map(str, appeal.tickets)),
            "Заказ": ", ".join(appeal.order_raws) or ", ".join(appeal.orders),
            "Ресторан": restaurant_names.get(appeal.key, appeal.city),
            "Тип вопроса": qtype,
            "Дата вопроса ОС": first_os["Дата"],
            "Вопрос ОС": _snippet(first_os["Текст"]),
            "Ответ ресторана": "Найден" if answered else "Не найден",
            "Основание ответа": basis,
            "Ответ (фрагмент)": _snippet(reply_row["Текст"]) if reply_row is not None else "",
            "Повторных запросов": max(len(os_msgs) - 1, 0),
            "Сотрудник ОС": employee,
        })

    work = pd.DataFrame(rows, columns=RESTAURANT_WORK_COLS) if rows else empty_work

    reverse_rows = []
    dr_offhours = 0
    rest_all = bitrix[bitrix["Сотрудник ОС"] == ""]
    for _, m in rest_all.iterrows():
        text = str(m["Текст"])
        if not _REVERSE_RE.search(text.lower()):
            continue
        is_birthday = any(marker in text.lower() for marker in cc.BIRTHDAY_MARKERS)
        hour = m["Дата"].hour if pd.notna(m["Дата"]) else None
        offhours = bool(
            is_birthday and hour is not None
            and not (c.OFFICIAL_HOURS[0] <= hour < c.OFFICIAL_HOURS[1])
        )
        if offhours:
            dr_offhours += 1
        reverse_rows.append({
            "Дата": m["Дата"],
            "Источник": m["Источник"],
            "Автор": m["Автор"],
            "Текст": _snippet(text, 300),
            "Вне часов ОС (ДР)": "Да" if offhours else "",
        })
    reverse = pd.DataFrame(reverse_rows, columns=REVERSE_COLS) if reverse_rows else empty_reverse
    return work, transfers, reverse, dr_offhours
