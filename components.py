"""Компоненты интерфейса: шапка, карточки, баннеры, кнопки, подвал.

v2.3 (дизайн-система Sage & Sandstone):
- Никаких хардкод-цветов: только CSS-переменные, которые выставляет styles.py.
- Все строки, вставляемые в HTML, проходят html.escape (фикс XSS).
- Блок "Оформление" в сайдбаре:
  * переключатель A/B — ссылка с полной перезагрузкой (?theme=light/dark),
    относительная query-ссылка сохраняет текущий путь страницы;
  * "↺ Авто" — кнопка: чистит URL и session_state, возвращает
    автоопределение по времени суток (Москва, UTC+3);
  * выбор переживает переходы между страницами через session_state
    (styles.py v2.2 читает override оттуда же).
- Динозавр — только на главной: render_footer(show_dino=True).
"""

import html
import os
import re
import datetime
import streamlit as st

from config.greetings import get_current_greeting
from config.theme import resolve_mode
from config.effects import is_effects_enabled, set_effects_enabled

# =============================================================================
# СЛУЖЕБНОЕ
# =============================================================================

def make_key(text: str) -> str:
    """Превращает текст в безопасный ключ."""
    safe = re.sub(r'[^\w]', '', text)
    safe = re.sub(r'_+', '', safe)
    return safe.lower()


def _esc(value) -> str:
    """Экранирование строк для безопасной вставки в HTML."""
    return html.escape(str(value if value is not None else ""))


def _get_override() -> Optional[str]:
    """Ручной выбор темы: сначала URL, затем session_state.

    session_state переживает внутренние переходы между страницами,
    где query-параметр теряется. Найденное в URL значение запоминаем.
    """
    try:
        value = st.query_params.get("theme")
    except Exception:
        value = None
    if value in ("light", "dark"):
        st.session_state["theme_override"] = value
        return value
    value = st.session_state.get("theme_override")
    return value if value in ("light", "dark") else None

# =============================================================================
# БЛОК "ОФОРМЛЕНИЕ" В САЙДБАРЕ
# =============================================================================

def render_theme_controls() -> None:
    """Блок "Оформление" внизу сайдбара.

    - Ссылка-переключатель темы с полной перезагрузкой страницы:
      Streamlit применяет базовую тему из URL при загрузке.
    - "↺ Авто" (кнопка, видна только при ручном override) — возврат
      к автоопределению по времени суток.
    - Тумблер праздничных эффектов (session_state).
    """
    greeting_theme = get_current_greeting()["theme"]
    override = _get_override()
    current_mode = resolve_mode(override, greeting_theme)

    st.sidebar.markdown("---")
    st.sidebar.caption("Оформление")

    # Ссылка-переключатель темы (полная перезагрузка)
    if current_mode == "dark":
        href, label = "?theme=light", "☀️ Светлая тема"
    else:
        href, label = "?theme=dark", "🌙 Тёмная тема"

    link_style = (
        "display:block;padding:8px 12px;margin:4px 0;border-radius:8px;"
        "background:var(--hover-bg);border:1px solid var(--card-border);"
        "color:var(--text-primary);text-decoration:none;font-weight:600;"
        "text-align:center;font-size:14px;"
    )
    st.sidebar.markdown(
        f'<a href="{href}" style="{link_style}">{label}</a>',
        unsafe_allow_html=True,
    )

    # Возврат к автоопределению (только если есть ручной override)
    if override:
        if st.sidebar.button(
            "↺ Авто-режим",
            key="theme_auto",
            use_container_width=True,
        ):
            st.session_state.pop("theme_override", None)
            if "theme" in st.query_params:
                del st.query_params["theme"]
            st.rerun()

    # Тумблер праздничных эффектов
    fx_wanted = st.sidebar.toggle(
        "🎉 Праздничные эффекты",
        value=is_effects_enabled(),
        key="fx_toggle",
    )
    if fx_wanted != is_effects_enabled():
        set_effects_enabled(fx_wanted)
        st.rerun()

# =============================================================================
# ШАПКА
# =============================================================================

def render_app_header():
    """Верхняя панель приложения (на переменных темы)."""
    greeting_data = get_current_greeting()
    _render_header_container(icon=greeting_data["icon"])


