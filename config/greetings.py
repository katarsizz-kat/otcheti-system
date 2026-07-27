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
            "theme": "morning",  # Новая тема для утра
            "icon": "☀️",
            "greeting": "Доброго утречка!",
            "subtitle": "Начните день с формирования отчётов"
        }
    elif 12 <= hour < 18:
        return {
            "theme": "day",  # Тема для дня
            "icon": "️",
            "greeting": "Доброго денёчка!",
            "subtitle": "Продолжайте работу с отчётами"
        }
    elif 18 <= hour < 23:
        return {
            "theme": "evening",
            "icon": "",
            "greeting": "Не засидись допоздна)",
            "subtitle": "Подведите итоги дня"
        }
    else:  # 23:00 - 05:00
        return {
            "theme": "night",
            "icon": "🌜",
            "greeting": "Пупупум.... а кто это тут не спит?",
            "subtitle": "Ночные отчёты — тоже отчёты"
        }
