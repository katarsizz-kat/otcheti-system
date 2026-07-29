"""Пасхалка с динозавром — версия с st.dialog()."""
import os
import random
import base64
import streamlit as st
from config.mascots import get_random_phrase

@st.dialog("🦖 Динозавр приветствует тебя!")
def dino_dialog(phrase: str, gif_src: str):
    """Нативная модалка Streamlit."""
    # Гифка
    st.image(gif_src, use_container_width=True)
    
    # Фраза
    st.markdown(
        f"""
        <div style="text-align: center; font-size: 22px; font-weight: 700; color: #000000; padding: 20px 0;">
            {phrase}
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Звук через <audio> тег + CSS для маленькой кнопки закрытия
    # Примечание: автовоспроизведение звука (autoplay) может блокироваться политиками современных браузеров
    st.markdown(
        """
        <audio autoplay>
            <source src="assets/dino_roar.mp3" type="audio/mpeg">
        </audio>
        <style>
        /* Маленькая круглая кнопка закрытия ТОЛЬКО внутри диалога */
        div[data-testid="stDialog"] button[kind="secondary"] {
            background: rgba(0,0,0,0.1) !important;
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
            transition: all 0.2s ease !important;
        }
        div[data-testid="stDialog"] button[kind="secondary"]:hover {
            background: rgba(0,0,0,0.2) !important;
            transform: scale(1.1) !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Кнопка закрытия
    if st.button("✖", key="dino_close_btn", help="Закрыть"):
        st.session_state.dino_modal_open = False
        st.rerun()

def render_dino_footer():
    """Рендерит кнопку и логику динозавра в подвале."""
    
    if "dino_modal_open" not in st.session_state:
        st.session_state.dino_modal_open = False
    if "dino_phrase" not in st.session_state:
        st.session_state.dino_phrase = get_random_phrase()
    if "dino_click_count" not in st.session_state:
        st.session_state.dino_click_count = 0

    # Если модалка открыта — показываем диалог
    if st.session_state.dino_modal_open:
        gif_num = random.choice([1, 2])
        gif_path = f"assets/dino{gif_num}.gif"
        
        # Загружаем гифку как base64
        try:
            with open(gif_path, "rb") as f:
                gif_base64 = base64.b64encode(f.read()).decode()
                gif_src = f"data:image/gif;base64,{gif_base64}"
        except Exception:
            # Запасной вариант, если локальный файл не найден
            gif_src = "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"
        
        dino_dialog(st.session_state.dino_phrase, gif_src)
    else:
        # Показываем только кнопку вызова
        col1, col2 = st.columns([1, 10])
        with col1:
            if st.button("🦖", key="dino_open_btn", help="Нажми меня!"):
                st.session_state.dino_click_count += 1
                if st.session_state.dino_click_count % 5 == 0:
                    st.session_state.dino_phrase = "Кристина лучшая ❤️"
                else:
                    st.session_state.dino_phrase = get_random_phrase()
                st.session_state.dino_modal_open = True
                st.rerun()
