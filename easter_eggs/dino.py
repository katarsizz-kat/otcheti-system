"""Пасхалка с динозавром."""
import os
import random
import streamlit as st
from config.mascots import get_random_phrase

def render_dino_button():
    """Отображает кнопку-динозавра для встраивания в подвал."""
    
    # Генерируем звук "ррр" через Web Audio API
    dino_sound_js = """
    <script>
    function playDinoRoar() {
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
        } catch(e) {
            console.log('Audio play failed:', e);
        }
    }
    
    function openDinoModal() {
        playDinoRoar();
        const modal = document.getElementById('dino-modal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }
    
    function closeDinoModal() {
        const modal = document.getElementById('dino-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    // Закрытие по клику вне модального окна
    document.addEventListener('DOMContentLoaded', function() {
        const modal = document.getElementById('dino-modal');
        if (modal) {
            modal.addEventListener('click', function(e) {
                if (e.target === modal) {
                    closeDinoModal();
                }
            });
        }
    });
    
    // Закрытие по Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeDinoModal();
        }
    });
    </script>
    """
    
    # Кнопка-динозавр (только эмодзи, без фона)
    button_html = f"""
    {dino_sound_js}
    <div class="dino-footer-button">
        <button class="dino-emoji-btn" onclick="openDinoModal()" title="Нажми меня!">
            🦖
        </button>
    </div>
    """
    
    st.markdown(button_html, unsafe_allow_html=True)

def render_dino_modal():
    """Рендерит модальное окно с динозавром."""
    
    # Выбираем случайную гифку
    gif_num = random.choice([1, 2])
    gif_path = f"assets/dino{gif_num}.gif"
    
    # Проверяем существование файла
    if not os.path.exists(gif_path):
        # Если гифки нет, используем placeholder
        gif_path = "https://media.giphy.com/media/v1.Y1l3cO7hPjC7S/giphy.gif"
    
    # Получаем случайную фразу
    phrase = get_random_phrase()
    
    # HTML модального окна
    modal_html = f"""
    <div id="dino-modal" class="dino-modal">
        <div class="dino-modal-content">
            <span class="dino-modal-close" onclick="closeDinoModal()">&times;</span>
            <div class="dino-gif-container">
                <img src="{gif_path}" alt="Динозавр" class="dino-gif" onerror="this.src='https://media.giphy.com/media/v1.Y1l3cO7hPjC7S/giphy.gif'" />
            </div>
            <div class="dino-phrase">
                <p>{phrase}</p>
            </div>
        </div>
    </div>
    """
    
    st.markdown(modal_html, unsafe_allow_html=True)
