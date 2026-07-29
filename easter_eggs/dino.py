"""Пасхалка с динозавром."""
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
    st.markdown(
        """
        <style>
        .dino-footer-button { text-align: left; margin-bottom: 16px; padding-left: 8px; }
        .dino-emoji-btn { 
            background: rgba(255,255,255,0.1) !important; 
            border: none !important; 
            font-size: 32px; 
            cursor: pointer; 
            padding: 8px 12px; 
            transition: all 0.3s ease; 
            border-radius: 8px; 
            line-height: 1; 
        }
        .dino-emoji-btn:hover { transform: scale(1.2) rotate(-10deg); background: rgba(255,255,255,0.2) !important; }
        .dino-emoji-btn:active { transform: scale(1.1); }
        </style>
        <div class="dino-footer-button">
            <button class="dino-emoji-btn" id="dino-open-btn" title="Нажми меня!">🦖</button>
        </div>
        <script>
        document.getElementById('dino-open-btn').addEventListener('click', function() {
            // Находим скрытый чекбокс Streamlit и кликаем его
            const labels = document.querySelectorAll('label');
            labels.forEach(label => {
                if (label.textContent.includes('DINO_TRIGGER_HIDDEN')) {
                    const checkbox = label.querySelector('input[type="checkbox"]');
                    if (checkbox) checkbox.click();
                }
            });
        });
        </script>
        """,
        unsafe_allow_html=True
    )
    
    # Скрытый чекбокс для управления состоянием
    st.checkbox("DINO_TRIGGER_HIDDEN", key="dino_trigger", value=False)
    
    # Если чекбокс активен, открываем модалку
    if st.session_state.dino_trigger:
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
        .dino-close-btn {
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
        }
        .dino-close-btn:hover {
            color: #FFD700;
            transform: scale(1.2);
            background: rgba(255,255,255,0.1);
        }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes scaleIn { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # HTML модалки с JavaScript для закрытия
    modal_html = f"""
    <div class="dino-overlay" id="dino-overlay">
        <div class="dino-modal" style="position: relative;">
            <span class="dino-close-btn" id="dino-close-btn">&times;</span>
            <div class="dino-gif-container">
                <img src="{gif_path}" alt="Динозавр" class="dino-gif" />
            </div>
            <div class="dino-phrase">
                <p>{phrase}</p>
            </div>
        </div>
    </div>
    <script>
    // Функция закрытия модалки
    function closeDinoModal() {{
        const labels = document.querySelectorAll('label');
        labels.forEach(label => {{
            if (label.textContent.includes('DINO_TRIGGER_HIDDEN')) {{
                const checkbox = label.querySelector('input[type="checkbox"]');
                if (checkbox && checkbox.checked) {{
                    checkbox.click(); // Снимет галочку и вызовет rerun
                }}
            }}
        }});
    }}
    
    // Закрытие по клику на крестик
    document.getElementById('dino-close-btn').addEventListener('click', closeDinoModal);
    
    // Закрытие по клику вне окна (на затемненный фон)
    document.getElementById('dino-overlay').addEventListener('click', function(e) {{
        if (e.target.id === 'dino-overlay') {{
            closeDinoModal();
        }}
    }});
    
    // Закрытие по клавише Escape
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
            closeDinoModal();
        }}
    }});
    
    // Автозакрытие через 10 секунд
    setTimeout(closeDinoModal, 10000);
    </script>
    """
    
    st.markdown(modal_html, unsafe_allow_html=True)
    
    # Звуковой эффект "ррр" через Web Audio API
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
