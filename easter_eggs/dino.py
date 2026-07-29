"""Пасхалка с динозавром — версия БЕЗ JavaScript."""
import os
import random
import base64
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

def _get_gif_base64(gif_path: str) -> str:
    """Читает гифку и возвращает base64 строку."""
    try:
        with open(gif_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

def _render_dino_modal():
    """Рендерит модальное окно с динозавром."""
    gif_num = random.choice([1, 2])
    gif_path = f"assets/dino{gif_num}.gif"
    
    gif_base64 = _get_gif_base64(gif_path)
    if gif_base64:
        gif_src = f"data:image/gif;base64,{gif_base64}"
    else:
        gif_src = "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"
    
    phrase = st.session_state.dino_phrase
    
    st.markdown(
        """
        <style>
        .dino-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.85);
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .dino-modal {
            background: #FFFFFF !important;
            border-radius: 20px;
            padding: 0;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6);
            overflow: hidden;
            position: relative;
            border: 4px solid #667eea;
        }
        .dino-gif-container {
            text-align: center;
            padding: 30px 20px 10px 20px;
            background: #F8F9FA;
        }
        .dino-gif {
            max-width: 100%;
            height: auto;
            border-radius: 12px;
        }
        .dino-phrase {
            background: #FFFFFF !important;
            padding: 24px;
            margin: 0;
            text-align: center;
        }
        .dino-phrase p {
            margin: 0;
            font-size: 22px;
            color: #000000 !important;
            font-weight: 700;
            line-height: 1.5;
        }
        .dino-close-area {
            margin-top: 20px;
            text-align: center;
            padding: 0 20px 20px 20px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    modal_html = f"""
    <div class="dino-overlay">
        <div class="dino-modal">
            <div class="dino-gif-container">
                <img src="{gif_src}" alt="Динозавр" class="dino-gif" />
            </div>
            <div class="dino-phrase">
                <p>{phrase}</p>
            </div>
        </div>
    </div>
    """
    
    st.markdown(modal_html, unsafe_allow_html=True)
    
    st.markdown('<div class="dino-close-area">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        if st.button("✖ Закрыть", key="dino_close_btn", width="stretch"):
            st.session_state.dino_modal_open = False
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
