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

    # 2. Скрытый виджет-триггер (чекбокс надежно меняет session_state при клике)
    hidden_label = "🦖_HIDDEN_DINO_TRIGGER_999"
    st.checkbox(hidden_label, key="dino_trigger", value=st.session_state.dino_modal_open)

    # 3. Скрипт для скрытия виджета и обработки кликов по нашей кнопке
    st.markdown(
        f"""
        <style>
        /* Дополнительная страховка для скрытия через CSS */
        div[data-testid="stCheckbox"]:has(span:contains("{hidden_label}")) {{
            display: none !important;
        }}
        </style>
        <script>
        // Скрываем виджет динозавра после загрузки страницы
        setTimeout(() => {{
            const labels = document.querySelectorAll('label');
            labels.forEach(label => {{
                if (label.textContent.includes('{hidden_label}')) {{
                    const checkboxContainer = label.closest('div[data-testid="stCheckbox"]');
                    if (checkboxContainer) checkboxContainer.style.display = 'none';
                }}
            }});
        }}, 100);

        // Обработка клика по видимой кнопке-эмодзи
        document.addEventListener('click', function(e) {{
            if (e.target.id === 'dino-visual-btn' || e.target.closest('#dino-visual-btn')) {{
                // 1. Воспроизводим звук "ррр"
                try {{
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
                }} catch(err) {{}}
                
                // 2. Находим скрытый чекбокс Streamlit и программно кликаем его
                const labels = document.querySelectorAll('label');
                labels.forEach(label => {{
                    if (label.textContent.includes('{hidden_label}')) {{
                        const checkbox = label.querySelector('input[type="checkbox"]');
                        if (checkbox) {{
                            checkbox.click(); // Это изменит session_state и вызовет rerun
                        }}
                    }}
                }});
            }}
        }});
        </script>
        
        <div class="dino-footer-button">
            <button class="dino-emoji-btn" id="dino-visual-btn" title="Нажми меня!">🦖</button>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 4. Если триггер активен (чекбокс отмечен), обновляем фразу и показываем модалку
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
    // Функция закрытия модалки
    function closeDinoModal() {{
        const labels = document.querySelectorAll('label');
        labels.forEach(label => {{
            if (label.textContent.includes('🦖_HIDDEN_DINO_TRIGGER_999')) {{
                const checkbox = label.querySelector('input[type="checkbox"]');
                // Если чекбокс отмечен, снимаем отметку (это вызовет rerun и закроет модалку)
                if (checkbox && checkbox.checked) {{
                    checkbox.click();
                }}
            }}
        }});
    }}

    // Закрытие по клику на крестик
    document.getElementById('dino-close-btn').addEventListener('click', closeDinoModal);
    
    // Закрытие по клику вне окна (на затемненный фон)
    document.getElementById('dino-modal-overlay').addEventListener('click', function(e) {{
        if (e.target.id === 'dino-modal-overlay') {{
            closeDinoModal();
        }}
    }});
    
    // Закрытие по клавише Escape
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
            closeDinoModal();
        }}
    }});
    </script>
    """
    st.markdown(modal_html, unsafe_allow_html=True)
