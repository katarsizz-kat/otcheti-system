"""Пасхалка с динозавром — версия без JavaScript."""
import os
import random
import streamlit as st
from config.mascots import get_random_phrase

def render_dino_footer():
    """Рендерит кнопку и логику динозавра в подвале."""
    
    # Инициализация состояния
    if "dino_modal_open" not in st.session_state:
        st.session_state.dino_modal_open = False
    if "dino_phrase" not in st.session_state:
        st.session_state.dino_phrase = get_random_phrase()
    if "dino_click_count" not in st.session_state:
        st.session_state.dino_click_count = 0

    # Если модалка открыта — показываем её
    if st.session_state.dino_modal_open:
        _render_dino_modal()
    else:
        # Показываем только кнопку
        _render_dino_button()

def _render_dino_button():
    """Рендерит кнопку-динозавра (прозрачную, без фона)."""
    # Создаём колонку для кнопки (левая часть подвала)
    dino_col, _ = st.columns([1, 10])
    
    with dino_col:
        if st.button("🦖", key="dino_emoji_btn", help="Нажми меня!", use_container_width=False):
            st.session_state.dino_click_count += 1
            
            # Каждое пятое нажатие — специальная фраза для Кристины
            if st.session_state.dino_click_count % 5 == 0:
                st.session_state.dino_phrase = "Кристина лучшая ❤️"
            else:
                st.session_state.dino_phrase = get_random_phrase()
            
            st.session_state.dino_modal_open = True
            st.rerun()

def _render_dino_modal():
    """Рендерит модальное окно с динозавром."""
    # Выбираем случайную гифку
    gif_num = random.choice([1, 2])
    gif_path = f"assets/dino{gif_num}.gif"
    
    # Проверяем существование файла
    if not os.path.exists(gif_path):
        # Если гифки нет, используем placeholder из интернета
        gif_path = "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"
    
    phrase = st.session_state.dino_phrase
    
    # CSS для модалки
    st.markdown(
        """
        <style>
        .dino-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.75);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s ease-out;
        }
        .dino-modal {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            padding: 0;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6);
            overflow: hidden;
            animation: scaleIn 0.4s ease-out;
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
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes scaleIn { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }
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
    
    # Кнопка закрытия (под модалкой)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        if st.button("✖ Закрыть", key="close_dino_modal", use_container_width=True):
            st.session_state.dino_modal_open = False
            st.rerun()
    
    # Звуковой эффект "ррр" через Web Audio API (выполняется один раз при рендере)
    st.markdown(
        """
        <script>
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            oscillator.type = 'sawtooth';
            oscillator.frequency.setValueAtTime(150, audioContext.currentTime);
            oscillator.frequency.exponentialRampToValueAtTime(80, audioContext.currentTime + 0.3);
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
        } catch(err) {}
        </script>
        """,
        unsafe_allow_html=True
    )
