"""Модуль для отправки уведомлений через Telegram."""
import requests
from datetime import datetime, date
import streamlit as st
from typing import Optional


def get_telegram_config():
    """Получить конфигурацию Telegram из secrets."""
    try:
        bot_token = st.secrets["telegram"]["bot_token"]
        chat_id = st.secrets["telegram"]["chat_id"]
        return bot_token, chat_id
    except KeyError:
        return None, None


def send_telegram_message(message: str, parse_mode: str = "HTML") -> bool:
    """
    Отправить сообщение в Telegram.
    
    Args:
        message: Текст сообщения
        parse_mode: Режим парсинга ("HTML" или "Markdown")
    
    Returns:
        bool: True если успешно, False иначе
    """
    bot_token, chat_id = get_telegram_config()
    
    if not bot_token or not chat_id:
        st.warning("⚠️ Telegram не настроен. Добавьте token и chat_id в secrets.")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Ошибка отправки Telegram: {str(e)}")
        return False


def send_reminder_notification(event: dict) -> bool:
    """
    Отправить напоминание о событии.
    
    Args:
        event: Словарь с данными события
    
    Returns:
        bool: True если успешно
    """
    title = event.get('title', 'Без названия')
    start_date = event.get('start_date', '')
    category = event.get('category', '')
    location = event.get('location_custom') or event.get('location_type', '')
    
    # Форматируем дату
    try:
        date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        date_str = date_obj.strftime("%d.%m.%Y")
    except:
        date_str = start_date
    
    message = f"""
 <b>Напоминание о событии</b>

📌 <b>{title}</b>

📅 Дата: {date_str}
🏷 Категория: {category}
📍 Локация: {location}

<i>Календарь событий</i>
    """.strip()
    
    return send_telegram_message(message)


def send_daily_summary(events: list) -> bool:
    """
    Отправить ежедневную сводку событий.
    
    Args:
        events: Список событий на сегодня
    
    Returns:
        bool: True если успешно
    """
    if not events:
        return True
    
    today = date.today().strftime("%d.%m.%Y")
    
    message = f"""
📋 <b>События на сегодня ({today})</b>

Всего событий: {len(events)}

"""
    
    for i, event in enumerate(events[:10], 1):  # Максимум 10 событий
        title = event.get('title', 'Без названия')
        start_date = event.get('start_date', '')
        category = event.get('category', '')
        
        try:
            date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            time_str = date_obj.strftime("%H:%M")
        except:
            time_str = ""
        
        message += f"{i}. <b>{title}</b>\n"
        if time_str:
            message += f"   ⏰ {time_str}\n"
        message += f"   🏷 {category}\n\n"
    
    if len(events) > 10:
        message += f"... и ещё {len(events) - 10} событий\n"
    
    message += "\n<i>Календарь событий</i>"
    
    return send_telegram_message(message)


def test_telegram_connection() -> bool:
    """
    Протестировать соединение с Telegram.
    
    Returns:
        bool: True если успешно
    """
    message = "✅ <b>Telegram подключён!</b>\n\nТеперь вы будете получать напоминания о событиях."
    return send_telegram_message(message)
