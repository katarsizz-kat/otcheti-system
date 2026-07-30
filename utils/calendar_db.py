import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional
import config.calendar as cfg


def get_connection():
    """Получить соединение с базой данных"""
    conn = sqlite3.connect(cfg.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создать базу данных, если её ещё нет"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            category TEXT NOT NULL,
            location_type TEXT NOT NULL,
            location_custom TEXT,
            reminder_days_before_start INTEGER DEFAULT 0,
            reminder_on_start_day INTEGER DEFAULT 1,
            reminder_days_before_end INTEGER DEFAULT 0,
            reminder_custom_date DATE,
            recurrence_type TEXT DEFAULT 'none',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Если база уже была создана раньше, добавляем новое поле
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN reminder_custom_date DATE')
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Поле уже есть
    
    conn.close()


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
    """Добавить новое событие"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO events (
            title, start_date, end_date, category, location_type,
            location_custom, reminder_days_before_start, reminder_on_start_day,
            reminder_days_before_end, reminder_custom_date, recurrence_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        title, start_date, end_date, category, location_type,
        location_custom, reminder_days_before_start, reminder_on_start_day,
        reminder_days_before_end, reminder_custom_date, recurrence_type
    ))
    
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return event_id


def get_all_events() -> List[Dict]:
    """Получить все события"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events ORDER BY start_date')
    rows = cursor.fetchall()
    events = [dict(row) for row in rows]
    conn.close()
    return events


def get_event_by_id(event_id: int) -> Optional[Dict]:
    """Получить событие по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


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
    """Обновить событие"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE events SET
            title = ?, start_date = ?, end_date = ?, category = ?,
            location_type = ?, location_custom = ?,
            reminder_days_before_start = ?, reminder_on_start_day = ?,
            reminder_days_before_end = ?, reminder_custom_date = ?,
            recurrence_type = ?
        WHERE id = ?
    ''', (
        title, start_date, end_date, category, location_type,
        location_custom, reminder_days_before_start, reminder_on_start_day,
        reminder_days_before_end, reminder_custom_date, recurrence_type, event_id
    ))
    
    conn.commit()
    conn.close()


def delete_event(event_id: int):
    """Удалить событие"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()


def get_events_for_date(target_date: date) -> List[Dict]:
    """Получить события для конкретной даты"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM events
        WHERE start_date <= ? AND end_date >= ?
        ORDER BY start_date
    ''', (target_date, target_date))
    rows = cursor.fetchall()
    events = [dict(row) for row in rows]
    conn.close()
    return events


def get_events_for_date_range(start_date: date, end_date: date) -> List[Dict]:
    """Получить события в диапазоне дат"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM events
        WHERE start_date <= ? AND end_date >= ?
        ORDER BY start_date
    ''', (end_date, start_date))
    rows = cursor.fetchall()
    events = [dict(row) for row in rows]
    conn.close()
    return events


def search_events(query: str) -> List[Dict]:
    """Поиск событий по названию"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM events
        WHERE title LIKE ?
        ORDER BY start_date
    ''', (f'%{query}%',))
    rows = cursor.fetchall()
    events = [dict(row) for row in rows]
    conn.close()
    return events


def get_events_by_category(category: str) -> List[Dict]:
    """Получить события по категории"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM events
        WHERE category = ?
        ORDER BY start_date
    ''', (category,))
    rows = cursor.fetchall()
    events = [dict(row) for row in rows]
    conn.close()
    return events


def get_upcoming_reminders(target_date: date) -> List[Dict]:
    """Получить события, о которых нужно напомнить на указанную дату"""
    conn = get_connection()
    cursor = conn.cursor()
    reminders = []
    
    # 1. События, которые начинаются сегодня
    cursor.execute('''
        SELECT * FROM events
        WHERE start_date = ? AND reminder_on_start_day = 1
    ''', (target_date,))
    reminders.extend([dict(row) for row in cursor.fetchall()])
    
    # 2. За N дней до начала
    cursor.execute('''
        SELECT * FROM events
        WHERE reminder_days_before_start > 0
        AND date(start_date, '-' || reminder_days_before_start || ' days') = ?
    ''', (target_date,))
    reminders.extend([dict(row) for row in cursor.fetchall()])
    
    # 3. За N дней до конца
    cursor.execute('''
        SELECT * FROM events
        WHERE reminder_days_before_end > 0
        AND date(end_date, '-' || reminder_days_before_end || ' days') = ?
    ''', (target_date,))
    reminders.extend([dict(row) for row in cursor.fetchall()])
    
    # 4. В конкретную дату
    cursor.execute('''
        SELECT * FROM events
        WHERE reminder_custom_date = ?
    ''', (target_date,))
    reminders.extend([dict(row) for row in cursor.fetchall()])
    
    conn.close()
    
    # Убираем дубликаты
    seen_ids = set()
    unique_reminders = []
    for r in reminders:
        if r['id'] not in seen_ids:
            seen_ids.add(r['id'])
            unique_reminders.append(r)
    
    return unique_reminders


# Инициализация БД при импорте модуля
init_db()
