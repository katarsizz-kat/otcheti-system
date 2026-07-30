"""Модуль работы с базой данных через Supabase."""
from supabase import create_client, Client
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import streamlit as st

def get_supabase_client() -> Client:
    """Получить клиент Supabase."""
    if 'supabase_client' not in st.session_state:
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]
        st.session_state.supabase_client = create_client(supabase_url, supabase_key)
    return st.session_state.supabase_client

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
    """Получить все события."""
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
            "created_at": row.get("created_at")
        }
        events.append(event)
    
    return events

def get_event_by_id(event_id: int) -> Optional[Dict]:
    """Получить событие по ID."""
    supabase = get_supabase_client()
    response = supabase.table("events").select("*").eq("id", event_id).execute()
    
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
    event_id: int,
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
    
    supabase.table("events").update(data).eq("id", event_id).execute()

def delete_event(event_id: int):
    """Удалить событие."""
    supabase = get_supabase_client()
    supabase.table("events").delete().eq("id", event_id).execute()

def get_events_for_date(target_date: date) -> List[Dict]:
    """Получить события для конкретной даты."""
    all_events = get_all_events()
    return [
        e for e in all_events 
        if e['start_date'] <= target_date.isoformat() <= e['end_date']
    ]

def get_events_for_date_range(start_date: date, end_date: date) -> List[Dict]:
    """Получить события в диапазоне дат."""
    all_events = get_all_events()
    return [
        e for e in all_events 
        if e['start_date'] <= end_date.isoformat() and e['end_date'] >= start_date.isoformat()
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
