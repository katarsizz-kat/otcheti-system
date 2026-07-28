"""Пасхалка с динозавром - модальное окно с автоскрытием."""
import streamlit as st
from config.mascots import get_mascot_text


def init_easter_egg():
    """Инициализирует пасхалку."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False


def render_dino_modal():
    """Рендерит модальное окно с динозавром ПОВЕРХ всего."""
    if not st.session_state.get("easter_egg_activated"):
        return
    
    text = get_mascot_text("dino")
    
    # Модальное окно через st.markdown с position: fixed
    st.markdown(f"""
    <div id="dino-overlay" style="
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        z-index: 99999;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: fadeIn 0.3s ease-out;
    ">
        <div style="
            background: white;
            border-radius: 24px;
            padding: 40px;
            max-width: 400px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
            animation: slideUp 0.5s ease-out;
            position: relative;
        ">
            <div style="font-size: 120px; margin-bottom: 20px; animation: dinoWave 1.5s ease-in-out infinite; display: inline-block; transform-origin: bottom center; filter: hue-rotate(90deg) saturate(1.5);">
                🦖
            </div>
            <p style="font-size: 18px; color: #2C3E50; margin: 0; line-height: 1.4;">
                {text}
            </p>
        </div>
    </div>
    
    <style>
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        @keyframes slideUp {{
            from {{ opacity: 0; transform: translateY(50px) scale(0.8); }}
            to {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}
        @keyframes dinoWave {{
            0%, 100% {{ transform: rotate(0deg) translateY(0); }}
            25% {{ transform: rotate(-15deg) translateY(-5px); }}
            50% {{ transform: rotate(0deg) translateY(0); }}
            75% {{ transform: rotate(15deg) translateY(-5px); }}
        }}
    </style>
    
    <script>
        // Автозакрытие через 10 секунд
        setTimeout(function() {{
            var overlay = document.getElementById('dino-overlay');
            if (overlay) {{
                overlay.style.opacity = '0';
                overlay.style.transition = 'opacity 0.3s ease';
                setTimeout(function() {{
                    overlay.style.display = 'none';
                }}, 300);
            }}
        }}, 10000);
    </script>
    """, unsafe_allow_html=True)
    
    # Скрытая кнопка закрытия (позиционируется поверх модального окна)
    st.markdown("""
    <style>
        button[data-testid="stBaseButton-secondary"][key="close_dino_modal"] {
            position: fixed !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(calc(-50% + 160px), calc(-50% - 110px)) !important;
            width: 36px !important;
            height: 36px !important;
            min-width: 36px !important;
            background: rgba(255,255,255,0.3) !important;
            border: none !important;
            border-radius: 50% !important;
            font-size: 18px !important;
            cursor: pointer !important;
            z-index: 100000 !important;
            padding: 0 !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            color: #666 !important;
            opacity: 0.5 !important;
        }
        button[data-testid="stBaseButton-secondary"][key="close_dino_modal"]:hover {
            opacity: 1 !important;
            background: rgba(255,255,255,0.8) !important;
        }
        button[data-testid="stBaseButton-secondary"][key="close_dino_modal"] span {
            display: none !important;
        }
        button[data-testid="stBaseButton-secondary"][key="close_dino_modal"]::before {
            content: '✖' !important;
            font-size: 18px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Невидимая кнопка для закрытия
    if st.button("", key="close_dino_modal"):
        st.session_state.easter_egg_activated = False
        st.rerun()


def render_secret_button():
    """Рендерит прозрачную кнопку-эмодзи в правом нижнем углу."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    # Прозрачная кнопка через HTML
    st.markdown("""
    <div id="secret-dino-btn" style="
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 24px;
        height: 24px;
        cursor: pointer;
        opacity: 0.15;
        transition: opacity 0.3s ease;
        z-index: 9998;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    " onmouseover="this.style.opacity='0.6'" 
      onmouseout="this.style.opacity='0.15'"
      onclick="document.getElementById('activate-dino-checkbox').click()">
        🦖
    </div>
    """, unsafe_allow_html=True)
    
    # Скрытый checkbox для активации (Streamlit не видит HTML-клики, поэтому используем checkbox)
    activate = st.checkbox("", key="activate_dino_checkbox", label_visibility="collapsed")
    
    if activate:
        st.session_state.easter_egg_activated = True
        st.balloons()
        st.rerun()
    
    # Стили для скрытия checkbox и позиционирования его поверх кнопки
    st.markdown("""
    <style>
        div[data-testid="stCheckbox"] > label {
            position: fixed !important;
            bottom: 20px !important;
            right: 20px !important;
            width: 24px !important;
            height: 24px !important;
            opacity: 0 !important;
            cursor: pointer !important;
            z-index: 9999 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div[data-testid="stCheckbox"] > label > div {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
