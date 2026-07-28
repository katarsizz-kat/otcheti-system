"""Пасхалка с динозавром - модальное окно с автоскрытием."""
import streamlit as st
from config.mascots import get_mascot_text


def init_easter_egg():
    """Инициализирует пасхалку с Konami Code."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False


def render_dino_modal():
    """Рендерит модальное окно с динозавром."""
    if not st.session_state.get("easter_egg_activated"):
        return
    
    text = get_mascot_text("dino")
    
    # Модальное окно через st.markdown (не iframe!)
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
        z-index: 9999;
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
            max-height: 300px;
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
            background: #f0f0f0 !important;
            border: none !important;
            border-radius: 50% !important;
            font-size: 18px !important;
            cursor: pointer !important;
            z-index: 10000 !important;
            padding: 0 !important;
            line-height: 1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
        }
        button[data-testid="stBaseButton-secondary"][key="close_dino_modal"]:hover {
            background: #e0e0e0 !important;
            transform: translate(calc(-50% + 160px), calc(-50% - 110px)) scale(1.1) !important;
        }
        button[data-testid="stBaseButton-secondary"][key="close_dino_modal"] span {
            display: none !important;
        }
        button[data-testid="stBaseButton-secondary"][key="close_dino_modal"]::before {
            content: '✖' !important;
            font-size: 18px !important;
            color: #333 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Невидимая кнопка для закрытия
    if st.button("", key="close_dino_modal"):
        st.session_state.easter_egg_activated = False
        st.rerun()


def render_secret_button():
    """Рендерит скрытую кнопку в футере для активации пасхалки."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    # Создаём колонку с кнопкой
    col1, col2 = st.columns([0.95, 0.05])
    
    with col2:
        # Кнопка с эмодзи динозавра
        if st.button("🦖", key="secret_dino_btn"):
            st.session_state.easter_egg_activated = True
            st.balloons()
            st.rerun()
    
    # Делаем кнопку максимально незаметной
    st.markdown("""
    <style>
        button[data-testid="stBaseButton-secondary"][key="secret_dino_btn"] {
            opacity: 0.1 !important;
            font-size: 16px !important;
            padding: 0 !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            min-width: 20px !important;
            width: 20px !important;
            height: 20px !important;
            line-height: 1 !important;
            margin: 0 !important;
        }
        button[data-testid="stBaseButton-secondary"][key="secret_dino_btn"]:hover {
            opacity: 0.5 !important;
        }
        button[data-testid="stBaseButton-secondary"][key="secret_dino_btn"] span {
            display: none !important;
        }
        button[data-testid="stBaseButton-secondary"][key="secret_dino_btn"]::before {
            content: '🦖' !important;
            font-size: 16px !important;
        }
    </style>
    """, unsafe_allow_html=True)
