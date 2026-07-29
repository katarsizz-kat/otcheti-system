"""Пасхалка с динозавром."""
import os
import random
import streamlit as st
from config.mascots import get_random_phrase

def render_dino_footer():
    """Рендерит кнопку и логику динозавра в подвале (обход защиты Streamlit на onclick)."""
    
    # 1. Инициализация состояния
    if "dino_modal_open" not in st.session_state:
        st.session_state.dino_modal_open = False
    if "dino_phrase" not in st.session_state:
        st.session_state.dino_phrase = get_random_phrase()

    # 2. Скрытые нативные кнопки Streamlit для управления состоянием
    if st.button("open_dino_trigger", key="open_dino_trigger", style="display:none;"):
        st.session_state.dino_modal_open = True
        st.session_state.dino_phrase = get_random_phrase()  # Новая фраза при каждом открытии
        st.rerun()

    if st.button("close_dino_trigger", key="close_dino_trigger", style="display:none;"):
        st.session_state.dino_modal_open = False
        st.rerun()

    # 3. Видимая кнопка-эмодзи + JS, который "кликает" по скрытой кнопке Streamlit
    st.markdown(
        """
        <div class="dino-footer-button">
            <button class="dino-emoji-btn" id="dino-visual-btn" title="Нажми меня!">🦖</button>
        </div>
        <script>
        document.addEventListener('click', function(e) {
            if (e.target.id === 'dino-visual-btn' || e.target.closest('#dino-visual-btn')) {
                // 1. Воспроизводим звук "ррр"
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
                
                // 2. Кликаем скрытую кнопку Streamlit для открытия модалки
                const trigger = document.querySelector('button[key="open_dino_trigger"]');
                if (trigger) trigger.click();
            }
        });
        </script>
        """,
        unsafe_allow_html=True
    )

    # 4. Рендер модального окна, только если оно открыто
    if st.session_state.dino_modal_open:
        _render_dino_modal_html()

def _render_dino_modal_html():
    """Рендерит HTML модального окна."""
    gif_num = random.choice([1, 2])
    gif_path = f"assets/dino{gif_num}.gif"
    
    if not os.path.exists(gif_path):
        gif_path = "https://media.giphy.com/media/v1.Y1l3cO7hPjC7S/giphy.gif"
        
    phrase = st.session_state.dino_phrase
    
    modal_html = f"""
    <div class="dino-modal-overlay" id="dino-modal-overlay">
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
    // Закрытие по клику на крестик
    document.getElementById('dino-close-btn').addEventListener('click', function() {{
        const trigger = document.querySelector('button[key="close_dino_trigger"]');
        if (trigger) trigger.click();
    }});
    
    // Закрытие по клику вне окна (на затемненный фон)
    document.getElementById('dino-modal-overlay').addEventListener('click', function(e) {{
        if (e.target.id === 'dino-modal-overlay') {{
            const trigger = document.querySelector('button[key="close_dino_trigger"]');
            if (trigger) trigger.click();
        }}
    }});
    
    // Закрытие по клавише Escape
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
            const trigger = document.querySelector('button[key="close_dino_trigger"]');
            if (trigger) trigger.click();
        }}
    }});
    </script>
    """
    st.markdown(modal_html, unsafe_allow_html=True)
