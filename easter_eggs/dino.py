"""Пасхалка с динозавром — исправленная версия (не открывается автоматически).

v2.0 (дизайн-система Sage & Sandstone):
- Цвета диалога — на CSS-переменных текущей темы A/B
  (вместо хардкода #005F6B / #000000).
- st.dialog нативно закрывается по Esc и клику вне окна —
  требование доступности выполнено без JS.
- Логика сохранена полностью: ключи, счётчик кликов,
  "Кристина лучшая ❤️" каждый 5-й клик, автозвук, фолбэк-gif.
"""

import html
import random
import base64
import streamlit as st

from config.mascots import get_random_phrase


@st.cache_data
def load_gif_base64(gif_path: str) -> str:
    """Кэшированная загрузка GIF в base64."""
    try:
        with open(gif_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


@st.dialog("🦖 Динозавр приветствует тебя!")
def dino_dialog(phrase: str, gif_src: str):
    """Нативная модалка Streamlit (Esc / клик вне — закрытие)."""
    # CSS диалога — на переменных темы
    st.markdown(
        """
        <style>
        /* Заголовок диалога */
        div[data-testid="stDialog"] h3 {
            color: var(--accent-strong, #557052) !important;
            font-size: 24px !important;
            font-weight: bold !important;
            text-align: center !important;
            margin-bottom: 20px !important;
        }
        /* Маленькая круглая кнопка закрытия */
        div[data-testid="stDialog"] button[kind="secondary"] {
            background: var(--hover-bg, rgba(45,58,46,0.06)) !important;
            border: none !important;
            border-radius: 50% !important;
            width: 36px !important;
            height: 36px !important;
            min-width: 36px !important;
            padding: 0 !important;
            font-size: 20px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            margin: 10px auto 0 auto !important;
            transition: transform 0.15s ease,
                background-color 0.15s ease !important;
        }
        div[data-testid="stDialog"] button[kind="secondary"]:hover {
            background: var(--active-bg, rgba(45,58,46,0.10)) !important;
            transform: scale(1.1) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Гифка
    st.image(gif_src, use_container_width=True)

    # Фраза (экранирована)
    st.markdown(
        f"""
        <div style="text-align: center; font-size: 22px; font-weight: 700;
            color: var(--text-primary, #2D3A2E); padding: 20px 0;">
            {html.escape(str(phrase))}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Звук
    st.markdown(
        """
        <audio autoplay>
            <source src="assets/dino_roar.mp3" type="audio/mpeg">
        </audio>
        """,
        unsafe_allow_html=True,
    )

    # Кнопка закрытия
    if st.button("✖", key="dino_close_btn", help="Закрыть"):
        st.session_state.main_page_dino_modal_open = False
        st.rerun()


def render_dino_footer():
    """Рендерит кнопку динозавра в подвале (всегда видна, открывается только по клику)."""
    # Уникальные ключи для главной страницы (не конфликтуют с другими страницами)
    if "main_page_dino_modal_open" not in st.session_state:
        st.session_state.main_page_dino_modal_open = False
    if "main_page_dino_phrase" not in st.session_state:
        st.session_state.main_page_dino_phrase = get_random_phrase()
    if "main_page_dino_click_count" not in st.session_state:
        st.session_state.main_page_dino_click_count = 0

    # Кнопка вызова динозавра (ВСЕГДА видна)
    col1, col2 = st.columns([1, 10])
    with col1:
        if st.button("🦖", key="dino_open_btn", help="Нажми меня!"):
            st.session_state.main_page_dino_click_count += 1
            if st.session_state.main_page_dino_click_count % 5 == 0:
                st.session_state.main_page_dino_phrase = "Кристина лучшая ❤️"
            else:
                st.session_state.main_page_dino_phrase = get_random_phrase()
            st.session_state.main_page_dino_modal_open = True
            st.rerun()

    # Если модалка открыта — показываем диалог и сразу сбрасываем состояние
    if st.session_state.main_page_dino_modal_open:
        gif_num = random.choice([1, 2])
        gif_path = f"assets/dino{gif_num}.gif"
        gif_base64 = load_gif_base64(gif_path)
        if gif_base64:
            gif_src = f"data:image/gif;base64,{gif_base64}"
        else:
            gif_src = "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"

        # Вызываем диалог
        dino_dialog(st.session_state.main_page_dino_phrase, gif_src)

        # Сбрасываем состояние после открытия (чтобы не открывался
        # автоматически при следующем рендере)
        st.session_state.main_page_dino_modal_open = False