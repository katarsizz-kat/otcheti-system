"""Страница календаря событий."""
import streamlit as st
from datetime import datetime, date, timedelta
from streamlit_calendar import calendar
import utils.calendar_db as db
import config.calendar as cfg
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
import io

st.set_page_config(page_title="Календарь событий", page_icon="📅", layout="wide")

# =============================================================================
# Вспомогательные функции
# =============================================================================

def parse_date(d):
    """Безопасный парсинг даты из строки или объекта date."""
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d))

def get_key_by_value(d: dict, target_val, default=None):
    """Получить ключ словаря по его значению (для обратного маппинга)."""
    for k, v in d.items():
        if v == target_val:
            return k
    return default if default else list(d.keys())[0]

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
    'form_recurrence': list(cfg.RECURRENCE_TYPES.values())[0] if cfg.RECURRENCE_TYPES else 'none'
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
    
    search_query = st.text_input("Поиск по названию", key="filter_search")
    
    date_range = st.date_input(
        "Диапазон дат",
        value=(date.today(), date.today() + timedelta(days=30)),
        key="filter_date_range"
    )
    
    # Исправление: безопасная обработка выбора одной даты
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date_filter, end_date_filter = date_range
    else:
        start_date_filter = end_date_filter = date_range if isinstance(date_range, date) else date.today()
    
    st.divider()
    st.header("📤 Экспорт")
    
    if st.button("Экспорт в Excel", use_container_width=True, key="btn_export"):
        with st.spinner("Генерация Excel..."):
            events = get_cached_events()
            if events:
                wb = Workbook()
                ws = wb.active
                ws.title = "События"
                
                # Стили
                header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                spb_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
                tyumen_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                center_align = Alignment(horizontal="center", vertical="center")
                double_border = Border(
                    top=Side(style="double"), bottom=Side(style="double"),
                    left=Side(style="thin"), right=Side(style="thin")
                )
                
                # Заголовки с формулами для соответствия требованиям
                headers = ["Название", "Категория", "Локация", "Дата начала", "Дата окончания", "Статус (IF)", "Вес (SUMPRODUCT)"]
                ws.append(headers)
                
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = center_align
                
                # Сортируем события для группировки блоков СПб и Тюмень
                sorted_events = sorted(events, key=lambda x: x.get('location_type', 'all'))
                
                for idx, event in enumerate(sorted_events, start=2):
                    loc_type = event.get('location_type', 'all')
                    loc_display = event.get('location_custom') or loc_type
                    
                    # Определение цвета блока
                    fill = spb_fill if loc_type in ['spb', 'all'] else tyumen_fill
                    
                    # Формулы: IF для статуса, SUMPRODUCT для подсчета встреч в этой локации нарастающим итогом
                    status_formula = f'=IF(D{idx}<>"", "Активно", "Архив")'
                    sumproduct_formula = f'=SUMPRODUCT(--(C$2:C${idx}="{loc_display}"))'
                    
                    ws.append([
                        event['title'],
                        event['category'],
                        loc_display,
                        event['start_date'],
                        event['end_date'],
                        status_formula,
                        sumproduct_formula
                    ])
                    
                    # Применяем стили к строке
                    for cell in ws[idx]:
                        cell.fill = fill
                        cell.alignment = center_align
                
                # Итоговая строка с формулой SUM и двойной границей
                last_row = len(sorted_events) + 1
                ws.append(["ИТОГО СОБЫТИЙ", "", "", "", "", "", f'=SUM(G2:G{last_row-1})'])
                
                for cell in ws[last_row]:
                    cell.font = Font(bold=True, color="000000")
                    cell.border = double_border
                    cell.alignment = center_align
                
                # Автоширина столбцов
                for column in ws.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except Exception:
                            pass
                    ws.column_dimensions[column_letter].width = min(max_length + 2, 50)
                
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
# Получение и фильтрация событий
# =============================================================================

all_events = get_cached_events()
filtered_events = all_events if all_events else []

if selected_category:
    filtered_events = [e for e in filtered_events if e['category'] in selected_category]

if selected_location != "Все рестораны":
    location_code = cfg.LOCATIONS.get(selected_location, "all")
    if location_code == "spb":
        filtered_events = [e for e in filtered_events if e.get('location_type') in ['spb', 'all']]
    elif location_code == "tyumen":
        filtered_events = [e for e in filtered_events if e.get('location_type') in ['tyumen', 'all']]

if search_query:
    filtered_events = [e for e in filtered_events if search_query.lower() in str(e['title']).lower()]

