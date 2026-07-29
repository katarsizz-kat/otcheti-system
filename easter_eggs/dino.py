"""Пасхалка с динозавром."""
import os
import random
import streamlit as st
from config.mascots import get_random_phrase

def render_dino_footer():
    """Рендерит кнопку и логику динозавра в подвале."""
    
    # 1. Инициализация состояния
    if "dino_modal_open" not in st.session_state:
        st.session_state.dino_modal_open = False
    if "dino_phrase" not in st.session_state:
        st.session_state.dino_phrase = get_random_phrase()

    # 2. Скрытый чекбокс для управления состоянием (надежный способ Streamlit)
    st.checkbox("🦖_HIDDEN_DINO_TRIGGER_999", key="dino_trigger", value=st.session_state.dino_modal_open)

    # 3. Видимая кнопка-эмодзи и JS для управления
    st.markdown(
        """
        <style>
        /* Скрываем чекбокс динозавра через CSS */
        div[data-testid="stCheckbox"]:has(label:contains("🦖_HIDDEN_DINO_TRIGGER_999")) {
            display: none !important;
        }
        .dino-footer-button { text-align: left; margin-bottom: 16px; padding-left: 8px; }
        .dino-emoji-btn { 
            background: transparent !important; 
            border: none !important; 
            font-size: 32px; 
            cursor: pointer; 
            padding: 8px 12px; 
            transition: all 0.3s ease; 
            border-radius: 8px; 
            line-height: 1; 
        }
        .dino-emoji-btn:hover { transform: scale(1.2) rotate(-10deg); background: rgba(255,255,255,0.1) !important; }
        .dino-emoji-btn:active { transform: scale(1.1); }
        </style>
        <script>
        // Скрываем чекбокс (дополнительная страховка JS)
        document.addEventListener("DOMContentLoaded", function() {
            const labels = document.querySelectorAll('label');
            labels.forEach(label => {
                if (label.textContent.includes('🦖_HIDDEN_DINO_TRIGGER_999')) {
                    const container = label.closest('div[data-testid="stCheckbox"]');
                    if (container) container.style.display = 'none';
                }
            });
        });

        // Обработка клика по кнопке-динозавру
        document.addEventListener('click', function(e) {
            if (e.target.id === 'dino-visual-btn' || e.target.closest('#dino-visual-btn')) {
                // 1. Звук "ррр"
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
                
                // 2. Программно кликаем скрытый чекбокс Streamlit
                const labels = document.querySelectorAll('label');
                labels.forEach(label => {
                    if (label.textContent.includes('🦖_HIDDEN_DINO_TRIGGER_999')) {
                        const checkbox = label.querySelector('input[type="checkbox"]');
                        if (checkbox) checkbox.click();
                    }
                });
            }
        });
        </script>
        <div class="dino-footer-button">
            <button class="dino-emoji-btn" id="dino-visual-btn" title="Нажми меня!">🦖</button>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 4. Если чекбокс активен, обновляем фразу и показываем модалку
    if st.session_state.dino_trigger:
        st.session_state.dino_phrase = get_random_phrase()
        _render_dino_modal_html()

def _render_dino_modal_html():
    """Рендерит HTML модального окна."""
    gif_num = random.choice([1, 2])
    gif_path = f"assets/dino{gif_num}.gif"
    
    if not os.path.exists(gif_path):
        gif_path = "https://media.giphy.com/media/v1.Y1l3cO7hPjC7S/giphy.gif"
        
    phrase = st.session_state.dino_phrase
    
    # Обрати внимание на style="display: flex !important;" — это переопределяет display: none из styles.py
    modal_html = f"""
    <div class="dino-modal" id="dino-modal" style="display: flex !important;">
        <div class="dino-modal-content">
            <span class="dino-modal-close" id="dino-close-btn">&times;</span>
            <div class="dino-gif-container">
                <img src="{gif_path}" alt="Динозавр" class="dino-gif" onerror="this.src='https://media.giphy.com/media/v1.Y1l3cO7hPjC7S/giphy.gif'" />
            </div>
            <div class="dino-phrase">
                <p>{phrase}</p>
            </div>
        </div>
    </div>
    <script>
    function closeDinoModal() {{
        const labels = document.querySelectorAll('label');
        labels.forEach(label => {{
            if (label.textContent.includes('🦖_HIDDEN_DINO_TRIGGER_999')) {{
                const checkbox = label.querySelector('input[type="checkbox"]');
                if (checkbox && checkbox.checked) {{
                    checkbox.click(); // Снимет галочку и вызовет rerun
                }}
            }}
        }});
    }}
    
    document.getElementById('dino-close-btn').addEventListener('click', closeDinoModal);
    
    document.getElementById('dino-modal').addEventListener('click', function(e) {{
        if (e.target.id === 'dino-modal') {{
            closeDinoModal();
        }}
    }});
    
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
            closeDinoModal();
        }}
    }});
    </script>
    """
    st.markdown(modal_html, unsafe_allow_html=True)
