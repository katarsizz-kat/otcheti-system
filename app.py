"""Главная страница приложения."""
import streamlit as st
from datetime import date, datetime, timedelta

st.set_page_config(page_title="Система отчётов", page_icon="🦖", layout="wide")

from config.greetings import get_current_greeting
from config.reports import get_reports
from config.holidays import get_today_holiday, get_upcoming_holidays
from styles import apply_theme
from components import (
    render_app_header,
    render_welcome_block,
    render_holiday_banner,
    render_report_card,
    render_upcoming_holidays_section,
    render_footer,
)

# =============================================================================
# Получение данных
# =============================================================================

greeting_data = get_current_greeting()
holiday = get_today_holiday()
reports = get_reports()
upcoming_holidays = get_upcoming_holidays(days=7)

holiday_effects = holiday.get("effects") if holiday and isinstance(holiday, dict) else None
apply_theme(greeting_data["theme"], holiday_effects)


def get_upcoming_events_safe(days_ahead=30, max_events=6):
    """Безопасно получить ближайшие события с обработкой ошибок."""
    try:
        import utils.supabase_db as db
        events = db.get_upcoming_events(days_ahead=days_ahead)
        return events[:max_events]
    except Exception as e:
        return []


def parse_event_date(d):
    """Безопасный парсинг даты события."""
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


upcoming_events = get_upcoming_events_safe(days_ahead=30, max_events=6)

# =============================================================================
# Рендеринг страницы
# =============================================================================

render_app_header()

subtitle = "Здесь можно сформировать отчёты одним кликом."
render_welcome_block(
    icon=greeting_data["icon"],
    greeting=greeting_data["greeting"],
    subtitle=subtitle,
)

# =============================================================================
# Блок "Ближайшие события"
# =============================================================================

st.markdown("### 📅 Ближайшие события", unsafe_allow_html=True)

if upcoming_events:
    # Определяем количество колонок
    num_cols = min(3, len(upcoming_events))
    cols = st.columns(num_cols)
    
    # Цвета категорий
    category_colors = {
        'Праздник': '#E74C3C',
        'Мероприятие': '#3498DB',
        'Встреча': '#9B59B6',
        'Дедлайн': '#E67E22',
        'Обучение': '#1ABC9C',
    }
    
    for idx, event in enumerate(upcoming_events):
        with cols[idx % num_cols]:
            # Парсим дату
            event_date = parse_event_date(event.get('start_date', ''))
            days_left = (event_date - date.today()).days
            
            # Текст и цвет для дней
            if days_left == 0:
                days_text = "🔴 Сегодня!"
                days_color = "#E74C3C"
            elif days_left == 1:
                days_text = "⏰ Завтра"
                days_color = "#E67E22"
            elif days_left <= 7:
                days_text = f"⚡ Через {days_left} дн."
                days_color = "#F39C12"
            else:
                days_text = f"📆 Через {days_left} дн."
                days_color = "#27AE60"
            
            title = event.get('title', 'Без названия')
            category = event.get('category', '')
            location = event.get('location_custom') or event.get('location_type', '')
            date_display = event_date.strftime("%d.%m.%Y")
            
            cat_color = category_colors.get(category, '#95A5A6')
            
            # Карточка через контейнер
            with st.container():
                st.markdown(f"**{title}**")
                st.markdown(f"📅 {date_display}")
                st.markdown(f"<span style='color:{days_color}; font-weight:bold;'>{days_text}</span>", unsafe_allow_html=True)
                if category:
                    st.markdown(f"🏷️ {category}")
                if location:
                    st.markdown(f"📍 {location}")
                st.markdown("---")
    
    # Кнопка перехода к полному календарю
    if st.button("📅 Открыть полный календарь", use_container_width=True, type="primary"):
        st.switch_page("pages/5_Calendar.py")
else:
    st.info("ℹ️ На ближайшие 30 дней событий не запланировано")

# =============================================================================
# Праздничный баннер (если есть праздник сегодня)
# =============================================================================

if holiday:
    render_holiday_banner(holiday)

# =============================================================================
# Ближайшие праздники
# =============================================================================

if upcoming_holidays:
    render_upcoming_holidays_section(upcoming_holidays)

# =============================================================================
# Футер
# =============================================================================

render_footer()