filtered_events = [
    e for e in filtered_events
    if parse_date(e['start_date']) <= end_date_filter
    and parse_date(e['end_date']) >= start_date_filter
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
            "start": str(event['start_date']),
            "end": str(event['end_date']),
            "id": str(event['id']),
            "color": color,
            "extendedProps": {
                "category": event['category'],
                "location": event.get('location_type', 'all')
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
    }
    
    cal_value = calendar(events=calendar_events, options=calendar_options, key="main_calendar")
    
    # Обработка клика на дату
    if cal_value and cal_value.get("dateClick"):
        clicked_date = cal_value["dateClick"]["date"]
        if 'T' in clicked_date:
            clicked_date = clicked_date.split('T')[0]
        
        st.session_state.events_on_date = [
            e for e in all_events 
            if parse_date(e['start_date']) <= parse_date(clicked_date) <= parse_date(e['end_date'])
        ]
        st.session_state.show_events_on_date = clicked_date
        st.rerun()
    
    # Обработка клика на событие
    if cal_value and cal_value.get("eventClick"):
        event_id = cal_value["eventClick"]["event"]["id"]
        # Безопасное получение события (без жесткого int(), если ID строковый)
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
                        location_display = event.get('location_custom') or event.get('location_type', 'Не указано')
                        st.write(f"**Локация:** {location_display}")
                        st.write(f"**Повторяемость:** {event.get('recurrence_type', 'Нет')}")
                    
                    col_edit, col_delete = st.columns(2)
                    with col_edit:
                        if st.button(f"✏️ Редактировать", key=f"edit_{event['id']}", use_container_width=True):
                            st.session_state.selected_event = event
                            st.session_state.edit_mode = True
                            
                            # Заполнение формы с обратным маппингом
                            st.session_state.form_title = event['title']
                            st.session_state.form_start_date = parse_date(event['start_date'])
                            st.session_state.form_end_date = parse_date(event['end_date'])
                            st.session_state.form_category = event['category']
                            st.session_state.form_location = get_key_by_value(cfg.LOCATIONS, event.get('location_type', 'all'), "Все рестораны")
                            
                            if event.get('location_custom'):
                                st.session_state.form_location_custom = [r.strip() for r in event['location_custom'].split(',')]
                            else:
                                st.session_state.form_location_custom = []
                            
                            st.session_state.form_reminder_on_start = bool(event.get('reminder_on_start_day', True))
                            st.session_state.form_reminder_days_start = event.get('reminder_days_before_start', 0)
                            st.session_state.form_reminder_days_end = event.get('reminder_days_before_end', 0)
                            
                            if event.get('reminder_custom_date'):
                                st.session_state.form_use_custom_date = True
                                st.session_state.form_reminder_custom_date = parse_date(event['reminder_custom_date'])
                            else:
                                st.session_state.form_use_custom_date = False
                            
                            st.session_state.form_recurrence = get_key_by_value(cfg.RECURRENCE_TYPES, event.get('recurrence_type', 'none'), list(cfg.RECURRENCE_TYPES.values())[0])
                            st.session_state.is_indefinite = (event['start_date'] == event['end_date'])
                            st.session_state.location_type = event.get('location_type', 'all')
                            st.session_state.show_events_on_date = None
                            st.rerun()
                    
                    with col_delete:
                        if st.button(f"🗑️ Удалить", key=f"delete_{event['id']}", use_container_width=True, type="secondary"):
                            db.delete_event(event['id'])
                            clear_cache()
                            st.toast("Событие удалено", icon="✅")
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
            location_display = st.session_state.selected_event.get('location_custom') or st.session_state.selected_event.get('location_type', 'Не указано')
            st.write(f"**Локация:** {location_display}")
            st.write(f"**Повторяемость:** {st.session_state.selected_event.get('recurrence_type', 'Нет')}")
        
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
            if st.button("🗑️ Удалить", use_container_width=True, type="secondary", key="btn_delete_single"):
                db.delete_event(st.session_state.selected_event['id'])
                clear_cache()
                st.toast("Событие удалено", icon="✅")
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
            location_display = event.get('location_custom') or event.get('location_type', 'Не указано')
            end_date_display = "Однодневное" if event['start_date'] == event['end_date'] else event['end_date']
            
            df_data.append({
                "ID": event['id'],
                "Название": event['title'],
                "Дата начала": event['start_date'],
                "Дата окончания": end_date_display,
                "Категория": event['category'],
                "Локация": location_display,
                "Повторяемость": event.get('recurrence_type', 'Нет')
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
    
    # Исправление: ключи виджетов совпадают с ключами session_state для корректного сброса
    title = st.text_input("Название события", key="form_title")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", key="form_start_date")
    with col2:
        is_indefinite = st.checkbox("♾️ Однодневное событие", key="is_indefinite")
        if is_indefinite:
            end_date = start_date
            st.caption("✅ Дата окончания = дате начала")
        else:
            end_date = st.date_input("Дата окончания", key="form_end_date")
    
    category = st.selectbox(
        "Категория",
        options=list(cfg.EVENT_CATEGORIES.keys()),
        index=list(cfg.EVENT_CATEGORIES.keys()).index(st.session_state.form_category) if st.session_state.form_category in cfg.EVENT_CATEGORIES else 0,
        key="form_category"
    )
    
    location_type = st.selectbox(
        "Локация",
        options=list(cfg.LOCATIONS.keys()),
        index=list(cfg.LOCATIONS.keys()).index(st.session_state.form_location) if st.session_state.form_location in cfg.LOCATIONS else 0,
        key="form_location"
    )
    
    location_custom = None
    if location_type == "Выбрать конкретные":
        location_custom_list = st.multiselect(
            "📍 Выберите рестораны",
            options=getattr(cfg, 'ALL_RESTAURANTS', []),
            key="form_location_custom"
        )
        location_custom = ", ".join(location_custom_list) if location_custom_list else None
    else:
        # Если локация не "Выбрать конкретные", очищаем кастомную локацию во избежание противоречий
        st.session_state.form_location_custom = []
    
    st.divider()
    st.subheader("🔔 Напоминания")
    st.caption("Выберите один или несколько способов напоминания")
    
    reminder_on_start_day = st.checkbox("Напомнить в день начала события", key="form_reminder_on_start")
    reminder_days_before_start = st.number_input("За сколько дней до НАЧАЛА напомнить (0 = не напоминать)", min_value=0, max_value=90, key="form_reminder_days_start")
    reminder_days_before_end = st.number_input("За сколько дней до ОКОНЧАНИЯ напомнить (0 = не напоминать)", min_value=0, max_value=90, key="form_reminder_days_end")
    use_custom_date = st.checkbox("Напомнить в конкретную дату", key="form_use_custom_date")
    
    reminder_custom_date = None
    if use_custom_date:
        reminder_custom_date = st.date_input("Выберите дату напоминания", key="form_reminder_custom_date")
    
    recurrence_type = st.selectbox(
        "Повторяемость",
        options=list(cfg.RECURRENCE_TYPES.keys()),
        index=list(cfg.RECURRENCE_TYPES.values()).index(st.session_state.form_recurrence) if st.session_state.form_recurrence in cfg.RECURRENCE_TYPES.values() else 0,
        key="form_recurrence"
    )
    
    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 Сохранить" if not st.session_state.edit_mode else "💾 Обновить", use_container_width=True, type="primary", key="btn_save_event"):
            if not title:
                st.error("❌ Введите название события")
            elif start_date > end_date:
                st.error(f"❌ Дата начала ({start_date}) не может быть позже даты окончания ({end_date})")
            else:
                location_code = cfg.LOCATIONS.get(location_type, "all")
                if not use_custom_date:
                    reminder_custom_date = None
                
                try:
                    event_data = {
                        "title": title,
                        "start_date": start_date,
                        "end_date": end_date,
                        "category": category,
                        "location_type": location_code,
                        "location_custom": location_custom,
                        "reminder_days_before_start": reminder_days_before_start,
                        "reminder_on_start_day": 1 if reminder_on_start_day else 0,
                        "reminder_days_before_end": reminder_days_before_end,
                        "reminder_custom_date": reminder_custom_date,
                        "recurrence_type": cfg.RECURRENCE_TYPES.get(recurrence_type, 'none')
                    }
                    
                    if st.session_state.edit_mode and st.session_state.selected_event:
                        db.update_event(event_id=st.session_state.selected_event['id'], **event_data)
                        st.toast("✅ Событие обновлено!", icon="🎉")
                    else:
                        db.add_event(**event_data)
                        st.toast("✅ Событие добавлено!", icon="🎉")
                    
                    clear_cache()
                    reset_form()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка при сохранении: {str(e)}")
    
    with col_cancel:
        if st.session_state.edit_mode:
            if st.button("❌ Отменить редактирование", use_container_width=True, key="btn_cancel_edit"):
                reset_form()
                st.rerun()
