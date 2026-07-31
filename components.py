"""Компоненты интерфейса: шапка, карточки, баннеры, кнопки, подвал."""
import os
import re
import datetime
import streamlit as st
from config.greetings import get_current_greeting
from config.holidays import get_today_holiday


def make_key(text: str) -> str:
    """Превращает текст в безопасный ключ."""
    safe = re.sub(r'[^\w]', '', text)
    safe = re.sub(r'_+', '', safe)
    return safe.lower()


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


def render_holiday_banner(holiday: dict):
    if not holiday:
        return
    today = datetime.datetime.now().strftime("%m-%d")
    safe_title = make_key(f"{today}_{holiday.get('title', 'unknown')}")
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
            f"""<div style="background: linear-gradient(135deg, rgba(241,196,15,0.2) 0%, rgba(230,126,34,0.2) 100%); padding: 24px; border-radius: 16px; margin: 16px 0; border: 2px solid rgba(241,196,15,0.4);">
            <h3 style="margin-top: 0; color: #F1C40F; font-size: 28px;">{popup.get('title', 'Поздравляем!')}</h3>
            <p style="margin-bottom: 0; font-size: 18px;">{popup.get('text', '')}</p>
            </div>""",
            unsafe_allow_html=True,
        )

    if mascot.get("enabled"):
        st.markdown(
            f"""<div style="background: rgba(46, 204, 113, 0.15); padding: 16px 20px; border-radius: 12px; margin: 16px 0; display: flex; align-items: center; gap: 12px; border: 1px solid rgba(46, 204, 113, 0.3);">
            <span style="font-size: 36px;"></span>
            <p style="margin: 0; font-style: italic; font-size: 18px;">{mascot.get('text', '')}</p>
            </div>""",
            unsafe_allow_html=True,
        )

    if secret.get("enabled"):
        st.markdown(
            f"""<div style="background: rgba(155, 89, 182, 0.15); padding: 16px 20px; border-radius: 12px; margin: 16px 0; border: 1px solid rgba(155, 89, 182, 0.3);">
            <p style="margin: 0; font-size: 18px;"><strong>{secret.get('title', 'Пасхалка')}:</strong> {secret.get('text', '')}</p>
            </div>""",
            unsafe_allow_html=True,
        )

    action_key = f"action_executed_{safe_title}"
    if button.get("enabled") and button.get("action"):
        action_name = button["action"]
        if st.button("Выполнить действие", key=f"action_btn_{safe_title}", use_container_width=True, type="primary"):
            result = execute_action(action_name, holiday)
            st.session_state[action_key] = result
        if action_key in st.session_state:
            result = st.session_state[action_key]
            _render_action_result(result)

    st.markdown("---")
    if st.button("✖ Закрыть", key=f"close_{safe_title}", use_container_width=True):
        st.session_state[state_key] = False
        st.session_state[f"balloons_shown_{safe_title}"] = False
        if action_key in st.session_state:
            del st.session_state[action_key]
        st.rerun()


def _render_action_result(result: dict):
    result_type = result.get("type", "message")
    if result_type == "message":
        st.success(f"{result.get('title', '')}: {result.get('text', '')}")
    elif result_type == "effect":
        st.info(f"{result.get('title', '')}: {result.get('text', '')}")
    elif result_type == "sound":
        st.warning(f"{result.get('title', '')}: {result.get('text', '')}\n\n{result.get('note', '')}")


def render_report_card(report: dict):
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


def render_upcoming_holidays_section(upcoming_holidays: list):
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


def render_footer():
    """Подвал приложения с логотипами и слоганом (Вариант В — колонки)."""
    # Пути к логотипам
    logo_teal_path = os.path.join("assets", "logo_teal.png")
    logo_green_path = os.path.join("assets", "logo_green.png")

    # Проверяем существование файлов
    logo_teal_exists = os.path.exists(logo_teal_path)
    logo_green_exists = os.path.exists(logo_green_path)

    # CSS для полупрозрачности логотипов (только в подвале)
    st.markdown(
        """<style>
        .footer-logo img {
            opacity: 0.6;
            transition: opacity 0.3s ease;
        }
        .footer-logo img:hover {
            opacity: 0.9;
        }
        </style>""",
        unsafe_allow_html=True
    )

    # Внешние колонки: [пустое] [логотип+слоган+логотип] [пустое]
    footer_cols = st.columns([2, 6, 2])

    with footer_cols[0]:
        pass  # Пустое пространство слева

    with footer_cols[1]:
        # Внутренние колонки: [логотип] [слоган] [логотип]
        inner_cols = st.columns([1, 4, 1])

        # Левая — бирюзовый логотип
        with inner_cols[0]:
            if logo_teal_exists:
                st.markdown('<div class="footer-logo">', unsafe_allow_html=True)
                st.image(logo_teal_path, width=60, output_format="PNG")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="text-align:center;padding:10px;">'
                    '<span style="font-size:32px;opacity:0.6;">🦕</span>'
                    '</div>',
                    unsafe_allow_html=True
                )

        # Центр — слоган и копирайт
        with inner_cols[1]:
            st.markdown(
                '<div style="text-align:center;padding:10px;">'
                '<p style="margin:0;font-size:18px;font-style:italic;color:#5D6D7E;opacity:0.9;">'
                '«Мы обязательно что-нибудь придумаем»'
                '</p>'
                '<p style="margin:8px 0 0 0;font-size:14px;color:#7F8C8D;opacity:0.7;">'
                '© 2026 Система формирования отчётов • Версия 1.0'
                '</p>'
                '</div>',
                unsafe_allow_html=True
            )

        # Правая — салатовый логотип
        with inner_cols[2]:
            if logo_green_exists:
                st.markdown('<div class="footer-logo">', unsafe_allow_html=True)
                st.image(logo_green_path, width=60, output_format="PNG")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="text-align:center;padding:10px;">'
                    '<span style="font-size:32px;opacity:0.6;">🦖</span>'
                    '</div>',
                    unsafe_allow_html=True
                )

    with footer_cols[2]:
        pass  # Пустое пространство справа
