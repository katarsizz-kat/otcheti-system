"""Пасхалка с динозавром — версия только на Python."""
import os
import random
import streamlit as st
from config.mascots import get_random_phrase

def render_dino_footer():
    """Рендерит кнопку и логику динозавра в подвале."""
    
    if "dino_modal_open" not in st.session_state:
        st.session_state.dino_modal_open = False
    if "dino_phrase" not in st.session_state:
        st.session_state.dino_phrase = get_random_phrase()
    if "dino_click_count" not in st.session_state:
        st.session_state.dino_click_count = 0

    if st.session_state.dino_modal_open:
        _render_dino_modal()
    else:
        _render_dino_button()

def _render_dino_button():
    """Рендерит кнопку-динозавра."""
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

def _render_dino_modal():
    """Рендерит модальное окно с динозавром."""
    gif_num = random.choice([1, 2])
    gif_path = f"assets/dino{gif_num}.gif"
    
    if not os.path.exists(gif_path):
        gif_path = "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"
    
    phrase = st.session_state.dino_phrase
    
    # CSS для модалки с контрастным текстом
    st.markdown(
        """
        <style>
        .dino-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.85);
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .dino-modal {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6);
            position: relative;
        }
        .dino-gif-container {
            text-align: center;
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            margin-bottom: 20px;
        }
        .dino-gif {
            max-width: 100%;
            height: auto;
            border-radius: 10px;
        }
        .dino-phrase {
            background: #FFFFFF;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 20px;
        }
        .dino-phrase p {
            margin: 0;
            font-size: 22px;
            color: #000000 !important;
            font-weight: 700;
            line-height: 1.5;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # HTML модалки
    modal_html = f"""
    <div class="dino-overlay">
        <div class="dino-modal">
            <div class="dino-gif-container">
                <img src="{gif_path}" alt="Динозавр" class="dino-gif" />
            </div>
            <div class="dino-phrase">
                <p>{phrase}</p>
            </div>
        </div>
    </div>
    """
    
    st.markdown(modal_html, unsafe_allow_html=True)
    
    # Кнопка закрытия под модалкой
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        if st.button("✖ Закрыть", key="close_dino_btn", use_container_width=True, type="secondary"):
            st.session_state.dino_modal_open = False
            st.rerun()
    
    # Инструкция
    st.markdown(
        "<p style='text-align: center; color: #888; font-size: 14px;'>Нажмите кнопку выше или обновите страницу</p>",
        unsafe_allow_html=True
    )
