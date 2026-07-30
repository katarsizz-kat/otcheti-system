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

st.title("📅 Календарь событий")

# Боковая панель с фильтрами
with st.sidebar:
    st.header(" Фильтры")
    
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
                label="📥 Скачать Excel",
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
        st.subheader(f"📌 {st.session_state.selected_event['title']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Категория:** {st.session_state.selected_event['category']}")
            st.write(f"**Дата начала:** {st.session_state.selected_event['start_date']}")
            
            # Показываем "Бессрочно" если даты совпадают
            if st.session_state.selected_event['start_date'] == st.session_state.selected_event['end_date']:
                st.write("**Дата окончания:** Бессрочно (однодневное)")
            else:
                st.write(f"**Дата окончания:** {st.session_state.selected_event['end_date']}")
        
        with col2:
            location_display = st.session_state.selected_event['location_type']
            if st.session_state.selected_event['location_custom']:
                location_display = st.session_state.selected_event['location_custom']
            st.write(f"**Локация:** {location_display}")
            st.write(f"**Повторяемость:** {st.session_state.selected_event['recurrence_type']}")
        
        # Показываем настроенные напоминания
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
            
            # Показываем "Бессрочно" если даты совпадают
            end_date_display = "Бессрочно" if event['start_date'] == event['end_date'] else event['end_date']
            
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
    
    default_values = {}
    if st.session_state.edit_mode and st.session_state.selected_event:
        default_values = st.session_state.selected_event
    
    with st.form("event_form", clear_on_submit=True):
        title = st.text_input(
            "Название события",
            value=default_values.get('title', '')
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "Дата начала",
                value=date.fromisoformat(default_values['start_date']) if 'start_date' in default_values else date.today()
            )
        
        with col2:
            # Чекбокс "Бессрочное событие"
            is_indefinite = st.checkbox(
                "♾️ Бессрочное (однодневное событие)",
                value=default_values.get('start_date') == default_values.get('end_date') if default_values else False
            )
            
            if is_indefinite:
                end_date = start_date  # Для однодневных событий дата окончания = дате начала
                st.info("Дата окончания будет установлена автоматически как дата начала")
            else:
                end_date = st.date_input(
                    "Дата окончания",
                    value=date.fromisoformat(default_values['end_date']) if 'end_date' in default_values else date.today()
                )
        
        category = st.selectbox(
            "Категория",
            options=list(cfg.EVENT_CATEGORIES.keys()),
            index=list(cfg.EVENT_CATEGORIES.keys()).index(default_values['category']) if 'category' in default_values else 0
        )
        
        location_type = st.selectbox(
            "Локация",
            options=list(cfg.LOCATIONS.keys()),
            index=list(cfg.LOCATIONS.keys()).index(default_values['location_type']) if 'location_type' in default_values else 0
        )
        
        location_custom = None
        if location_type == "Выбрать конкретные":
            location_custom = st.multiselect(
                "Выберите рестораны",
                options=cfg.ALL_RESTAURANTS
            )
            location_custom = ", ".join(location_custom) if location_custom else None
        elif 'location_custom' in default_values:
            location_custom = default_values['location_custom']
        
        st.divider()
        st.subheader("🔔 Напоминания")
        st.caption("Выберите один или несколько способов напоминания")
        
        reminder_on_start_day = st.checkbox(
            "📌 Напомнить в день начала события",
            value=bool(default_values.get('reminder_on_start_day', False))
        )
        
        # Увеличено с 30 до 90 дней
        reminder_days_before_start = st.number_input(
            " За сколько дней до НАЧАЛА напомнить (0 = не напоминать)",
            min_value=0,
            max_value=90,
            value=default_values.get('reminder_days_before_start', 0) if default_values else 0
        )
        
        # Увеличено с 30 до 90 дней
        reminder_days_before_end = st.number_input(
            "⏰ За сколько дней до ОКОНЧАНИЯ напомнить (0 = не напоминать)",
            min_value=0,
            max_value=90,
            value=default_values.get('reminder_days_before_end', 0) if default_values else 0
        )
        
        use_custom_date = st.checkbox(
            "📅 Напомнить в конкретную дату",
            value=default_values.get('reminder_custom_date') is not None if default_values else False
        )
        
        reminder_custom_date = None
        if use_custom_date:
            reminder_custom_date = st.date_input(
                "Выберите дату напоминания",
                value=date.fromisoformat(default_values['reminder_custom_date']) if default_values.get('reminder_custom_date') else date.today(),
                key="custom_reminder_date"
            )
        
        recurrence_type = st.selectbox(
            "Повторяемость",
            options=list(cfg.RECURRENCE_TYPES.keys()),
            index=list(cfg.RECURRENCE_TYPES.values()).index(default_values['recurrence_type']) if 'recurrence_type' in default_values else 0
        )
        
        submitted = st.form_submit_button(
            "💾 Сохранить" if not st.session_state.edit_mode else "💾 Обновить",
            use_container_width=True,
            type="primary"
        )
        
        if submitted:
            # Отладочная информация
            st.write(f"**Отладка:**")
            st.write(f"- Название: {title}")
            st.write(f"- Дата начала: {start_date}")
            st.write(f"- Дата окончания: {end_date}")
            st.write(f"- Бессрочное: {is_indefinite}")
            
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
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка при сохранении: {str(e)}")
        
        if st.session_state.edit_mode:
            if st.button("❌ Отменить редактирование", use_container_width=True):
                st.session_state.edit_mode = False
                st.session_state.selected_event = None
                st.rerun()
