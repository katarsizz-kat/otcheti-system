"""Главная страница приложения."""
import html
import streamlit as st
from datetime import date

# =============================================================================
# 1. НАСТРОЙКА СТРАНИЦЫ (ВСЕГДА ПЕРВАЯ КОМАНДА!)
# =============================================================================
st.set_page_config(page_title="Система отчётов", page_icon="🦖", layout="wide")

# =============================================================================
# 2. КРИТИЧЕСКИЙ CSS (МГНОВЕННОЕ ПРИМЕНЕНИЕ)
# Фон берётся из палитры Sage & Sandstone; если в URL уже есть
# ?theme=dark — красим сразу в тёмный, чтобы не было мигания.
# =============================================================================
_override = st.query_params.get("theme")
_crit_bg = "#1E2420" if _override == "dark" else "#F7F5F1"

st.markdown(
    f"""
<style>
/* Принудительно красим контейнеры Streamlit ДО загрузки apply_theme */
.stApp,
body,
.main .block-container,
[data-testid="stAppViewBlockContainer"] {{
    background-color: {_crit_bg} !important;
    background: {_crit_bg} !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# 3. ЛЁГКИЕ ИМПОРТЫ (конфиги — без БД, мигания не будет)
# =============================================================================
from config.greetings import get_current_greeting
from config.holidays import get_today_holiday, get_upcoming_holidays
from config.theme import resolve_mode
from styles import apply_theme
from components import (
    render_app_header,
    render_welcome_block,
    render_holiday_banner,
    render_upcoming_holidays_section,
    render_footer,
)

# =============================================================================
# Сброс состояния динозавра при загрузке главной страницы
# =============================================================================
if "main_page_dino_modal_open" not in st.session_state:
    st.session_state.main_page_dino_modal_open = False

# =============================================================================
# Получение данных
# =============================================================================
greeting_data = get_current_greeting()
holiday = get_today_holiday()
upcoming_holidays = get_upcoming_holidays(days=7)
holiday_effects = holiday.get("effects") if holiday and isinstance(holiday, dict) else None

# Применяем тему (база A/B + эффекты поверх, с учётом override из URL)
apply_theme(greeting_data["theme"], holiday_effects)


# =============================================================================
# ✅ ОПТИМИЗАЦИЯ: Кэширование запросов к Supabase
# =============================================================================
@st.cache_data(ttl=300)  # Кэш на 5 минут; ошибки НЕ кэшируются
def _get_upcoming_events(days_ahead: int = 30):
    """Запрос к БД (кэшируемый)."""
    import utils.supabase_db as db
    return db.get_upcoming_events(days_ahead=days_ahead)


def get_upcoming_events_safe(days_ahead=30, max_events=6):
    """Безопасное получение событий.

    Возвращает список событий либо None, если БД недоступна
    (чтобы показать состояние ошибки, а не "событий нет").
    """
    try:
        events = _get_upcoming_events(days_ahead=days_ahead)
        return (events or [])[:max_events]
    except Exception:
        return None


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


def _esc(value) -> str:
    """Экранирование строк из БД для безопасной вставки в HTML (фикс XSS)."""
    return html.escape(str(value if value is not None else ""))


upcoming_events = get_upcoming_events_safe(days_ahead=30, max_events=6)

# =============================================================================
# Рендеринг страницы
# =============================================================================
render_app_header()

subtitle = "Календарь событий, праздники и немного магии — всё здесь."
render_welcome_block(
    icon=greeting_data["icon"],
    greeting=greeting_data["greeting"],
    subtitle=subtitle,
)

# =============================================================================
# Блок "Ближайшие события"
# =============================================================================
st.markdown("### 📅 Ближайшие события", unsafe_allow_html=True)

if upcoming_events is None:
    # Состояние ошибки: БД недоступна
    st.warning("⚠️ Не удалось загрузить события календаря. Проверьте соединение с базой данных.")

elif upcoming_events:
    num_cols = min(3, len(upcoming_events))
    cols = st.columns(num_cols)

    # Семантические цвета категорий и сроков (читаемы в обеих темах)
    category_colors = {
        'Праздник': '#E74C3C',
        'Мероприятие': '#3498DB',
        'Встреча': '#9B59B6',
        'Дедлайн': '#E67E22',
        'Обучение': '#1ABC9C',
    }

    for idx, event in enumerate(upcoming_events):
        with cols[idx % num_cols]:
            event_date = parse_event_date(event.get('start_date', ''))
            days_left = (event_date - date.today()).days

            if days_left == 0:
                days_text = "Сегодня!"
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

            st.markdown(
                f"""
                <div class="content-block" style="
                    border-left: 5px solid {cat_color};
                    margin-bottom: 16px;
                    height: 100%;
                ">
                    <div style="font-size: 16px; font-weight: 700;
                        color: var(--text-primary);
                        margin-bottom: 12px; line-height: 1.3;">
                        {_esc(title)}
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 8px;
                        font-size: 14px; color: var(--text-secondary);">
                        <div>
                            {date_display} &nbsp;
                            <span style="color: {days_color}; font-weight: 600;">{days_text}</span>
                        </div>
                        {f'<div><span style="color: {cat_color}; font-weight: 500;">{_esc(category)}</span></div>' if category else ''}
                        {f'<div>📍 {_esc(location)}</div>' if location else ''}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📅 Открыть полный календарь", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Calendar.py")
else:
    # Пустое состояние
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
# Футер (с динозавром — только на главной)
# =============================================================================
render_footer(show_dino=True)