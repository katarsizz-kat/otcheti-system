"""Страница календаря событий."""
import streamlit as st
from datetime import datetime, date, timedelta
from streamlit_calendar import calendar
import utils.calendar_db as db
import config.calendar as cfg
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
import io

st.set_page_config(page_title="Календарь событий", page_icon="", layout="wide")

# =============================================================================
# Кэширование данных
# =============================================================================

@st.cache_data(ttl=60)
def get_cached_events():
    """Получить все события с кэшированием."""
    return db.get_all_events()

@st.cache_data(ttl=60)
def get_cached_event_by_id(event_id):
    """Получить событие по ID с кэшированием."""
    return db.get_event_by_id(event_id)

def clear_cache():
    """Очистить кэш."""
    get_cached_events.clear()
    get_cached_event_by_id.clear()

# =============================================================================
# Инициализация session state
# =============================================================================

if 'selected_event' not in st.session_state:
    st.session_state.selected_event = None

if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False

if 'is_indefinite' not in st.session_state:
    st.session_state.is_indefinite = True

if 'location_type' not in st.session_state:
    st.session_state.location_type = "Все рестораны"

if 'events_on_date' not in st.session_state:
    st.session_state.events_on_date = []

if 'show_events_on_date' not in st.session_state:
    st.session_state.show_events_on_date = None

# =============================================================================
# Session state для формы
# =============================================================================

form_defaults = {
    'form_title': "",
    'form_start_date': date.today(),
    'form_end_date': date.today(),
    'form_category': list(cfg.EVENT_CATEGORIES.keys())[0],
    'form_location': "Все рестораны",
    'form_location_custom': [],
    'form_reminder_on_start': True,
    'form_reminder_days_start': 0,
    'form_reminder_days_end': 0,
    'form_use_custom_date': False,
    'form_reminder_custom_date': date.today(),
    'form_recurrence': 'none'
}

for key, value in form_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =============================================================================
# Заголовок страницы
# =============================================================================

st.title("📅 Календарь событий")

# =============================================================================
# Функция для сброса формы
# =============================================================================

def reset_form():
    """Сбросить форму к значениям по умолчанию."""
    for key, value in form_defaults.items():
        st.session_state[key] = value
    st.session_state.is_indefinite = True
    st.session_state.location_type = "Все рестораны"
    st.session_state.edit_mode = False
    st.session_state.selected_event = None

# =============================================================================
# Боковая панель с фильтрами
# =============================================================================

with st.sidebar:
    st.header("🔍 Фильтры")
    
    selected_category = st.multiselect(
        "Категория",
        options=list(cfg.EVENT_CATEGORIES.keys()),
        default=[],
        key="filter_category"
    )
    
    selected_location = st.selectbox(
        "Локация",
        options=list(cfg.LOCATIONS.keys()),
        key="filter_location"
    )
    
    search_query = st.text_input(" Поиск по названию", key="filter_search")
    
    date_range = st.date_input(
        "Диапазон дат",
        value=(date.today(), date.today() + timedelta(days=30)),
        key="filter_date_range"
    )
    
    if len(date_range) == 2:
        start_date_filter, end_date_filter = date_range
    else:
        start_date_filter = end_date_filter = date.today()
    
    st.divider()
    
    st.header("📤 Экспорт")
    
    if st.button("Экспорт в Excel", use_container_width=True, key="btn_export"):
        with st.spinner("Генерация Excel..."):
            events = get_cached_events()
            if events:
                wb = Workbook()
                ws = wb.active
                ws.title = "События"
                
                headers = ["Название", "Дата начала", "Дата окончания", "Категория", "Локация", "Повторяемость"]
                ws.append(headers)
                
                header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center")
                
                for event in events:
                    location_display = event['location_type']
                    if event.get('location_custom'):
                        location_display = event['location_custom']
                    
                    ws.append([
                        event['title'],
                        event['start_date'],
                        event['end_date'],
                        event['category'],
                        location_display,
                        event['recurrence_type']
                    ])
                
                # Автоширина столбцов
                for column in ws.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    ws.column_dimensions[column_letter].width = adjusted_width
                
                buffer = io.BytesIO()
                wb.save(buffer)
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Скачать Excel",
                    data=buffer,
                    file_name=f"calendar_events_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_download_excel"
                )
            else:
                st.warning("Нет событий для экспорта")

