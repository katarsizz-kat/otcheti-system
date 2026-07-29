"""Система маскотов приложения."""
import random

# База данных маскотов
MASCOTS = {
    "dino": {
        "emoji": "🦖",
        "name": "Дино",
        "default_texts": [
            "Привет! Я Дино!",
            "Ррр! Как дела?",
            "Люблю отчёты и пиццу! 🍕",
            "Нажми на баннер праздника! 🎉",
            "Я маленький, но храбрый!",
            "Давай сформируем отчёт?",
        ],
    },
}


def get_mascot(mascot_type: str) -> dict:
    """Возвращает данные маскота по типу."""
    return MASCOTS.get(mascot_type, MASCOTS["dino"])


def get_mascot_emoji(mascot_type: str) -> str:
    """Возвращает эмодзи маскота."""
    mascot = get_mascot(mascot_type)
    return mascot["emoji"]


def get_mascot_text(mascot_type: str, custom_text: str = None) -> str:
    """
    Возвращает текст маскота.
    Если custom_text не указан, возвращает случайную фразу.
    """
    if custom_text:
        return custom_text
    mascot = get_mascot(mascot_type)
    return random.choice(mascot["default_texts"])


def get_all_mascot_types() -> list:
    """Возвращает список всех доступных типов маскотов."""
    return list(MASCOTS.keys())
