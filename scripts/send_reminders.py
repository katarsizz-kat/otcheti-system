"""
Автономный скрипт для отправки ежедневных напоминаний.
Запускается через GitHub Actions каждый день в 10:00 по Москве.
"""
import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict

# Добавляем корень проекта в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client
import requests


# =============================================================================
# Конфигурация из переменных окружения
# =============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def check_config():
    """Проверить наличие всех необходимых переменных окружения."""
    missing = []
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        missing.append("SUPABASE_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    
    if missing:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing)}")
        sys.exit(1)


# =============================================================================
# Работа с Supabase
# =============================================================================

def get_supabase_client():
    """Создать клиент Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def parse_date(d):
    """Безопасный парсинг даты."""
    if isinstance(d, date):
        return d
    if d is None:
        return date.today()
    
    d_str = str(d).strip()
    if 'T' in d_str:
        d_str = d_str.split('T')[0]
    if '+' in d_str[10:]:
        d_str = d_str.split('+')[0]
    if d_str.endswith('Z'):
        d_str = d_str[:-1]
    
    try:
        return date.fromisoformat(d_str)
    except ValueError:
        return date.today()


def get_events_for_reminders(target_date: date) -> List[Dict]:
    """
    Получить события, о которых нужно напомнить на указанную дату.
    Возвращает список событий с типом напоминания.
    """
    supabase = get_supabase_client()
    response = supabase.table("events").select("*").execute()
    
    if not response.data:
        return []
    
    reminders = []
    target_str = target_date.isoformat()
    
    for row in response.data:
        event = {
            "id": row["id"],
            "title": row["title"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "category": row["category"],
            "location_type": row["location_type"],
            "location_custom": row.get("location_custom"),
            "reminder_days_before_start": row.get("reminder_days_before_start", 0),
            "reminder_on_start_day": row.get("reminder_on_start_day", 1),
            "reminder_days_before_end": row.get("reminder_days_before_end", 0),
            "reminder_custom_date": row.get("reminder_custom_date"),
            "recurrence_type": row.get("recurrence_type", "none")
        }
        
        start_date = parse_date(event["start_date"])
        end_date = parse_date(event["end_date"])
        
        # 1. Напоминание в день начала
        if start_date == target_date and event.get("reminder_on_start_day", 1):
            reminders.append({
                "event": event,
                "type": "start_day",
                "message": f"🎉 Сегодня: {event['title']}"
            })
        
        # 2. За N дней до начала
        days_before = event.get("reminder_days_before_start", 0)
        if days_before > 0:
            reminder_date = start_date - timedelta(days=days_before)
            if reminder_date == target_date:
                reminders.append({
                    "event": event,
                    "type": "before_start",
                    "message": f" Через {days_before} дн.: {event['title']} ({start_date.strftime('%d.%m.%Y')})"
                })
        
        # 3. За N дней до окончания
        days_before_end = event.get("reminder_days_before_end", 0)
        if days_before_end > 0:
            reminder_date = end_date - timedelta(days=days_before_end)
            if reminder_date == target_date:
                reminders.append({
                    "event": event,
                    "type": "before_end",
                    "message": f"⚠️ До окончания {event['title']} осталось {days_before_end} дн."
                })
        
        # 4. В конкретную дату
        if event.get("reminder_custom_date"):
            custom_date = parse_date(event["reminder_custom_date"])
            if custom_date == target_date:
                reminders.append({
                    "event": event,
                    "type": "custom",
                    "message": f" Напоминание: {event['title']}"
                })
    
    # Убираем дубликаты по ID
    seen_ids = set()
    unique_reminders = []
    for r in reminders:
        if r["event"]["id"] not in seen_ids:
            seen_ids.add(r["event"]["id"])
            unique_reminders.append(r)
    
    return unique_reminders


def get_upcoming_events(days_ahead: int = 7) -> List[Dict]:
    """Получить события на ближайшие N дней (для ежедневной сводки)."""
    supabase = get_supabase_client()
    response = supabase.table("events").select("*").execute()
    
    if not response.data:
        return []
    
    today = date.today()
    end_date = today + timedelta(days=days_ahead)
    
    upcoming = []
    for row in response.data:
        start_date = parse_date(row["start_date"])
        end_date_event = parse_date(row["end_date"])
        
        if start_date <= end_date and end_date_event >= today:
            upcoming.append(row)
    
    # Сортировка по дате начала
    upcoming.sort(key=lambda x: parse_date(x["start_date"]))
    
    return upcoming[:20]  # Максимум 20 событий


# =============================================================================
# Отправка в Telegram
# =============================================================================

def send_telegram_message(message: str) -> bool:
    """Отправить сообщение в Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка отправки Telegram: {str(e)}")
        return False


