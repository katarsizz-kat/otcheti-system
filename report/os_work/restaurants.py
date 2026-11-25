"""
Расшифровка ресторанов: CRM restaurant_id -> название.

В JSON-выгрузке только числовые ID. Справочник ID->номер собран по
префиксам номеров заказов в текстах (sankt-peterburg-8-… = ресторан №8)
и именам менеджеров; номера->названия — по октябрьской CRM-выгрузке и
листу «Сводная» Google-таблицы СПб (уличные названия, если доступны).
Неизвестные ID показываются честно как «город (ID N)» и попадают
в предупреждения отчёта.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional, Tuple

TYUMEN_NAMES = {
    2: "Тюмень №2 – Орджоникидзе",
    3: "Тюмень №3 – Мельникайте (Южный)",
    4: "Тюмень №4 – Газавиков",
}

# Действующие рестораны СПб (подтверждено пользователем 25.11.2026).
# Номер вне списка = ресторан закрыт → помечаем «не выявлен».
SPB_ACTIVE_NUMBERS = {1, 2, 4, 5, 6, 7, 8, 13, 15, 16, 18, 20}

NOT_IDENTIFIED = "не выявлен"

_REF_PATH = os.path.join(os.path.dirname(__file__), "restaurants.json")


def load_reference() -> Dict[int, dict]:
    try:
        with open(_REF_PATH, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}
    return {int(k): v for k, v in raw.items() if not k.startswith("_")}


def resolve_name(
    restaurant_id: Optional[int],
    city: str,
    reference: Optional[Dict[int, dict]] = None,
    svodnaya_map: Optional[Dict[int, str]] = None,
) -> Tuple[str, bool]:
    """Возвращает (название, расшифрован ли ID)."""
    if restaurant_id is None:
        return (city or "Город не указан"), False
    ref = reference if reference is not None else load_reference()
    entry = ref.get(int(restaurant_id))
    if not entry:
        return f"{city or 'Город не указан'} (ID {restaurant_id})", False
    number = entry.get("number")
    entry_city = entry.get("city") or city
    if number is None:
        # ID есть, но номер не определён (закрыт/не из действующих) — не выявлен.
        return NOT_IDENTIFIED, True
    if entry_city == "Тюмень" and number in TYUMEN_NAMES:
        return TYUMEN_NAMES[number], True
    if entry_city == "Санкт-Петербург" and number not in SPB_ACTIVE_NUMBERS:
        return NOT_IDENTIFIED, True  # закрытый ресторан
    name = f"{entry_city} №{number}"
    if svodnaya_map and number in svodnaya_map:
        name = f"{name} — {svodnaya_map[number]}"
    return name, True
