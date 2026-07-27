"""Определение времени суток и приветствий."""
from datetime import datetime


def get_current_greeting() -> dict:
    """
    Возвращает приветствие в зависимости от времени суток.
    
    Returns:
        dict с ключами: icon, greeting, theme, hour
    """
    hour = datetime.now().hour
    
    greetings = {
        "morning": {
            "icon": "☀️",
            "greeting": "Доброго утречка!",
            "theme": "day",
            "range": (5, 12),
        },
        "day": {
            "icon": "🌤",
            "greeting": "Доброго денёчка!",
            "theme": "day",
            "range": (12, 18),
        },
        "evening": {
            "icon": "🌇",
            "greeting": "Не засидись допоздна 😊",
            "theme": "evening",
            "range": (18, 23),
        },
        "night": {
            "icon": "🌙",
            "greeting": " Пупупум... а кто это тут не спит? ",
            "theme": "night",
            "range": (23, 5),
        },
    }
    
    for key, data in greetings.items():
        start, end = data["range"]
        if start < end:
            if start <= hour < end:
                return {"icon": data["icon"], "greeting": data["greeting"], 
                        "theme": data["theme"], "hour": hour}
        else:  # ночной диапазон (23-5)
            if hour >= start or hour < end:
                return {"icon": data["icon"], "greeting": data["greeting"], 
                        "theme": data["theme"], "hour": hour}
    
    # fallback
    return {"icon": "", "greeting": "Добрый день!", "theme": "day", "hour": hour}