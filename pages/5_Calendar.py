import streamlit as st
from datetime import datetime, date, timedelta
from streamlit_calendar import calendar
import utils.calendar_db as db
import config.calendar as cfg
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
import io

st.set_page_config(page_title="Календарь событий", page_icon="📅", layout="wide")

# Инициализация session state
if 'selected_event' not in st.session_state:
    st.session_state.selected_event = None
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
if 'is_indefinite' not in st.session_state:
    st.session_state.is_indefinite = True
if 'location_type' not in st.session_state:
    st.session_state.location_type = "Все рестораны"

st.title(" Календарь событий")

# Боковая панель с фильтрами
with st.sidebar:
    st.header("🔍 Фильтры")
    
    selected_category = st.multiselect(
        "Категория",
        options=list(cfg.EVENT_CATEGORIES.keys()),
        default=[]
    )
    
    selected_location = st.selectbox(
        "Локация",
        options=list(cfg.LOCATIONS.keys())
    )
    
    search_query = st.text_input("🔎 Поиск по названию")
    
    date_range = st.date_input(
        "Диапазон дат",
        value=(date.today(), date.today() + timedelta(days=30)),
        key="date_range"
    )
    
    if len(date_range) == 2:
        start_date_filter, end_date_filter = date_range
    else:
        start_date_filter = end_date_filter = date.today()
    
    st.divider()
    
    st.header("📤 Экспорт")
    if st.button("Экспорт в Excel", use_container_width=True):
        events = db.get_all_events()
        
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
                if event['location_custom']:
                    location_display = event['location_custom']
                
                ws.append([
                    event['title'],
                    event['start_date'],
                    event['end_date'],
                    event['category'],
                    location_display,
                    event['recurrence_type']
                ])
            
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
                label=" Скачать Excel",
                data=buffer,
                file_name=f"calendar_events_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Нет событий для экспорта")

# Получение событий с учетом фильтров
all_events = db.get_all_events()
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

# Вкладки
tab_calendar, tab_list, tab_add = st.tabs([" Календарь", "📋 Список", "➕ Добавить событие"])

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
            "right": "dayGridMonth,timeGridWeek"
        },
        "initialView": "dayGridMonth",
    }
    
    cal_value = calendar(events=calendar_events, options=calendar_options, key="calendar")
    
    if cal_value and cal_value.get("eventClick"):
        event_id = int(cal_value["eventClick"]["event"]["id"])
        st.session_state.selected_event = db.get_event_by_id(event_id)
        st.rerun()
    
    if st.session_state.selected_event:
        st.divider()
        st.subheader(f" {st.session_state.selected_event['title']}")
        
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
            if st.session_state.selected_event['location_custom']:
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
            if st.button("✏️ Редактировать", use_container_width=True):
                st.session_state.edit_mode = True
                st.session_state.is_indefinite = (st.session_state.selected_event['start_date'] == st.session_state.selected_event['end_date'])
                st.session_state.location_type = st.session_state.selected_event['location_type']
                st.rerun()
        
        with col_delete:
            if st.button("🗑️ Удалить", use_container_width=True, type="secondary"):
                db.delete_event(st.session_state.selected_event['id'])
                st.session_state.selected_event = None
                st.success("Событие удалено")
                st.rerun()

with tab_list:
    st.subheader("📋 Список событий")
    
    if filtered_events:
        df_data = []
        for event in filtered_events:
            location_display = event['location_type']
            if event['location_custom']:
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