def _render_header_container(icon: str):
    """Контейнер верхней панели."""
    header_html = (
        '<div style="display:flex;justify-content:space-between;'
        'align-items:center;padding:16px 24px;margin-bottom:24px;'
        'border-bottom:1px solid var(--card-border);">'
        '<div style="display:flex;align-items:center;gap:12px;">'
        '<span style="font-size:20px;font-weight:700;'
        'color:var(--text-primary);letter-spacing:0.5px;">'
        'Система формирования отчётов</span>'
        '</div>'
        '<div style="font-size:28px;">' + _esc(icon) + '</div>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

# =============================================================================
# ПРИВЕТСТВЕННЫЙ БЛОК
# =============================================================================

def render_welcome_block(icon: str, greeting: str, subtitle: str = " "):
    """Приветственный блок главной страницы."""
    st.markdown(
        f"""<div class="welcome-block fade-in">
            <div class="welcome-icon">{_esc(icon)}</div>
            <h1 class="welcome-title">{_esc(greeting)}</h1>
            <p class="welcome-subtitle">{_esc(subtitle)}</p>
            <p class="welcome-hint">Отчёты — в меню слева ☜</p>
        </div>""",
        unsafe_allow_html=True,
    )

# =============================================================================
# ПРАЗДНИЧНЫЙ БАННЕР И ПОПАП
# =============================================================================

def render_holiday_banner(holiday: dict):
    """Кнопка-баннер сегодняшнего праздника + попап по клику."""
    if not holiday:
        return

    today = datetime.datetime.now().strftime("%m-%d")
    safe_title = make_key(f"{today} {holiday.get('title', 'unknown')}")
    state_key = f"show_popup_{safe_title}"

    if state_key not in st.session_state:
        st.session_state[state_key] = False

    banner_text = (
        f"{holiday.get('emoji', '')}\n\n"
        f"Сегодня праздник\n\n"
        f"{holiday.get('title', '').upper()}\n\n"
        f"{holiday.get('message', '')}"
    )

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
    """Попап праздника: все цвета — на CSS-переменных."""
    from config.actions import execute_action

    popup = holiday.get("popup") if isinstance(holiday.get("popup"), dict) else {}
    mascot = holiday.get("mascot") if isinstance(holiday.get("mascot"), dict) else {}
    secret = holiday.get("secret") if isinstance(holiday.get("secret"), dict) else {}
    button = holiday.get("button") if isinstance(holiday.get("button"), dict) else {}

    if not st.session_state.get(f"balloons_shown_{safe_title}"):
        st.balloons()
        st.session_state[f"balloons_shown_{safe_title}"] = True

    if popup.get("enabled"):
        st.markdown(
            f"""<div style="background: var(--warning-bg); padding: 24px;
            border-radius: 16px; margin: 16px 0; border: 1px solid var(--warning);">
            <h3 style="margin-top: 0; color: var(--warning); font-size: 28px;">
            {_esc(popup.get('title', 'Поздравляем!'))}</h3>
            <p style="margin-bottom: 0; font-size: 18px; color: var(--text-primary);">
            {_esc(popup.get('text', ''))}</p>
            </div>""",
            unsafe_allow_html=True,
        )

    if mascot.get("enabled"):
        st.markdown(
            f"""<div style="background: var(--success-bg); padding: 16px 20px;
            border-radius: 12px; margin: 16px 0; display: flex; align-items: center;
            gap: 12px; border: 1px solid var(--success);">
            <span style="font-size: 36px;">🦖</span>
            <p style="margin: 0; font-style: italic; font-size: 18px;
            color: var(--text-primary);">{_esc(mascot.get('text', ''))}</p>
            </div>""",
            unsafe_allow_html=True,
        )

    if secret.get("enabled"):
        st.markdown(
            f"""<div style="background: var(--info-bg); padding: 16px 20px;
            border-radius: 12px; margin: 16px 0; border: 1px solid var(--info);">
            <p style="margin: 0; font-size: 18px; color: var(--text-primary);">
            <strong>{_esc(secret.get('title', 'Пасхалка'))}:</strong>
            {_esc(secret.get('text', ''))}</p>
            </div>""",
            unsafe_allow_html=True,
        )

    action_key = f"action_executed_{safe_title}"
    if button.get("enabled") and button.get("action"):
        action_name = button["action"]
        if st.button(
            "Выполнить действие",
            key=f"action_btn_{safe_title}",
            use_container_width=True,
            type="primary",
        ):
            result = execute_action(action_name, holiday)
            st.session_state[action_key] = result

        if action_key in st.session_state:
            _render_action_result(st.session_state[action_key])

    st.markdown("---")
    if st.button("✖ Закрыть", key=f"close_{safe_title}", use_container_width=True):
        st.session_state[state_key] = False
        st.session_state[f"balloons_shown_{safe_title}"] = False
        if action_key in st.session_state:
            del st.session_state[action_key]
        st.rerun()


def _render_action_result(result: dict):
    """Результат праздничного действия."""
    result_type = result.get("type", "message")
    if result_type == "message":
        st.success(f"{result.get('title', '')}: {result.get('text', '')}")
    elif result_type == "effect":
        st.info(f"{result.get('title', '')}: {result.get('text', '')}")
    elif result_type == "sound":
        st.warning(f"{result.get('title', '')}: {result.get('text', '')}\n\n{result.get('note', '')}")

# =============================================================================
# КАРТОЧКА ОТЧЁТА (используется в навигации/витринах)
# =============================================================================

def render_report_card(report: dict):
    """Карточка отчёта-ссылки."""
    st.markdown(
        f"""<a href="/{report['page']}" style="text-decoration:none;">
            <div class="report-card fade-in">
                <div class="card-icon">{_esc(report['icon'])}</div>
                <h3 class="card-title">{_esc(report['title'])}</h3>
                <p class="card-description">{_esc(report['description'])}</p>
                <div class="card-link">Открыть →</div>
            </div>
        </a>""",
        unsafe_allow_html=True,
    )

# =============================================================================
# БЛИЖАЙШИЕ ПРАЗДНИКИ
# =============================================================================

def render_upcoming_holidays_section(upcoming_holidays: list):
    """Секция "Ближайшие праздники" на главной."""
    if not upcoming_holidays:
        return

    st.markdown("### 🎉 Ближайшие праздники", unsafe_allow_html=True)
    cols = st.columns([2, 1])

    with cols[0]:
        html_str = (
            '<div class="content-block fade-in">'
            '<ul style="padding-left: 20px; margin: 0; list-style-type: none;">'
        )
        for h in upcoming_holidays:
            html_str += (
                '<li style="margin: 12px 0; padding: 8px 0; '
                'border-bottom: 1px solid var(--card-border); '
                'display: flex; align-items: flex-start; gap: 10px; '
                'color: var(--text-primary);">'
                f'<span style="font-size: 18px;">{_esc(h["emoji"])}</span>'
                '<span style="flex: 1; color: var(--text-primary);">'
                f'{_esc(h["date"])} — {_esc(h["title"])}</span></li>'
            )
        html_str += '</ul></div>'
        st.markdown(html_str, unsafe_allow_html=True)

    with cols[1]:
        gif_path = os.path.join("assets", "animation.gif")
        if os.path.exists(gif_path):
            st.image(gif_path, width=250)
        else:
            st.markdown(
                '<div style="display:flex;justify-content:center;align-items:center;'
                'height:200px;background:var(--card-bg);border-radius:10px;"></div>',
                unsafe_allow_html=True,
            )

# =============================================================================
# ПОДВАЛ
# =============================================================================

def render_footer(show_dino: bool = False):
    """Подвал: логотипы, слоган, блок "Оформление" и (опционально) динозавр.

    show_dino=True — только на главной странице (app.py).
    Блок "Оформление" рендерится в сайдбаре на всех страницах с футером.
    """
    # Блок переключения тем — в сайдбар (вниз)
    render_theme_controls()

    logo_teal_path = os.path.join("assets", "logo_teal.png")
    logo_green_path = os.path.join("assets", "logo_green.png")
    logo_teal_exists = os.path.exists(logo_teal_path)
    logo_green_exists = os.path.exists(logo_green_path)

    footer_cols = st.columns([1, 4, 1])

    # Левая — бирюзовый логотип
    with footer_cols[0]:
        if logo_teal_exists:
            st.markdown('<div class="footer-logo">', unsafe_allow_html=True)
            st.image(logo_teal_path, width=60, output_format="PNG")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="text-align:center;padding:10px;">'
                '<span style="font-size:32px;opacity:0.6;">🦕</span>'
                '</div>',
                unsafe_allow_html=True,
            )

    # Центр — слоган, копирайт и (опционально) пасхалка
    with footer_cols[1]:
        st.markdown(
            '<div style="text-align:center;padding:10px;">'
            '<p style="margin:0;font-size:18px;font-style:italic;'
            'color:var(--text-secondary);opacity:0.9;">'
            '«Мы обязательно что-нибудь придумаем»'
            '</p>'
            '<p style="margin:8px 0 0 0;font-size:14px;'
            'color:var(--text-secondary);opacity:0.7;">'
            '© 2026 Система формирования отчётов • Версия 1.0'
            '</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        if show_dino:
            from easter_eggs.dino import render_dino_footer
            render_dino_footer()

    # Правая — салатовый логотип
    with footer_cols[2]:
        if logo_green_exists:
            st.markdown('<div class="footer-logo">', unsafe_allow_html=True)
            st.image(logo_green_path, width=60, output_format="PNG")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="text-align:center;padding:10px;">'
                '<span style="font-size:32px;opacity:0.6;">🦖</span>'
                '</div>',
                unsafe_allow_html=True,
            )

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "make_key",
    "render_theme_controls",
    "render_app_header",
    "render_welcome_block",
    "render_holiday_banner",
    "render_report_card",
    "render_upcoming_holidays_section",
    "render_footer",
]
