"""Пасхалка с динозавром."""
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
    
    # Загружаем гифку как base64 (гарантированно работает на Streamlit Cloud)
    gif_base64 = _get_gif_base64(gif_path)
    if gif_base64:
        gif_src = f"data:image/gif;base64,{gif_base64}"
    else:
        # Fallback на внешний URL, если файл не найден
        gif_src = "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"
    
    phrase = st.session_state.dino_phrase
    
    # CSS для модалки с максимальным контрастом и умными кликами
    st.markdown(
        """
        <style>
        .dino-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.75);
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none; /* КЛИКИ ПРОХОДЯТ СКВОЗЬ ЗАТЕМНЕНИЕ */
            backdrop-filter: blur(4px);
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
            pointer-events: auto; /* КЛИКИ НА САМОЙ МОДАЛКЕ РАБОТАЮТ */
        }
        .dino-close-btn {
            position: absolute;
            right: 15px;
            top: 15px;
            color: #333333 !important;
            font-size: 32px;
            font-weight: bold;
            cursor: pointer;
            z-index: 10;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: rgba(0,0,0,0.1);
            border: none;
            line-height: 1;
            transition: all 0.2s ease;
        }
        .dino-close-btn:hover {
            background: rgba(0,0,0,0.2);
            transform: scale(1.1);
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
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
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
        .dino-close-streamlit {
            margin-top: 20px;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # HTML модалки с JavaScript для закрытия (Escape, 10 сек, крестик)
    modal_html = f"""
    <div class="dino-overlay" id="dino-overlay">
        <div class="dino-modal">
            <button class="dino-close-btn" id="dino-close-btn" title="Закрыть">&times;</button>
            <div class="dino-gif-container">
                <img src="{gif_src}" alt="Динозавр" class="dino-gif" />
            </div>
            <div class="dino-phrase">
                <p>{phrase}</p>
            </div>
        </div>
    </div>
    <script>
    function closeDinoModal() {{
        const overlay = document.getElementById('dino-overlay');
        if (overlay) {{
            overlay.style.display = 'none';
        }}
    }}
    
    document.getElementById('dino-close-btn').addEventListener('click', function(e) {{
        e.preventDefault();
        closeDinoModal();
    }});
    
    document.getElementById('dino-overlay').addEventListener('click', function(e) {{
        if (e.target.id === 'dino-overlay') {{
            closeDinoModal();
        }}
    }});
    
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
            closeDinoModal();
        }}
    }});
    
    setTimeout(closeDinoModal, 10000);
    </script>
    """
    
    st.markdown(modal_html, unsafe_allow_html=True)
    
    # ГАРАНТИРОВАННАЯ кнопка закрытия через Streamlit
    # Она находится под модалкой, но так как overlay имеет pointer-events: none, 
    # клик по области под модалкой попадёт на эту кнопку!
    st.markdown('<div class="dino-close-streamlit">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        if st.button("✖ Закрыть окно", key="dino_close_native_btn", use_container_width=True):
            st.session_state.dino_modal_open = False
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Звуковой эффект "ррр"
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
