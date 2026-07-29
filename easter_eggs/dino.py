"""Пасхалка с динозавром."""
import os
import random
import streamlit as st
from config.mascots import get_random_phrase

def render_dino_easter_egg():
    """Отображает кнопку-динозавра в правом нижнем углу."""
    
    # Генерируем звук "ррр" через Web Audio API
    dino_sound_js = """
    <script>
    function playDinoRoar() {
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
    }
    </script>
    """
    
    # Кнопка-динозавр
    button_html = f"""
    {dino_sound_js}
    <div class="dino-button-container">
        <button class="dino-button" onclick="playDinoRoar(); document.getElementById('dino-modal').style.display='flex';">
            🦖
        </button>
    </div>
    """
    
    st.markdown(button_html, unsafe_allow_html=True)
    
    # Модальное окно
    _render_dino_modal()

def _render_dino_modal():
    """Рендерит модальное окно с динозавром."""
    
    # Выбираем случайную гифку
    gif_num = random.choice([1, 2])
    gif_path = f"assets/dino{gif_num}.gif"
    
    # Получаем случайную фразу
    phrase = get_random_phrase()
    
    # JavaScript для закрытия модального окна
    close_modal_js = """
    <script>
    function closeDinoModal() {
        document.getElementById('dino-modal').style.display='none';
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
    </script>
    """
    
    # HTML модального окна
    modal_html = f"""
    {close_modal_js}
    <div id="dino-modal" class="dino-modal">
        <div class="dino-modal-content">
            <span class="dino-modal-close" onclick="closeDinoModal()">&times;</span>
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
