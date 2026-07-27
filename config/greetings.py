"""Приветствия и определение времени суток."""
from datetime import datetime, timezone, timedelta


# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))


def get_current_hour():
    """Возвращает текущий час по московскому времени."""
    now = datetime.now(MOSCOW_TZ)
    return now.hour


def get_current_greeting():
    """
    Возвращает приветствие и тему в зависимости от времени суток.
    
    Время определяется по московскому часовому поясу (UTC+3).
    """
    hour = get_current_hour()
    
    if 5 <= hour < 12:
        return {
            "theme": "day",
            "icon": "☀️",
            "greeting": "Доброе утро!",
            "subtitle": "Начните день с формирования отчётов"
        }
    elif 12 <= hour < 18:
        return {
            "theme": "day",
            "icon": "",
            "greeting": "Добрый день!",
            "subtitle": "Продолжайте работу с отчётами"
        }
    elif 18 <= hour < 23:
        return {
            "theme": "evening",
            "icon": "",
            "greeting": "Добрый вечер!",
            "subtitle": "Подведите итоги дня"
        }
    else:  # 23:00 - 05:00
        return {
            "theme": "night",
            "icon": "🌜",
            "greeting": "Доброй ночи!",
            "subtitle": "Ночные отчёты — тоже отчёты"
        }
