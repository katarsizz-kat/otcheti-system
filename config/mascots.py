"""Логика работы с фразами маскотов."""
import json
import random
import os
from datetime import datetime

# Путь к файлу с фразами
MASCOTS_FILE = os.path.join(os.path.dirname(__file__), "mascots.json")

# Кэш для загруженных фраз
_phrases_cache = None

def load_phrases():
    """Загружает фразы из JSON файла."""
    global _phrases_cache
    if _phrases_cache is None:
        try:
            with open(MASCOTS_FILE, 'r', encoding='utf-8') as f:
                _phrases_cache = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки mascots.json: {e}")
            _phrases_cache = {
                "humor": ["РРР, привеетики!"],
                "motivation": ["Ты можешь всё!"],
                "wishes": ["Хорошего дня!"],
                "horoscope": ["Рыбам сегодня повезёт!"],
                "kristina_special": "Кристина лучшая ❤️"
            }
    return _phrases_cache

def get_mascot_emoji(mascot_type: str = "dino") -> str:
    """Возвращает эмодзи для маскота."""
    emojis = {
        "dino": "🦖",
        "pizza": "🍕",
        "star": "⭐"
    }
    return emojis.get(mascot_type, "🦖")

def get_mascot_text(mascot_type: str = "dino") -> str:
    """Возвращает случайную фразу для маскота."""
    phrases = load_phrases()
    
    # Проверяем, нужно ли показать специальную фразу для Кристины
    # (каждое пятое открытие)
    click_count_key = f"{mascot_type}_click_count"
    if click_count_key not in load_phrases():
        load_phrases()[click_count_key] = 0
    
    load_phrases()[click_count_key] += 1
    
    if load_phrases()[click_count_key] % 5 == 0:
        return phrases.get("kristina_special", "Кристина лучшая ❤️")
    
    # Случайный выбор категории
    categories = ["humor", "motivation", "wishes", "horoscope"]
    category = random.choice(categories)
    
    category_phrases = phrases.get(category, [])
    if not category_phrases:
        return "РРР!"
    
    return random.choice(category_phrases)

def get_random_phrase() -> str:
    """Возвращает случайную фразу (для пасхалки)."""
    return get_mascot_text("dino")
