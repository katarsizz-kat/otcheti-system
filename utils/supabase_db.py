"""Модуль работы с базой данных через Supabase."""
from supabase import create_client, Client
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import streamlit as st
import calendar

# Горизонт планирования - 30 лет
PLANNING_YEARS = 30

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
    """Генерирует вхождения повторяющихся событий на 30 лет вперёд."""
    if max_date is None:
        max_date = date.today() + timedelta(days=365 * PLANNING_YEARS)
    
    recurring_events = []
    
    # Лимиты вхождений по типу повторяемости (для производительности)
    occurrence_limits = {
        'yearly': PLANNING_YEARS + 5,           # 35 вхождений
        'monthly': PLANNING_YEARS * 12 + 12,    # 372 вхождения
        'weekly': PLANNING_YEARS * 52 + 10,     # 1570 вхождений
        'daily': 365                            # Только 1 год для ежедневных
    }
    
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
        max_occurrences = occurrence_limits.get(recurrence_type, 100)
        
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

# ... остальной код остаётся без изменений ...
