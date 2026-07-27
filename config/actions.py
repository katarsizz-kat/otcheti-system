"""Система обработки праздничных действий."""
import random
import streamlit as st


# =============================================================================
# ДЕЙСТВИЯ
# =============================================================================

def action_new_year_gift(holiday: dict):
    """Новогодний подарок — случайный приз."""
    gifts = [
        "🎁 Счастливого Нового года! Пусть он принесёт удачу!",
        "🎄 Волшебства и чудес в новом году!",
        "✨ Исполнения всех желаний!",
        "🥂 Здоровья, счастья и успехов!",
        "🎊 Много радости и улыбок!",
    ]
    return {
        "type": "message",
        "title": "🎁 Подарок от Дино!",
        "text": random.choice(gifts),
        "icon": "",
    }


def action_confetti_burst(holiday: dict):
    """Взрыв конфетти."""
    return {
        "type": "effect",
        "effect": "confetti",
        "title": "🎊 Ура!",
        "text": "Праздничный взрыв конфетти!",
        "icon": "🎊",
    }


def action_balloon_release(holiday: dict):
    """Запуск воздушных шариков."""
    st.balloons()
    return {
        "type": "message",
        "title": "🎈 Шарики взлетели!",
        "text": "Пусть ваши мечты взлетят высоко-высоко!",
        "icon": "",
    }


def action_show_message(holiday: dict):
    """Показать сообщение из JSON."""
    message = holiday.get("button", {}).get("message", "Праздничное поздравление!")
    return {
        "type": "message",
        "title": "📢 Сообщение",
        "text": message,
        "icon": "📢",
    }


def action_play_sound(holiday: dict):
    """Воспроизвести звук (заглушка)."""
    sound_file = holiday.get("sound", {}).get("file", "")
    return {
        "type": "sound",
        "file": sound_file,
        "title": "🎵 Звук",
        "text": f"Воспроизведение: {sound_file}",
        "icon": "🎵",
        "note": "Звуки будут добавлены в следующей версии",
    }


def action_parachute_jump(holiday: dict):
    """Прыжок с парашютом (День ВДВ)."""
    return {
        "type": "message",
        "title": "🪂 Прыжок!",
        "text": "Виртуальный прыжок с парашютом выполнен! Высота 4000 метров!",
        "icon": "🪂",
    }


def action_make_wish(holiday: dict):
    """Загадать желание."""
    wishes = [
        "✨ Ваше желание записано в волшебную книгу!",
        "🌟 Звёзды услышали ваше желание!",
        "💫 Оно обязательно сбудется!",
    ]
    return {
        "type": "message",
        "title": " Желание загадано",
        "text": random.choice(wishes),
        "icon": "💭",
    }


def action_get_joke(holiday: dict):
    """Получить шутку (1 апреля)."""
    jokes = [
        "Почему динозавр не играет в прятки? Потому что его всегда видно издалека! 🦖",
        "Что сказал один отчёт другому? Давай объединимся! 📊",
        "Почему программисты любят кофе? Потому что без него они не компилируются! ",
    ]
    return {
        "type": "message",
        "title": "😂 Шутка дня",
        "text": random.choice(jokes),
        "icon": "😂",
    }


def action_get_fairy_tale(holiday: dict):
    """Получить сказку (День детской книги)."""
    tales = [
        "Жил-был динозавр, который очень любил отчёты... 🦖📚",
        "В некотором царстве, в некотором государстве жил принц, который мечтал о пицце... 👑🍕",
        "Давным-давно жила принцесса, которая умела формировать отчёты одним кликом... 👸✨",
    ]
    return {
        "type": "message",
        "title": " Сказка",
        "text": random.choice(tales),
        "icon": "📖",
    }


def action_get_recipe(holiday: dict):
    """Получить рецепт (День еды)."""
    recipes = {
        "pizza": "🍕 Рецепт пиццы: тесто + соус + сыр + любовь!",
        "cake": " Рецепт торта: мука + сахар + яйца + магия!",
        "coffee": "☕ Рецепт кофе: зёрна + вода + настроение!",
    }
    recipe_type = holiday.get("recipe_type", "pizza")
    return {
        "type": "message",
        "title": "🍳 Рецепт дня",
        "text": recipes.get(recipe_type, "Вкусного!"),
        "icon": "🍳",
    }


def action_default(holiday: dict):
    """Действие по умолчанию."""
    return {
        "type": "message",
        "title": "🎉 Праздник!",
        "text": f"Сегодня {holiday.get('title', 'праздник')}! {holiday.get('message', '')}",
        "icon": "",
    }


# =============================================================================
# РЕЕСТР ДЕЙСТВИЙ
# =============================================================================

ACTIONS = {
    "new_year_gift": action_new_year_gift,
    "confetti_burst": action_confetti_burst,
    "balloon_release": action_balloon_release,
    "show_message": action_show_message,
    "play_sound": action_play_sound,
    "parachute_jump": action_parachute_jump,
    "make_wish": action_make_wish,
    "get_joke": action_get_joke,
    "get_fairy_tale": action_get_fairy_tale,
    "get_recipe": action_get_recipe,
}


def execute_action(action_name: str, holiday: dict = None):
    """
    Выполняет действие по имени.
    
    Args:
        action_name: Название действия (из JSON)
        holiday: Данные праздника
    
    Returns:
        dict: Результат действия
    """
    if holiday is None:
        holiday = {}
    
    action_func = ACTIONS.get(action_name, action_default)
    return action_func(holiday)


def get_all_actions() -> list:
    """Возвращает список всех доступных действий."""
    return list(ACTIONS.keys())