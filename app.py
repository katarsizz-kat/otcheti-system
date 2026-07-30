"""Главная страница приложения."""
import streamlit as st
from datetime import date, datetime
from config.greetings import get_current_greeting
from config.holidays import get_today_holiday, get_upcoming_holidays
from styles import apply_theme
from components import (
    render_app_header,
    render_welcome_block,
    render_holiday_banner,
    render_upcoming_holidays_section,
    render_footer,
)

st.set_page_config(page_title="Система отчётов", page_icon="", layout="wide")

# =============================================================================
# Получение данных
# =============================================================================

greeting_data = get_current_greeting()
holiday = get_today_holiday()
upcoming_holidays = get_upcoming_holidays(days=7)

holiday_effects = holiday.get("effects") if holiday and isinstance(holiday, dict) else None
apply_theme(greeting_data["theme"], holiday_effects)

# Получаем ближайшие события из календаря
def get_upcoming_events_safe(days_ahead=30, max_events=6):
    """Безопасно получить ближайшие события с обработкой ошибок."""
    try:
        import utils.supabase_db as db
        events = db.get_upcoming_events(days_ahead=days_ahead)
        # Ограничиваем количество событий
        return events[:max_events]
    except Exception as e:
        st.warning(f"⚠️ Не удалось загрузить события: {str(e)}")
        return []

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
    # Определяем количество колонок (2 или 3 в зависимости от количества событий)
    num_cols = min(3, len(upcoming_events))
    cols = st.columns(num_cols)
    
    for idx, event in enumerate(upcoming_events):
        with cols[idx % num_cols]:
            # Парсим дату
            event_date_str = event.get('start_date', '')
            try:
                if 'T' in event_date_str:
                    event_date_str = event_date_str.split('T')[0]
                event_date = datetime.fromisoformat(event_date_str)
                date_display = event_date.strftime("%d.%m.%Y")
                
                # Вычисляем сколько дней осталось
                days_left = (event_date.date() - date.today()).days
                if days_left == 0:
                    days_text = " Сегодня!"
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
            except Exception:
                date_display = event_date_str
                days_text = ""
                days_color = "#7F8C8D"
            
            title = event.get('title', 'Без названия')
            category = event.get('category', '')
            location = event.get('location_custom') or event.get('location_type', '')
            
            # Цвет категории
            category_colors = {
                'Праздник': '#E74C3C',
                'Мероприятие': '#3498DB',
                'Встреча': '#9B59B6',
                'Дедлайн': '#E67E22',
                'Обучение': '#1ABC9C',
            }
            cat_color = category_colors.get(category, '#95A5A6')
            
            # Карточка события
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #FFFFFF 0%, #F8F9FA 100%);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 15px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border-left: 5px solid {cat_color};
                transition: transform 0.2s ease;
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                    <div style="font-size: 16px; font-weight: bold; color: #2C3E50; flex: 1;">
                        {title}
                    </div>
                </div>
                
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 14px;">📅</span>
                        <span style="font-size: 14px; color: #7F8C8D;">{date_display}</span>
                    </div>
                    
                    {f'<div style="display: flex; align-items: center; gap: 8px;"><span style="font-size: 14px;"></span><span style="font-size: 14px; font-weight: bold; color: {days_color};">{days_text}</span></div>' if days_text else ''}
                    
                    {f'<div style="display: flex; align-items: center; gap: 8px;"><span style="font-size: 14px;">🏷️</span><span style="font-size: 13px; color: {cat_color}; font-weight: 500;">{category}</span></div>' if category else ''}
                    
                    {f'<div style="display: flex; align-items: center; gap: 8px;"><span style="font-size: 14px;">📍</span><span style="font-size: 13px; color: #7F8C8D;">{location}</span></div>' if location else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Кнопка перехода к полному календарю
    st.markdown("---")
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
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
