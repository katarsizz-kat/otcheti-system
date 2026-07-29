"""Пасхалка с динозавром — исправленная версия."""
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
    
    # CSS с максимальным контрастом
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
            pointer-events: none;
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
            pointer-events: auto;
        }
        .dino-close-btn {
            position: absolute;
            right: 15px;
            top: 15px;
            color: #000000 !important;
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
    
    # HTML модалки с JavaScript для закрытия
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
    // Функция закрытия — скрывает модалку И уведомляет Streamlit
    function closeDinoModal() {{
        const overlay = document.getElementById('dino-overlay');
        if (overlay) {{
            overlay.style.display = 'none';
            // Находим скрытый чекбокс и снимаем галочку
            const labels = document.querySelectorAll('label');
            labels.forEach(label => {{
                if (label.textContent.includes('DINO_CLOSE_TRIGGER')) {{
                    const checkbox = label.querySelector('input[type="checkbox"]');
                    if (checkbox && checkbox.checked) {{
                        checkbox.click();
                    }}
                }}
            }});
        }}
    }}
    
    // Закрытие по крестику
    document.getElementById('dino-close-btn').addEventListener('click', function() {{
        closeDinoModal();
    }});
    
    // Закрытие по клику вне окна
    document.getElementById('dino-overlay').addEventListener('click', function(e) {{
        if (e.target.id === 'dino-overlay') {{
            closeDinoModal();
        }}
    }});
    
    // Закрытие по Escape
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
            closeDinoModal();
        }}
    }});
    
    // Звук "ррр" через Web Audio API (воспроизводится при загрузке модалки)
    try {{
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        oscillator.type = 'sawtooth';
        oscillator.frequency.setValueAtTime(150, audioContext.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(80, audioContext.currentTime + 0.5);
        gainNode.gain.setValueAtTime(0.5, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    }} catch(err) {{
        console.log('Audio error:', err);
    }}
    </script>
    """
    
    st.markdown(modal_html, unsafe_allow_html=True)
    
    # Скрытый чекбокс для сброса состояния (невидимый)
    st.checkbox("DINO_CLOSE_TRIGGER", key="dino_close_trigger", value=False)
    
    # Если чекбокс активен (закрыли модалку), сбрасываем состояние
    if st.session_state.dino_close_trigger:
        st.session_state.dino_modal_open = False
        st.session_state.dino_close_trigger = False  # Сбрасываем для следующего раза
        st.rerun()
    
    # НАТИВНАЯ кнопка закрытия Streamlit (гарантированно работает)
    st.markdown('<div class="dino-close-streamlit">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        if st.button("✖ Закрыть окно", key="dino_close_native_btn", use_container_width=True):
            st.session_state.dino_modal_open = False
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
