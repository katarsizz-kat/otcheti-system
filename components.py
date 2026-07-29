"""Компоненты интерфейса: шапка, карточки, баннеры, кнопки, подвал, маскот."""
import os
import re
import datetime
import streamlit as st
from config.greetings import get_current_greeting
from config.holidays import get_today_holiday

# =============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# =============================================================================
def make_key(text: str) -> str:
    """Превращает текст в безопасный ключ."""
    safe = re.sub(r'[^\w]', '', text)
    safe = re.sub(r'_+', '', safe)
    return safe.lower()

# =============================================================================
# ВЕРХНЯЯ ПАНЕЛЬ (ШАПКА)
# =============================================================================
def render_app_header():
    """Полноценная верхняя панель приложения."""
    greeting_data = get_current_greeting()
    _render_header_container(
        theme=greeting_data["theme"],
        icon=greeting_data["icon"],
    )

def _render_header_container(theme: str, icon: str):
    """Контейнер верхней панели."""
    text_color = "#1B4F72" if theme == "day" else "#FFFFFF"
    html = (
        '<div style="display:flex;justify-content:space-between;'
        'align-items:center;padding:16px 24px;margin-bottom:24px;'
        'border-bottom:1px solid rgba(0,0,0,0.08);">'
        '<div style="display:flex;align-items:center;gap:12px;">'
        '<span style="font-size:28px;"></span>'
        '<span style="font-size:20px;font-weight:700;color:' + text_color + ';'
        'letter-spacing:0.5px;">Система формирования отчётов</span>'
        '</div>'
        '<div style="display:flex;align-items:center;gap:16px;">'
        '<div style="font-size:28px;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.15));">'
        + icon + '</div></div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

# =============================================================================
# ПРИВЕТСТВЕННЫЙ БЛОК
# =============================================================================
def render_welcome_block(icon: str, greeting: str, subtitle: str = ""):
    """Красивый приветственный блок."""
    st.markdown(
        f"""<div class="welcome-block fade-in">
<div class="welcome-icon">{icon}</div>
<h1 class="welcome-title">{greeting}</h1>
<p class="welcome-subtitle">{subtitle}</p>
<p class="welcome-hint">Выберите нужный отчёт</p>
</div>""",
        unsafe_allow_html=True,
    )

# =============================================================================
# ПРАЗДНИЧНЫЙ БАННЕР (КНОПКА, СТИЛИЗОВАННАЯ ПОД БАННЕР)
# =============================================================================
def render_holiday_banner(holiday: dict):
    """
    Баннер праздника.
    Реализован как кнопка, стилизованная под голубой баннер.
    При клике открывает popup с поздравлением, Дино и пасхалкой.
    """
    if not holiday:
        return
    
    # Добавляем дату в ключ для уникальности
    today = datetime.datetime.now().strftime("%m-%d")
    safe_title = make_key(f"{today}_{holiday.get('title', 'unknown')}")
    state_key = f"show_popup_{safe_title}"
    
    if state_key not in st.session_state:
        st.session_state[state_key] = False
    
    # Структура текста: эмодзи → "Сегодня праздник" → НАЗВАНИЕ → пожелание
    banner_text = (
        f"{holiday.get('emoji', '')}\n\n"
        f"Сегодня праздник\n\n"
        f"{holiday.get('title', '').upper()}\n\n"
        f"{holiday.get('message', '')}"
    )
    
    # Кнопка с увеличенным шрифтом и паддингом
    banner_clicked = st.button(
        label=banner_text,
        key=f"banner_btn_{safe_title}",
        use_container_width=True,
        type="secondary",
    )
    
    if banner_clicked:
        st.session_state[state_key] = True
    
    if st.session_state.get(state_key):
        _render_holiday_popup(holiday, safe_title, state_key)

def _render_holiday_popup(holiday: dict, safe_title: str, state_key: str):
    """Показывает поздравление, Дино и пасхалку."""
    from config.actions import execute_action
    
    # Безопасное получение полей (защита от null в JSON)
    popup = holiday.get("popup") if isinstance(holiday.get("popup"), dict) else {}
    mascot = holiday.get("mascot") if isinstance(holiday.get("mascot"), dict) else {}
    secret = holiday.get("secret") if isinstance(holiday.get("secret"), dict) else {}
    button = holiday.get("button") if isinstance(holiday.get("button"), dict) else {}
    
    # Эффект шариков при первом открытии
    if not st.session_state.get(f"balloons_shown_{safe_title}"):
        st.balloons()
        st.session_state[f"balloons_shown_{safe_title}"] = True
    
    # Popup с поздравлением (увеличенный шрифт)
    if popup.get("enabled"):
        st.markdown(
            f"""<div style="background: linear-gradient(135deg, rgba(241,196,15,0.2) 0%, rgba(230,126,34,0.2) 100%); padding: 24px; border-radius: 16px; margin: 16px 0; border: 2px solid rgba(241,196,15,0.4);">
<h3 style="margin-top: 0; color: #F1C40F; font-size: 28px;">{popup.get('title', 'Поздравляем!')}</h3>
<p style="margin-bottom: 0; font-size: 18px;">{popup.get('text', '')}</p>
</div>""",
            unsafe_allow_html=True,
        )
    
    # Дино-маскот (увеличенный шрифт)
    if mascot.get("enabled"):
        st.markdown(
            f"""<div style="background: rgba(46, 204, 113, 0.15); padding: 16px 20px; border-radius: 12px; margin: 16px 0; display: flex; align-items: center; gap: 12px; border: 1px solid rgba(46, 204, 113, 0.3);">
<span style="font-size: 36px;">🦖</span>
<p style="margin: 0; font-style: italic; font-size: 18px;">{mascot.get('text', '')}</p>
</div>""",
            unsafe_allow_html=True,
        )
    
    # Пасхалка показывается сразу (увеличенный шрифт)
    if secret.get("enabled"):
        st.markdown(
            f"""<div style="background: rgba(155, 89, 182, 0.15); padding: 16px 20px; border-radius: 12px; margin: 16px 0; border: 1px solid rgba(155, 89, 182, 0.3);">
<p style="margin: 0; font-size: 18px;"><strong>{secret.get('title', 'Пасхалка')}:</strong> {secret.get('text', '')}</p>
</div>""",
            unsafe_allow_html=True,
        )
    
    # === ОБРАБОТКА ДЕЙСТВИЙ ===
    action_key = f"action_executed_{safe_title}"
    if button.get("enabled") and button.get("action"):
        action_name = button["action"]
        # Кнопка для выполнения действия
        if st.button(
            "Выполнить действие",
            key=f"action_btn_{safe_title}",
            use_container_width=True,
            type="primary",
        ):
            result = execute_action(action_name, holiday)
            st.session_state[action_key] = result
        
        # Показываем результат действия
        if action_key in st.session_state:
            result = st.session_state[action_key]
            _render_action_result(result)
    
    # Кнопка закрытия
    st.markdown("---")
    if st.button("✖ Закрыть", key=f"close_{safe_title}", use_container_width=True):
        st.session_state[state_key] = False
        st.session_state[f"balloons_shown_{safe_title}"] = False
        if action_key in st.session_state:
            del st.session_state[action_key]
        st.rerun()

def _render_action_result(result: dict):
    """Отображает результат выполнения действия."""
    result_type = result.get("type", "message")
    if result_type == "message":
        st.success(f"**{result.get('title', '')}**: {result.get('text', '')}")
    elif result_type == "effect":
        st.info(f"**{result.get('title', '')}**: {result.get('text', '')}")
    elif result_type == "sound":
        st.warning(f"**{result.get('title', '')}**: {result.get('text', '')}\n\n{result.get('note', '')}")

# =============================================================================
# КАРТОЧКА ОТЧЁТА
# =============================================================================
def render_report_card(report: dict):
    """Карточка перехода на страницу отчёта."""
    st.markdown(
        f"""<a href="/{report['page']}" style="text-decoration:none;">
<div class="report-card fade-in">
<div class="card-icon">{report['icon']}</div>
<h3 class="card-title">{report['title']}</h3>
<p class="card-description">{report['description']}</p>
<div class="card-link">Открыть →</div>
</div>
</a>""",
        unsafe_allow_html=True,
    )

# =============================================================================
# БЛОК БЛИЖАЙШИХ ПРАЗДНИКОВ
# =============================================================================
def render_upcoming_holidays_section(upcoming_holidays: list):
    """Полная секция ближайших праздников."""
    if not upcoming_holidays:
        return
    
    st.markdown("### 🎉 Ближайшие праздники", unsafe_allow_html=True)
    cols = st.columns([2, 1])
    
    with cols[0]:
        html = '<div class="content-block fade-in"><ul style="padding-left: 20px; margin: 0; list-style-type: none;">'
        for h in upcoming_holidays:
            html += (
                f'<li style="margin: 12px 0; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.1); '
                f'display: flex; align-items: flex-start; gap: 10px;">'
                f'<span style="font-size: 18px;">{h["emoji"]}</span>'
                f'<span style="flex: 1;">{h["date"]} — {h["title"]}</span></li>'
            )
        html += '</ul></div>'
        st.markdown(html, unsafe_allow_html=True)
    
    with cols[1]:
        gif_path = os.path.join("assets", "animation.gif")
        if os.path.exists(gif_path):
            st.image(gif_path, width=250)
        else:
            st.markdown(
                '<div style="display:flex;justify-content:center;align-items:center;'
                'height:200px;background:#F8F9FA;border-radius:10px;">🎉</div>',
                unsafe_allow_html=True,
            )

# =============================================================================
# МАСКОТ (ДИНО) - УПРОЩЁННАЯ ВЕРСИЯ
# =============================================================================
def render_mascot(mascot_type: str = "dino", custom_text: str = None):
    """
    Отображает маскота (Дино) в левом нижнем углу.
    Упрощённая версия без анимаций.
    """
    if not mascot_type:
        return
    
    from config.mascots import get_mascot_emoji, get_mascot_text
    
    safe_type = make_key(mascot_type)
    emoji = get_mascot_emoji(mascot_type)
    state_key = f"mascot_show_{safe_type}"
    text_key = f"mascot_text_{safe_type}"
    
    if state_key not in st.session_state:
        st.session_state[state_key] = False
    
    if custom_text:
        st.session_state[text_key] = custom_text
    elif text_key not in st.session_state:
        st.session_state[text_key] = get_mascot_text(mascot_type)
    
    show_bubble = st.session_state.get(state_key, False)
    bubble_text = st.session_state.get(text_key, "")
    
    # Создаём контейнер для маскота
    mascot_col, _ = st.columns([1, 10])
    with mascot_col:
        # Кнопка-динозавр
        if st.button(emoji, key=f"mascot_btn_{safe_type}", use_container_width=True):
            if not custom_text:
                st.session_state[text_key] = get_mascot_text(mascot_type)
            st.session_state[state_key] = True
            st.rerun()
        
        # Облачко с текстом
        if show_bubble:
            st.markdown(
                f"""<div style="background: white; padding: 12px 16px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); margin-bottom: 10px;">
<p style="margin: 0; font-size: 14px; color: #2C3E50;">{bubble_text}</p>
</div>"""
            )
            if st.button("✖ Закрыть", key=f"mascot_close_{safe_type}", use_container_width=True):
                st.session_state[state_key] = False
                st.rerun()

# =============================================================================
# ПОДВАЛ (FOOTER) С КНОПКОЙ-ДИНОЗАВРОМ
# =============================================================================
def render_footer():
    """Подвал приложения с кнопкой-динозавром."""
    from easter_eggs.dino import render_dino_button, render_dino_modal
    
    # Кнопка-динозавр (в левом углу, перед копирайтом)
    render_dino_button()
    
    # Копирайт
    st.markdown(
        '<div style="text-align:center;padding:20px;opacity:0.7;">'
        '<p style="margin:0;font-size:14px;">© 2026 Система формирования отчётов • Версия 1.0</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    
    # Модальное окно (скрыто по умолчанию)
    render_dino_modal()
