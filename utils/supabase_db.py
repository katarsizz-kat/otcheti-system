"""Модуль работы с базой данных через Supabase."""
from supabase import create_client, Client
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import streamlit as st
import calendar

def get_supabase_client() -> Client:
    """Получить клиент Supabase."""
    if 'supabase_client' not in st.session_state:
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]
        st.session_state.supabase_client = create_client(supabase_url, supabase_key)
    return st.session_state.supabase_client

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

def extract_original_id(event_id) -> int:
    """Извлечь оригинальный числовой ID из ID вхождения."""
    id_str = str(event_id)
    if "_occ_" in id_str:
        return int(id_str.split("_occ_")[0])
    return int(id_str)

def generate_recurring_events(events: List[Dict], max_date: Optional[date] = None) -> List[Dict]:
    """Генерирует вхождения повторяющихся событий."""
    if max_date is None:
        max_date = date.today() + timedelta(days=730)
    
    recurring_events = []
    
    for event in events:
        recurrence_type = str(event.get('recurrence_type', 'none')).strip().lower()
        
        # Нормализация значений
        if recurrence_type in ['none', 'не повторяется', '']:
            recurrence_type = 'none'
        elif recurrence_type in ['daily', 'ежедневно', 'every day']:
            recurrence_type = 'daily'
        elif recurrence_type in ['weekly', 'еженедельно', 'every week']:
            recurrence_type = 'weekly'
        elif recurrence_type in ['monthly', 'ежемесячно', 'every month']:
            recurrence_type = 'monthly'
        elif recurrence_type in ['yearly', 'ежегодно', 'every year', 'annual', 'annually']:
            recurrence_type = 'yearly'
        
        # Обновляем значение в словаре
        event['recurrence_type'] = recurrence_type
        
        if recurrence_type == 'none':
            recurring_events.append(event)
            continue
        
        start_date = parse_date(event['start_date'])
        end_date = parse_date(event['end_date'])
        duration = (end_date - start_date).days
        
        current_date = start_date
        occurrence_count = 0
        max_occurrences = 100
        
        while current_date <= max_date and occurrence_count < max_occurrences:
            occurrence = event.copy()
            occurrence['start_date'] = current_date.isoformat()
            occurrence['end_date'] = (current_date + timedelta(days=duration)).isoformat()
            occurrence['is_occurrence'] = True
            occurrence['occurrence_date'] = current_date.isoformat()
            occurrence['original_id'] = event['id']
            occurrence['id'] = f"{event['id']}_occ_{occurrence_count}"
            
            recurring_events.append(occurrence)
            occurrence_count += 1
            
            if recurrence_type == 'daily':
                current_date += timedelta(days=1)
            elif recurrence_type == 'weekly':
                current_date += timedelta(weeks=1)
            elif recurrence_type == 'monthly':
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
                
                last_day = calendar.monthrange(current_date.year, current_date.month)[1]
                if start_date.day > last_day:
                    current_date = current_date.replace(day=last_day)
                else:
                    current_date = current_date.replace(day=start_date.day)
            elif recurrence_type == 'yearly':
                try:
                    current_date = current_date.replace(year=current_date.year + 1)
                    if start_date.month == 2 and start_date.day == 29:
                        if not calendar.isleap(current_date.year):
                            current_date = current_date.replace(day=28)
                except ValueError:
                    break
    
    return recurring_events

def add_event(
    title: str,
    start_date: date,
    end_date: date,
    category: str,
    location_type: str,
    location_custom: Optional[str] = None,
    reminder_days_before_start: int = 0,
    reminder_on_start_day: int = 1,
    reminder_days_before_end: int = 0,
    reminder_custom_date: Optional[date] = None,
    recurrence_type: str = 'none'
) -> int:
    """Добавить новое событие."""
    supabase = get_supabase_client()
    
    # Нормализация recurrence_type перед сохранением
    recurrence_type = str(recurrence_type).strip().lower()
    if recurrence_type in ['yearly', 'ежегодно', 'every year', 'annual']:
        recurrence_type = 'yearly'
    elif recurrence_type in ['monthly', 'ежемесячно', 'every month']:
        recurrence_type = 'monthly'
    elif recurrence_type in ['weekly', 'еженедельно', 'every week']:
        recurrence_type = 'weekly'
    elif recurrence_type in ['daily', 'ежедневно', 'every day']:
        recurrence_type = 'daily'
    else:
        recurrence_type = 'none'
    
    data = {
        "title": title,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "category": category,
        "location_type": location_type,
        "location_custom": location_custom,
        "reminder_days_before_start": reminder_days_before_start,
        "reminder_on_start_day": reminder_on_start_day,
        "reminder_days_before_end": reminder_days_before_end,
        "reminder_custom_date": reminder_custom_date.isoformat() if reminder_custom_date else None,
        "recurrence_type": recurrence_type
    }
    
    response = supabase.table("events").insert(data).execute()
    return response.data[0]["id"]

