"""Страница календаря событий."""
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from streamlit_calendar import calendar
import warnings
warnings.filterwarnings('ignore')

# ВАЖНО: st.set_page_config должен быть ПЕРВЫМ вызовом!
st.set_page_config(page_title="📅 Календарь", page_icon="📅", layout="wide")

from styles import apply_subtle_theme
from config.greetings import get_current_greeting
from config.holidays import get_today_holiday
import config.calendar_config as cfg

# ==========================================================
# ПРИМЕНЯЕМ ПРИГЛУШЁННУЮ ТЕМУ
# ==========================================================
greeting_data = get_current_greeting()
holiday = get_today_holiday()
holiday_effects = holiday.get("effects") if holiday and isinstance(holiday, dict) else None
apply_subtle_theme(greeting_data["theme"], holiday_effects)

# ==========================================================
# ОСВЕТЛЕНИЕ ФОНА + СТИЛИ
# ==========================================================
st.markdown("""
<style>
/* Полупрозрачный белый слой поверх фона (усиленное осветление) */
.stApp::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(255, 255, 255, 0.5);
    z-index: 0;
    pointer-events: none;
}

/* ===== ВКЛАДКИ (TABS) ===== */
div[data-testid="stTabs"] {
    margin-bottom: 24px !important;
}

div[data-testid="stTabs"] button[kind="secondary"] {
    background: rgba(255, 255, 255, 0.6) !important;
    color: #2C3E50 !important;
    border: 2px solid rgba(0, 95, 107, 0.3) !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    margin-right: 8px !important;
}

div[data-testid="stTabs"] button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, 0.9) !important;
    border-color: #005F6B !important;
    transform: translateY(-2px) !important;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    background: #005F6B !important;
    color: #FFFFFF !important;
    border-color: #005F6B !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.2) !important;
}

/* ===== ТАБЛИЦЫ ===== */
.stDataFrame {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 2px solid rgba(0, 95, 107, 0.2) !important;
}

/* ===== ФОРМЫ И ПОЛЯ ВВОДА ===== */
input[type="text"], input[type="date"], textarea, select {
    border: 2px solid rgba(0, 95, 107, 0.3) !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    font-size: 14px !important;
    background-color: rgba(255, 255, 255, 0.95) !important;
}

input[type="text"]:focus, input[type="date"]:focus, textarea:focus, select:focus {
    border-color: #005F6B !important;
    box-shadow: 0 0 8px rgba(0, 95, 107, 0.3) !important;
    outline: none !important;
}

/* ===== SIDEBAR (цветной, как на kr reports) ===== */
section[data-testid="stSidebar"] {
    background: var(--bg-sidebar) !important;
    border-right: 1px solid var(--card-border) !important;
    opacity: 0.95 !important;
}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] button {
    color: var(--text-primary) !important;
    font-size: 15px !important;
}

/* ===== РАЗДЕЛИТЕЛИ ===== */
hr {
    border: none !important;
    border-top: 2px solid rgba(0, 95, 107, 0.2) !important;
    margin: 24px 0 !important;
}

/* ===== SUCCESS/INFO/WARNING/ERROR ===== */
.stSuccess {
    background: rgba(39, 174, 96, 0.15) !important;
    border: 2px solid rgba(39, 174, 96, 0.4) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}

.stInfo {
    background: rgba(52, 152, 219, 0.15) !important;
    border: 2px solid rgba(52, 152, 219, 0.4) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}

.stWarning {
    background: rgba(241, 196, 15, 0.15) !important;
    border: 2px solid rgba(241, 196, 15, 0.4) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}

.stError {
    background: rgba(231, 76, 60, 0.15) !important;
    border: 2px solid rgba(231, 76, 60, 0.4) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================================
def init_db():
    """Инициализация базы данных."""
    conn = sqlite3.connect(cfg.DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  start_date DATE NOT NULL,
                  end_date DATE NOT NULL,
                  category TEXT NOT NULL,
                  location_type TEXT DEFAULT 'all',
                  description TEXT)''')
    conn.commit()
    conn.close()

def get_all_events():
    """Получить все события из БД."""
    conn = sqlite3.connect(cfg.DB_PATH)
    df = pd.read_sql_query("SELECT * FROM events ORDER BY start_date", conn)
    conn.close()
    return df

def add_event(title, start_date, end_date, category, location_type, description=""):
    """Добавить событие в БД."""
    conn = sqlite3.connect(cfg.DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO events (title, start_date, end_date, category, location_type, description) VALUES (?, ?, ?, ?, ?, ?)",
              (title, start_date, end_date, category, location_type, description))
    conn.commit()
    conn.close()

def delete_event(event_id):
    """Удалить событие по ID."""
    conn = sqlite3.connect(cfg.DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

def greeting_by_time():
    """Возвращает приветствие по времени суток."""
    hour = datetime.now().hour
    if 5 <= hour < 12: return "🌅 Доброе утро!"
    if 12 <= hour < 18: return " Добрый день!"
    if 18 <= hour < 23: return "🌙 Добрый вечер!"
    return "🌜 Доброй ночи!"

# ==========================================================
# ИНИЦИАЛИЗАЦИЯ
# ==========================================================
init_db()

# ==========================================================
# ИНТЕРФЕЙС
# ==========================================================
st.markdown(f"""
<div class="header-block">
    <h1> Календарь событий</h1>
    <p>{greeting_by_time()}</p>
    <p style="margin-top:10px; margin-bottom:0; font-size:16px;">Управление событиями и напоминаниями</p>
</div>
""", unsafe_allow_html=True)

# ── ВКЛАДКИ ──
tab_calendar, tab_list, tab_add = st.tabs([
    "📅 Календарь", " Список событий", "➕ Добавить событие"])

# =============================================
# ВКЛАДКА 1: КАЛЕНДАРЬ
# =============================================
with tab_calendar:
    # Получаем все события
    all_events = get_all_events()
    
    # Фильтры (в основной странице, под календарем)
    st.markdown("---")
    st.markdown("### 🔍 Фильтры")
    
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        st.markdown("#### 📂 Категория")
        available_categories = all_events['category'].unique().tolist() if not all_events.empty else []
        selected_categories = st.multiselect(
            "Категория:",
            options=available_categories,
            default=available_categories,
            key="cal_categories"
        )
    
    with col_filter2:
        st.markdown("#### 📍 Локация")
        location_filter = st.selectbox(
            "Локация:",
            options=["Все", "СПб", "Тюмень", "Онлайн"],
            key="cal_location"
        )
    
    with col_filter3:
        st.markdown("#### 🔎 Поиск")
        search_query = st.text_input(
            "Поиск по названию:",
            key="cal_search"
        )
    
    # Применяем фильтры
    filtered_events = all_events.copy()
    if selected_categories:
        filtered_events = filtered_events[filtered_events['category'].isin(selected_categories)]
    if location_filter != "Все":
        filtered_events = filtered_events[filtered_events['location_type'] == location_filter.lower()]
    if search_query:
        filtered_events = filtered_events[filtered_events['title'].str.contains(search_query, case=False, na=False)]
    
    # Отображаем календарь
    calendar_events = []
    for _, event in filtered_events.iterrows():
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
        "selectable": False,
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
    
    calendar(events=calendar_events, options=calendar_options, key="main_calendar")
    st.info("️ Для управления событиями перейдите во вкладку **📋 Список**")

# =============================================
# ВКЛАДКА 2: СПИСОК СОБЫТИЙ
# =============================================
with tab_list:
    st.subheader(" Список всех событий")
    
    all_events = get_all_events()
    
    if all_events.empty:
        st.info("📭 Событий пока нет. Добавьте первое событие во вкладке ** Добавить событие**.")
    else:
        # Фильтры для списка
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            cat_filter = st.multiselect(
                "Фильтр по категории:",
                options=all_events['category'].unique().tolist(),
                default=all_events['category'].unique().tolist(),
                key="list_categories"
            )
        with col_f2:
            loc_filter = st.selectbox(
                "Фильтр по локации:",
                options=["Все", "СПб", "Тюмень", "Онлайн"],
                key="list_location"
            )
        
        # Применяем фильтры
        filtered = all_events.copy()
        if cat_filter:
            filtered = filtered[filtered['category'].isin(cat_filter)]
        if loc_filter != "Все":
            filtered = filtered[filtered['location_type'] == loc_filter.lower()]
        
        # Отображаем таблицу
        st.dataframe(
            filtered[['title', 'start_date', 'end_date', 'category', 'location_type']],
            use_container_width=True,
            hide_index=True
        )
        
        # Удаление события
        st.markdown("---")
        st.markdown("### 🗑 Удалить событие")
        event_to_delete = st.selectbox(
            "Выберите событие для удаления:",
            options=filtered['id'].tolist(),
            format_func=lambda x: f"{filtered[filtered['id']==x]['title'].values[0]} ({filtered[filtered['id']==x]['start_date'].values[0]})",
            key="delete_event"
        )
        
        if st.button("🗑 Удалить событие", type="primary"):
            delete_event(event_to_delete)
            st.success("✅ Событие удалено!")
            st.rerun()

# =============================================
# ВКЛАДКА 3: ДОБАВИТЬ СОБЫТИЕ
# =============================================
with tab_add:
    st.subheader(" Добавить новое событие")
    
    with st.form("add_event_form"):
        title = st.text_input("Название события:", key="event_title")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Дата начала:", key="event_start")
        with col2:
            end_date = st.date_input("Дата окончания:", key="event_end")
        
        category = st.selectbox(
            "Категория:",
            options=list(cfg.EVENT_CATEGORIES.keys()),
            key="event_category"
        )
        
        location_type = st.selectbox(
            "Локация:",
            options=["all", "СПб", "Тюмень", "Онлайн"],
            key="event_location"
        )
        
        description = st.text_area("Описание (необязательно):", key="event_description")
        
        submitted = st.form_submit_button("💾 Сохранить событие", type="primary")
        
        if submitted:
            if title and start_date and end_date:
                if start_date > end_date:
                    st.error("❌ Дата начала не может быть позже даты окончания!")
                else:
                    add_event(title, start_date, end_date, category, location_type, description)
                    st.success("✅ Событие добавлено!")
                    st.rerun()
            else:
                st.error("❌ Заполните обязательные поля: название и даты!")
