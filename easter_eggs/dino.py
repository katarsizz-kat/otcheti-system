"""Пасхалка с динозавром — версия с CSS-модалкой (не блокирует шарики)."""
import os
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


def render_dino_footer():
    """Рендерит кнопку и логику динозавра в подвале."""
    # Инициализация session_state
    if "dino_modal_open" not in st.session_state:
        st.session_state.dino_modal_open = False
    if "dino_phrase" not in st.session_state:
        st.session_state.dino_phrase = get_random_phrase()
    if "dino_click_count" not in st.session_state:
        st.session_state.dino_click_count = 0

    # CSS для модалки
    st.markdown(
        """<style>
        .dino-modal-overlay {
            display: none;
            position: fixed;
            z-index: 10000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(4px);
            animation: fadeIn 0.3s ease-out;
        }
        .dino-modal-overlay.show {
            display: block;
        }
        .dino-modal-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 8% auto;
            padding: 0;
            border-radius: 20px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6);
            position: relative;
            animation: scaleIn 0.4s ease-out;
        }
        .dino-modal-close {
            position: absolute;
            right: 20px;
            top: 15px;
            color: white;
            font-size: 36px;
            font-weight: bold;
            cursor: pointer;
            z-index: 10;
            transition: all 0.3s ease;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: rgba(255,255,255,0.1);
            border: none;
        }
        .dino-modal-close:hover {
            color: #FFD700;
            transform: scale(1.2);
            background: rgba(255,255,255,0.2);
        }
        .dino-gif-container {
            text-align: center;
            padding: 30px 20px 20px 20px;
        }
        .dino-gif {
            max-width: 100%;
            height: auto;
            border-radius: 15px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        }
        .dino-phrase {
            background: rgba(255, 255, 255, 0.95);
            padding: 24px;
            margin: 0 20px 20px 20px;
            border-radius: 12px;
            text-align: center;
        }
        .dino-phrase p {
            margin: 0;
            font-size: 20px;
            color: #2C3E50;
            font-weight: 600;
            line-height: 1.6;
        }
        .dino-footer-btn {
            background: transparent !important;
            border: none !important;
            font-size: 32px;
            cursor: pointer;
            padding: 8px 12px;
            transition: all 0.3s ease;
            border-radius: 8px;
            line-height: 1;
        }
        .dino-footer-btn:hover {
            transform: scale(1.2) rotate(-10deg);
            background: rgba(255,255,255,0.1) !important;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes scaleIn {
            from { opacity: 0; transform: scale(0.8); }
            to { opacity: 1; transform: scale(1); }
        }
        </style>""",
        unsafe_allow_html=True
    )

    # Если модалка открыта — показываем её
    if st.session_state.dino_modal_open:
        # Загружаем GIF
        gif_num = random.choice([1, 2])
        gif_path = f"assets/dino{gif_num}.gif"
        gif_base64 = load_gif_base64(gif_path)
        
        if gif_base64:
            gif_src = f"data:image/gif;base64,{gif_base64}"
        else:
            gif_src = "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"
        
        # HTML модалки
        modal_html = f"""
        <div class="dino-modal-overlay show" id="dinoModal">
            <div class="dino-modal-content">
                <button class="dino-modal-close" onclick="document.getElementById('dinoModal').classList.remove('show')">✖</button>
                <div class="dino-gif-container">
                    <img src="{gif_src}" alt="Dino" class="dino-gif">
                </div>
                <div class="dino-phrase">
                    <p>{st.session_state.dino_phrase}</p>
                </div>
            </div>
        </div>
        <audio autoplay>
            <source src="assets/dino_roar.mp3" type="audio/mpeg">
        </audio>
        """
        st.markdown(modal_html, unsafe_allow_html=True)
        
        # Кнопка закрытия через Streamlit (для надёжности)
        if st.button("✖ Закрыть", key="dino_close_btn", help="Закрыть"):
            st.session_state.dino_modal_open = False
            st.rerun()
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