def get_all_events() -> List[Dict]:
    """Получить все события с генерацией повторяющихся вхождений."""
    supabase = get_supabase_client()
    response = supabase.table("events").select("*").order("start_date").execute()
    
    events = []
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
            "recurrence_type": row.get("recurrence_type", "none"),
            "created_at": row.get("created_at"),
            "is_occurrence": False
        }
        events.append(event)
    
    events_with_occurrences = generate_recurring_events(events)
    
    return events_with_occurrences

def get_event_by_id(event_id) -> Optional[Dict]:
    """Получить событие по ID."""
    supabase = get_supabase_client()
    original_id = extract_original_id(event_id)
    response = supabase.table("events").select("*").eq("id", original_id).execute()
    
    if response.data:
        row = response.data[0]
        return {
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
            "recurrence_type": row.get("recurrence_type", "none"),
            "created_at": row.get("created_at")
        }
    return None

def update_event(
    event_id,
    title: str,
    start_date: date,
    end_date: date,
    category: str,
    location_type: str,
    location_custom: Optional[str] = None,
    reminder_days_before_start: int = 0,
    reminder_on_start_day: int = 1,
    reminder_days_before_end: int = 0,
    reminder_custom_date: Optional[date] = None,
    recurrence_type: str = 'none'
):
    """Обновить событие."""
    supabase = get_supabase_client()
    original_id = extract_original_id(event_id)
    
    # Нормализация
    recurrence_type = str(recurrence_type).strip().lower()
    if recurrence_type in ['yearly', 'ежегодно', 'every year', 'annual']:
        recurrence_type = 'yearly'
    elif recurrence_type in ['monthly', 'ежемесячно', 'every month']:
        recurrence_type = 'monthly'
    elif recurrence_type in ['weekly', 'еженедельно', 'every week']:
        recurrence_type = 'weekly'
    elif recurrence_type in ['daily', 'ежедневно', 'every day']:
        recurrence_type = 'daily'
    else:
        recurrence_type = 'none'
    
    data = {
        "title": title,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "category": category,
        "location_type": location_type,
        "location_custom": location_custom,
        "reminder_days_before_start": reminder_days_before_start,
        "reminder_on_start_day": reminder_on_start_day,
        "reminder_days_before_end": reminder_days_before_end,
        "reminder_custom_date": reminder_custom_date.isoformat() if reminder_custom_date else None,
        "recurrence_type": recurrence_type
    }
    
    supabase.table("events").update(data).eq("id", original_id).execute()

def delete_event(event_id):
    """Удалить событие."""
    supabase = get_supabase_client()
    original_id = extract_original_id(event_id)
    supabase.table("events").delete().eq("id", original_id).execute()

def get_events_for_date(target_date: date) -> List[Dict]:
    """Получить события для конкретной даты."""
    all_events = get_all_events()
    return [
        e for e in all_events 
        if parse_date(e['start_date']) <= target_date <= parse_date(e['end_date'])
    ]

def get_events_for_date_range(start_date: date, end_date: date) -> List[Dict]:
    """Получить события в диапазоне дат."""
    all_events = get_all_events()
    return [
        e for e in all_events 
        if parse_date(e['start_date']) <= end_date and parse_date(e['end_date']) >= start_date
    ]

def search_events(query: str) -> List[Dict]:
    """Поиск событий по названию."""
    all_events = get_all_events()
    return [e for e in all_events if query.lower() in e['title'].lower()]

def get_events_by_category(category: str) -> List[Dict]:
    """Получить события по категории."""
    all_events = get_all_events()
    return [e for e in all_events if e['category'] == category]

def get_upcoming_reminders(target_date: date) -> List[Dict]:
    """Получить события, о которых нужно напомнить на указанную дату."""
    all_events = get_all_events()
    reminders = []
    target_str = target_date.isoformat()
    
    for event in all_events:
        if event.get('is_occurrence', False):
            continue
        
        if event['start_date'] == target_str and event.get('reminder_on_start_day', 1):
            reminders.append(event)
            continue
        
        days_before = event.get('reminder_days_before_start', 0)
        if days_before > 0:
            reminder_date = (datetime.fromisoformat(event['start_date']) - timedelta(days=days_before)).date().isoformat()
            if reminder_date == target_str:
                reminders.append(event)
                continue
        
        days_before_end = event.get('reminder_days_before_end', 0)
        if days_before_end > 0:
            reminder_date = (datetime.fromisoformat(event['end_date']) - timedelta(days=days_before_end)).date().isoformat()
            if reminder_date == target_str:
                reminders.append(event)
                continue
        
        if event.get('reminder_custom_date') == target_str:
            reminders.append(event)
    
    seen_ids = set()
    unique_reminders = []
    for r in reminders:
        if r['id'] not in seen_ids:
            seen_ids.add(r['id'])
            unique_reminders.append(r)
    
    return unique_reminders