# =============================================================================
# Получение событий с кэшированием
# =============================================================================

all_events = get_cached_events()

# =============================================================================
# Применение фильтров
# =============================================================================

filtered_events = all_events

if selected_category:
    filtered_events = [e for e in filtered_events if e['category'] in selected_category]

if selected_location != "Все рестораны":
    location_code = cfg.LOCATIONS[selected_location]
    if location_code == "spb":
        filtered_events = [e for e in filtered_events if e['location_type'] in ['spb', 'all']]
    elif location_code == "tyumen":
        filtered_events = [e for e in filtered_events if e['location_type'] in ['tyumen', 'all']]

if search_query:
    filtered_events = [e for e in filtered_events if search_query.lower() in e['title'].lower()]

filtered_events = [
    e for e in filtered_events
    if date.fromisoformat(e['start_date']) <= end_date_filter
    and date.fromisoformat(e['end_date']) >= start_date_filter
]

# =============================================================================
# Вкладки
# =============================================================================

tab_calendar, tab_list, tab_add = st.tabs(["📅 Календарь", "📋 Список", "➕ Добавить событие"])

# =============================================================================
# Вкладка 1: Календарь
# =============================================================================

with tab_calendar:
    calendar_events = []
    for event in filtered_events:
        color = cfg.EVENT_CATEGORIES.get(event['category'], '#808080')
        calendar_events.append({
            "title": event['title'],
            "start": event['start_date'],
            "end": event['end_date'],
            "id": str(event['id']),
            "color": color,
            "extendedProps": {
                "category": event['category'],
                "location": event['location_type']
            }
        })
    
    calendar_options = {
        "editable": False,
        "selectable": True,
        "events": calendar_events,
        "locale": "ru",
        "firstDay": 1,
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth"
        },
        "initialView": "dayGridMonth",
        "dayMaxEventRows": 3,
        "eventLimit": True,
    }
    
    cal_value = calendar(events=calendar_events, options=calendar_options, key="main_calendar")
    
    # Обработка клика на дату
    if cal_value and cal_value.get("dateClick"):
        clicked_date = cal_value["dateClick"]["date"]
        # Исправляем парсинг даты (убираем время если есть)
        if 'T' in clicked_date:
            clicked_date = clicked_date.split('T')[0]
        events_on_day = [
            e for e in all_events 
            if date.fromisoformat(e['start_date']) <= date.fromisoformat(clicked_date) <= date.fromisoformat(e['end_date'])
        ]
        st.session_state.events_on_date = events_on_day
        st.session_state.show_events_on_date = clicked_date
        st.rerun()
    
    # Обработка клика на событие
    if cal_value and cal_value.get("eventClick"):
        event_id = int(cal_value["eventClick"]["event"]["id"])
        st.session_state.selected_event = get_cached_event_by_id(event_id)
        st.session_state.show_events_on_date = None
        st.rerun()
    
    # Показываем все события на выбранную дату
    if st.session_state.show_events_on_date:
        st.divider()
        st.subheader(f"📌 События на {st.session_state.show_events_on_date}")
        
        if st.session_state.events_on_date:
            for idx, event in enumerate(st.session_state.events_on_date):
                with st.expander(f"{event['title']} ({event['category']})", expanded=(idx==0)):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Категория:** {event['category']}")
                        st.write(f"**Дата начала:** {event['start_date']}")
                        if event['start_date'] == event['end_date']:
                            st.write("**Дата окончания:** Однодневное событие")
                        else:
                            st.write(f"**Дата окончания:** {event['end_date']}")
                    
                    with col2:
                        location_display = event['location_type']
                        if event.get('location_custom'):
                            location_display = event['location_custom']
                        st.write(f"**Локация:** {location_display}")
                        st.write(f"**Повторяемость:** {event['recurrence_type']}")
                    
                    # Кнопки редактирования и удаления
                    col_edit, col_delete = st.columns(2)
                    
                    with col_edit:
                        if st.button(f"✏️ Редактировать", key=f"edit_{event['id']}", use_container_width=True):
                            st.session_state.selected_event = event
                            st.session_state.edit_mode = True
                            st.session_state.form_title = event['title']
                            st.session_state.form_start_date = date.fromisoformat(event['start_date'])
                            st.session_state.form_end_date = date.fromisoformat(event['end_date'])
                            st.session_state.form_category = event['category']
                            st.session_state.form_location = event['location_type']
                            
                            if event.get('location_custom'):
                                st.session_state.form_location_custom = [r.strip() for r in event['location_custom'].split(',')]
                            else:
                                st.session_state.form_location_custom = []
                            
                            st.session_state.form_reminder_on_start = bool(event.get('reminder_on_start_day', True))
                            st.session_state.form_reminder_days_start = event.get('reminder_days_before_start', 0)
                            st.session_state.form_reminder_days_end = event.get('reminder_days_before_end', 0)
                            
                            if event.get('reminder_custom_date'):
                                st.session_state.form_use_custom_date = True
                                st.session_state.form_reminder_custom_date = date.fromisoformat(event['reminder_custom_date'])
                            else:
                                st.session_state.form_use_custom_date = False
                            
                            st.session_state.form_recurrence = event.get('recurrence_type', 'none')
                            st.session_state.is_indefinite = (event['start_date'] == event['end_date'])
                            st.session_state.location_type = event['location_type']
                            st.session_state.show_events_on_date = None
                            st.rerun()
                    
                    with col_delete:
                        if st.button(f"🗑️ Удалить", key=f"delete_{event['id']}", use_container_width=True, type="secondary"):
                            db.delete_event(event['id'])
                            clear_cache()
                            st.toast("️ Событие удалено", icon="✅")
                            st.session_state.events_on_date = [e for e in st.session_state.events_on_date if e['id'] != event['id']]
                            st.rerun()
            
            if st.button("❌ Закрыть", use_container_width=True, key="btn_close_events"):
                st.session_state.show_events_on_date = None
                st.session_state.events_on_date = []
                st.rerun()
        else:
            st.info("Нет событий на эту дату")
            if st.button("❌ Закрыть", use_container_width=True, key="btn_close_no_events"):
                st.session_state.show_events_on_date = None
                st.rerun()
    
    # Показываем одно выбранное событие
    if st.session_state.selected_event and not st.session_state.show_events_on_date:
        st.divider()
        st.subheader(f"📌 {st.session_state.selected_event['title']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Категория:** {st.session_state.selected_event['category']}")
            st.write(f"**Дата начала:** {st.session_state.selected_event['start_date']}")
            if st.session_state.selected_event['start_date'] == st.session_state.selected_event['end_date']:
                st.write("**Дата окончания:** Однодневное событие")
            else:
                st.write(f"**Дата окончания:** {st.session_state.selected_event['end_date']}")
        
        with col2:
            location_display = st.session_state.selected_event['location_type']
            if st.session_state.selected_event.get('location_custom'):
                location_display = st.session_state.selected_event['location_custom']
            st.write(f"**Локация:** {location_display}")
            st.write(f"**Повторяемость:** {st.session_state.selected_event['recurrence_type']}")
        
        st.write("**🔔 Напоминания:**")
        reminders_list = []
        ev = st.session_state.selected_event
        
        if ev.get('reminder_on_start_day'):
            reminders_list.append("• В день начала")
        if ev.get('reminder_days_before_start') and ev['reminder_days_before_start'] > 0:
            reminders_list.append(f"• За {ev['reminder_days_before_start']} дн. до начала")
        if ev.get('reminder_days_before_end') and ev['reminder_days_before_end'] > 0:
            reminders_list.append(f"• За {ev['reminder_days_before_end']} дн. до окончания")
        if ev.get('reminder_custom_date'):
            reminders_list.append(f"• В конкретную дату: {ev['reminder_custom_date']}")
        
        if reminders_list:
            for r in reminders_list:
                st.write(r)
        else:
            st.write("• Напоминания не настроены")
        
        col_edit, col_delete = st.columns(2)
        
        with col_edit:
            if st.button("✏️ Редактировать", use_container_width=True, key="btn_edit_single"):
                st.session_state.edit_mode = True
                st.rerun()
        
        with col_delete:
            if st.button("️ Удалить", use_container_width=True, type="secondary", key="btn_delete_single"):
                db.delete_event(st.session_state.selected_event['id'])
                clear_cache()
                st.toast("🗑️ Событие удалено", icon="✅")
                st.session_state.selected_event = None
                st.rerun()

