"""Логика праздничных дней."""
import json
from pathlib import Path
from datetime import datetime, timedelta
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_holidays():
    """Загружает holidays.json один раз и кэширует."""
    holidays_path = Path(__file__).parent.parent / "holidays.json"
    if holidays_path.exists():
        with open(holidays_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_today_holiday():
    """Возвращает информацию о сегодняшнем празднике или None."""
    today = datetime.now()
    key = today.strftime("%m-%d")
    holidays = _load_holidays()

    if key not in holidays:
        return None

    data = holidays[key]

    # Старый формат (если вдруг встретится)
    if isinstance(data, str):
        return {
            "title": data,
            "emoji": "",
            "message": data,
            "effects": [],
        }

    # Новый формат
    if isinstance(data, dict):
        holiday = {
            "title": data.get("title", "Праздник"),
            "emoji": data.get("emoji", ""),
            "message": data.get("message", ""),
            "effects": data.get("effects", []),

            # Новые поля (для главных праздников)
            "theme": data.get("theme"),
            "button": data.get("button"),
            "popup": data.get("popup"),
            "animation": data.get("animation"),
            "sound": data.get("sound"),
            "mascot": data.get("mascot"),
            "secret": data.get("secret"),
        }

        return holiday

    return None


def get_upcoming_holidays(days=7):
    """Возвращает список предстоящих праздников."""
    holidays = _load_holidays()
    today = datetime.now()
    upcoming = []
    
    for i in range(1, days + 1):
        date = today + timedelta(days=i)
        key = date.strftime("%m-%d")
        
        if key in holidays:
            data = holidays[key]
            if isinstance(data, dict):
                upcoming.append({
                    "date": date.strftime("%d.%m"),
                    "title": data.get("title", "Праздник"),
                    "emoji": data.get("emoji", ""),
                })
            elif isinstance(data, str):
                upcoming.append({
                    "date": date.strftime("%d.%m"),
                    "title": data,
                    "emoji": "",
                })
    
    return upcoming