with tab_add:
    st.subheader("➕ Добавить новое событие" if not st.session_state.edit_mode else "✏️ Редактировать событие")
    
    # Сброс session state при входе на вкладку
    if st.session_state.edit_mode and st.session_state.selected_event:
        default_title = st.session_state.selected_event['title']
        default_start = date.fromisoformat(st.session_state.selected_event['start_date'])
        default_end = date.fromisoformat(st.session_state.selected_event['end_date'])
        default_category = st.session_state.selected_event['category']
        default_location = st.session_state.selected_event['location_type']
        default_location_custom = st.session_state.selected_event.get('location_custom')
        default_reminder_on_start = bool(st.session_state.selected_event.get('reminder_on_start_day', True))
        default_reminder_days_start = st.session_state.selected_event.get('reminder_days_before_start', 0)
        default_reminder_days_end = st.session_state.selected_event.get('reminder_days_before_end', 0)
        default_reminder_custom = st.session_state.selected_event.get('reminder_custom_date')
        default_recurrence = st.session_state.selected_event.get('recurrence_type', 'none')
    else:
        default_title = ""
        default_start = date.today()
        default_end = date.today()
        default_category = list(cfg.EVENT_CATEGORIES.keys())[0]
        default_location = "Все рестораны"
        default_location_custom = None
        default_reminder_on_start = True
        default_reminder_days_start = 0
        default_reminder_days_end = 0
        default_reminder_custom = None
        default_recurrence = 'none'
    
    # Основные поля
    title = st.text_input(
        "Название события",
        value=default_title
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Дата начала",
            value=default_start
        )
    
    with col2:
        # Чекбокс "Однодневное событие"
        is_indefinite = st.checkbox(
            "♾️ Однодневное событие",
            value=st.session_state.is_indefinite if st.session_state.edit_mode else True,
            key="indefinite_checkbox"
        )
        
        # Обновляем session state
        if st.session_state.is_indefinite != is_indefinite:
            st.session_state.is_indefinite = is_indefinite
            st.rerun()
        
        if is_indefinite:
            end_date = start_date
            st.caption("✅ Дата окончания = дате начала")
        else:
            end_date = st.date_input(
                "Дата окончания",
                value=default_end if not st.session_state.edit_mode else default_end
            )
    
    category = st.selectbox(
        "Категория",
        options=list(cfg.EVENT_CATEGORIES.keys()),
        index=list(cfg.EVENT_CATEGORIES.keys()).index(default_category) if default_category in cfg.EVENT_CATEGORIES.keys() else 0
    )
    
    location_type = st.selectbox(
        "Локация",
        options=list(cfg.LOCATIONS.keys()),
        index=list(cfg.LOCATIONS.keys()).index(default_location) if default_location in cfg.LOCATIONS.keys() else 0,
        key="location_select"
    )
    
    # Обновляем session state для локации
    if st.session_state.location_type != location_type:
        st.session_state.location_type = location_type
        st.rerun()
    
    location_custom = None
    if location_type == "Выбрать конкретные":
        default_restaurants = []
        if default_location_custom:
            default_restaurants = [r.strip() for r in default_location_custom.split(',')]
        
        location_custom_list = st.multiselect(
            "📍 Выберите рестораны",
            options=cfg.ALL_RESTAURANTS,
            default=default_restaurants,
            key="restaurant_select"
        )
        location_custom = ", ".join(location_custom_list) if location_custom_list else None
    elif default_location_custom:
        location_custom = default_location_custom
    
    st.divider()
    st.subheader("🔔 Напоминания")
    st.caption("Выберите один или несколько способов напоминания")
    
    reminder_on_start_day = st.checkbox(
        "📌 Напомнить в день начала события",
        value=default_reminder_on_start
    )
    
    reminder_days_before_start = st.number_input(
        "⏰ За сколько дней до НАЧАЛА напомнить (0 = не напоминать)",
        min_value=0,
        max_value=90,
        value=default_reminder_days_start
    )
    
    reminder_days_before_end = st.number_input(
        "⏰ За сколько дней до ОКОНЧАНИЯ напомнить (0 = не напоминать)",
        min_value=0,
        max_value=90,
        value=default_reminder_days_end
    )
    
    use_custom_date = st.checkbox(
        "📅 Напомнить в конкретную дату",
        value=default_reminder_custom is not None
    )
    
    reminder_custom_date = None
    if use_custom_date:
        reminder_custom_date = st.date_input(
            "Выберите дату напоминания",
            value=date.fromisoformat(default_reminder_custom) if default_reminder_custom else date.today()
        )
    
    recurrence_type = st.selectbox(
        "Повторяемость",
        options=list(cfg.RECURRENCE_TYPES.keys()),
        index=list(cfg.RECURRENCE_TYPES.values()).index(default_recurrence) if default_recurrence in cfg.RECURRENCE_TYPES.values() else 0
    )
    
    # Кнопка сохранения
    col_save, col_cancel = st.columns(2)
    
    with col_save:
        if st.button(
            "💾 Сохранить" if not st.session_state.edit_mode else "💾 Обновить",
            use_container_width=True,
            type="primary"
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
                        st.success("✅ Событие обновлено!")
                        st.session_state.edit_mode = False
                        st.session_state.selected_event = None
                        st.session_state.is_indefinite = True
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
                        st.success(f"✅ Событие добавлено! ID: {event_id}")
                        st.session_state.is_indefinite = True
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка при сохранении: {str(e)}")
    
    with col_cancel:
        if st.session_state.edit_mode:
            if st.button("❌ Отменить редактирование", use_container_width=True):
                st.session_state.edit_mode = False
                st.session_state.selected_event = None
                st.session_state.is_indefinite = True
                st.rerun()