# =============================================================================
# Вкладка 2: Список событий
# =============================================================================

with tab_list:
    st.subheader("📋 Список событий")
    
    if filtered_events:
        df_data = []
        for event in filtered_events:
            location_display = event['location_type']
            if event.get('location_custom'):
                location_display = event['location_custom']
            
            end_date_display = "Однодневное" if event['start_date'] == event['end_date'] else event['end_date']
            
            df_data.append({
                "ID": event['id'],
                "Название": event['title'],
                "Дата начала": event['start_date'],
                "Дата окончания": end_date_display,
                "Категория": event['category'],
                "Локация": location_display,
                "Повторяемость": event['recurrence_type']
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Нет событий для отображения")

# =============================================================================
# Вкладка 3: Добавить событие
# =============================================================================

with tab_add:
    st.subheader("➕ Добавить новое событие" if not st.session_state.edit_mode else "✏️ Редактировать событие")
    
    title = st.text_input(
        "Название события",
        value=st.session_state.form_title,
        key="input_title"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Дата начала",
            value=st.session_state.form_start_date,
            key="input_start_date"
        )
    
    with col2:
        is_indefinite = st.checkbox(
            "♾️ Однодневное событие",
            value=st.session_state.is_indefinite,
            key="checkbox_indefinite"
        )
        
        if is_indefinite:
            end_date = start_date
            st.caption("✅ Дата окончания = дате начала")
        else:
            end_date = st.date_input(
                "Дата окончания",
                value=st.session_state.form_end_date,
                key="input_end_date"
            )
    
    category = st.selectbox(
        "Категория",
        options=list(cfg.EVENT_CATEGORIES.keys()),
        index=list(cfg.EVENT_CATEGORIES.keys()).index(st.session_state.form_category) if st.session_state.form_category in cfg.EVENT_CATEGORIES.keys() else 0,
        key="select_category"
    )
    
    location_type = st.selectbox(
        "Локация",
        options=list(cfg.LOCATIONS.keys()),
        index=list(cfg.LOCATIONS.keys()).index(st.session_state.form_location) if st.session_state.form_location in cfg.LOCATIONS.keys() else 0,
        key="select_location"
    )
    
    location_custom = None
    
    if location_type == "Выбрать конкретные":
        location_custom_list = st.multiselect(
            "📍 Выберите рестораны",
            options=cfg.ALL_RESTAURANTS,
            default=st.session_state.form_location_custom,
            key="multiselect_restaurants"
        )
        location_custom = ", ".join(location_custom_list) if location_custom_list else None
    elif st.session_state.form_location_custom:
        location_custom = ", ".join(st.session_state.form_location_custom)
    
    st.divider()
    
    st.subheader("🔔 Напоминания")
    st.caption("Выберите один или несколько способов напоминания")
    
    reminder_on_start_day = st.checkbox(
        " Напомнить в день начала события",
        value=st.session_state.form_reminder_on_start,
        key="checkbox_reminder_start"
    )
    
    reminder_days_before_start = st.number_input(
        "⏰ За сколько дней до НАЧАЛА напомнить (0 = не напоминать)",
        min_value=0,
        max_value=90,
        value=st.session_state.form_reminder_days_start,
        key="number_reminder_days_start"
    )
    
    reminder_days_before_end = st.number_input(
        " За сколько дней до ОКОНЧАНИЯ напомнить (0 = не напоминать)",
        min_value=0,
        max_value=90,
        value=st.session_state.form_reminder_days_end,
        key="number_reminder_days_end"
    )
    
    use_custom_date = st.checkbox(
        "📅 Напомнить в конкретную дату",
        value=st.session_state.form_use_custom_date,
        key="checkbox_custom_date"
    )
    
    reminder_custom_date = None
    
    if use_custom_date:
        reminder_custom_date = st.date_input(
            "Выберите дату напоминания",
            value=st.session_state.form_reminder_custom_date,
            key="date_reminder_custom"
        )
    
    recurrence_type = st.selectbox(
        "Повторяемость",
        options=list(cfg.RECURRENCE_TYPES.keys()),
        index=list(cfg.RECURRENCE_TYPES.values()).index(st.session_state.form_recurrence) if st.session_state.form_recurrence in cfg.RECURRENCE_TYPES.values() else 0,
        key="select_recurrence"
    )
    
    col_save, col_cancel = st.columns(2)
    
    with col_save:
        if st.button(
            "💾 Сохранить" if not st.session_state.edit_mode else "💾 Обновить",
            use_container_width=True,
            type="primary",
            key="btn_save_event"
        ):
            if not title:
                st.error("❌ Введите название события")
            elif start_date > end_date:
                st.error(f"❌ Дата начала ({start_date}) не может быть позже даты окончания ({end_date})")
            else:
                location_code = cfg.LOCATIONS[location_type]
                
                if not use_custom_date:
                    reminder_custom_date = None
                
                try:
                    if st.session_state.edit_mode and st.session_state.selected_event:
                        db.update_event(
                            event_id=st.session_state.selected_event['id'],
                            title=title,
                            start_date=start_date,
                            end_date=end_date,
                            category=category,
                            location_type=location_code,
                            location_custom=location_custom,
                            reminder_days_before_start=reminder_days_before_start,
                            reminder_on_start_day=1 if reminder_on_start_day else 0,
                            reminder_days_before_end=reminder_days_before_end,
                            reminder_custom_date=reminder_custom_date,
                            recurrence_type=cfg.RECURRENCE_TYPES[recurrence_type]
                        )
                        clear_cache()
                        st.toast("✅ Событие обновлено!", icon="🎉")
                        reset_form()
                        st.rerun()
                    else:
                        event_id = db.add_event(
                            title=title,
                            start_date=start_date,
                            end_date=end_date,
                            category=category,
                            location_type=location_code,
                            location_custom=location_custom,
                            reminder_days_before_start=reminder_days_before_start,
                            reminder_on_start_day=1 if reminder_on_start_day else 0,
                            reminder_days_before_end=reminder_days_before_end,
                            reminder_custom_date=reminder_custom_date,
                            recurrence_type=cfg.RECURRENCE_TYPES[recurrence_type]
                        )
                        clear_cache()
                        st.toast(f"✅ Событие добавлено!", icon="🎉")
                        reset_form()
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка при сохранении: {str(e)}")
    
    with col_cancel:
        if st.session_state.edit_mode:
            if st.button("❌ Отменить редактирование", use_container_width=True, key="btn_cancel_edit"):
                reset_form()
                st.rerun()