def format_reminder_message(reminders: List[Dict]) -> str:
    """Сформировать сообщение с напоминаниями."""
    today = date.today().strftime("%d.%m.%Y")
    day_name = date.today().strftime("%A")
    
    # Перевод дней недели
    day_names_ru = {
        'Monday': 'Понедельник',
        'Tuesday': 'Вторник',
        'Wednesday': 'Среда',
        'Thursday': 'Четверг',
        'Friday': 'Пятница',
        'Saturday': 'Суббота',
        'Sunday': 'Воскресенье'
    }
    day_name_ru = day_names_ru.get(day_name, day_name)
    
    message = f"""
📅 <b>Напоминания на {today} ({day_name_ru})</b>

"""
    
    if not reminders:
        message += "✨ На сегодня напоминаний нет!\n"
    else:
        for i, reminder in enumerate(reminders, 1):
            message += f"{i}. {reminder['message']}\n"
            
            # Добавляем детали
            event = reminder["event"]
            location = event.get("location_custom") or event.get("location_type", "")
            if location:
                message += f"   📍 {location}\n"
            
            message += "\n"
    
    message += "\n<i>Календарь событий • Otcheti System</i>"
    
    return message


def format_daily_summary(upcoming_events: List[Dict]) -> str:
    """Сформировать ежедневную сводку."""
    today = date.today().strftime("%d.%m.%Y")
    
    message = f"""
 <b>Ежедневная сводка ({today})</b>

Всего активных событий: {len(upcoming_events)}

"""
    
    if not upcoming_events:
        message += "✨ Нет активных событий\n"
    else:
        # Группируем по датам
        events_by_date = {}
        for event in upcoming_events:
            start_date = parse_date(event["start_date"])
            date_str = start_date.strftime("%d.%m.%Y")
            if date_str not in events_by_date:
                events_by_date[date_str] = []
            events_by_date[date_str].append(event)
        
        for date_str, events in list(events_by_date.items())[:7]:  # Показываем 7 дней
            message += f"<b>📅 {date_str}:</b>\n"
            for event in events[:3]:  # Максимум 3 события на день
                title = event.get("title", "Без названия")
                category = event.get("category", "")
                message += f"  • {title}"
                if category:
                    message += f" ({category})"
                message += "\n"
            if len(events) > 3:
                message += f"  ... и ещё {len(events) - 3}\n"
            message += "\n"
    
    message += "\n<i>Календарь событий • Otcheti System</i>"
    
    return message


# =============================================================================
# Главная функция
# =============================================================================

def main():
    """Главная функция скрипта."""
    print(f"🚀 Запуск скрипта напоминаний: {datetime.now()}")
    
    # Проверяем конфигурацию
    check_config()
    
    today = date.today()
    
    # 1. Получаем напоминания на сегодня
    print(f"📅 Проверяем напоминания на {today}...")
    reminders = get_events_for_reminders(today)
    print(f"   Найдено напоминаний: {len(reminders)}")
    
    # 2. Получаем сводку на ближайшие 7 дней
    print("📋 Формируем сводку на 7 дней...")
    upcoming = get_upcoming_events(days_ahead=7)
    print(f"   Найдено активных событий: {len(upcoming)}")
    
    # 3. Отправляем напоминания (если есть)
    if reminders:
        print("📤 Отправляем напоминания...")
        reminder_message = format_reminder_message(reminders)
        success = send_telegram_message(reminder_message)
        if success:
            print("   ✅ Напоминания отправлены")
        else:
            print("   ❌ Ошибка отправки напоминаний")
    else:
        print("   ℹ️ Напоминаний на сегодня нет")
    
    # 4. Отправляем ежедневную сводку (каждый день)
    print("📤 Отправляем ежедневную сводку...")
    summary_message = format_daily_summary(upcoming)
    success = send_telegram_message(summary_message)
    if success:
        print("   ✅ Сводка отправлена")
    else:
        print("   ❌ Ошибка отправки сводки")
    
    print("✅ Скрипт завершён")


if __name__ == "__main__":
    main()
