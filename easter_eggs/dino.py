"""Пасхалка с динозавром - модальное окно с размытым фоном."""
import streamlit as st
import streamlit.components.v1 as components
from config.mascots import get_mascot_text


def init_easter_egg():
    """Инициализирует пасхалку с Konami Code."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    # JavaScript для перехвата Konami Code: ↑↑↓↓←→←→BA
    konami_js = """
    <script>
        const konamiCode = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 
                           'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
        let konamiIndex = 0;
        
        document.addEventListener('keydown', function(e) {
            const key = e.key.length > 1 ? e.key : e.key.toLowerCase();
            if (key === konamiCode[konamiIndex]) {
                konamiIndex++;
                if (konamiIndex === konamiCode.length) {
                    window.parent.postMessage({type: 'easter_egg_activated'}, '*');
                    konamiIndex = 0;
                }
            } else {
                konamiIndex = 0;
            }
        });
    </script>
    """
    components.html(konami_js, height=0, width=0)


def render_dino_modal():
    """Рендерит модальное окно с динозавром."""
    if not st.session_state.get("easter_egg_activated"):
        return
    
    text = get_mascot_text("dino")
    
    # Модальное окно с размытым фоном и встроенной кнопкой закрытия
    st.markdown(f"""
    <div id="dino-modal-overlay" style="
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        z-index: 1000;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: fadeIn 0.3s ease-out;
    ">
        <div style="
            background: white;
            border-radius: 24px;
            padding: 40px;
            max-width: 25vw;
            max-height: 25vh;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
            animation: slideUp 0.5s ease-out;
            position: relative;
        ">
            <button id="dino-close-btn" style="
                position: absolute;
                top: 15px;
                right: 15px;
                width: 36px;
                height: 36px;
                background: #f0f0f0;
                border: none;
                border-radius: 50%;
                font-size: 20px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #333;
                transition: all 0.2s ease;
                z-index: 1001;
            " onmouseover="this.style.background='#e0e0e0'; this.style.transform='scale(1.1)'" 
              onmouseout="this.style.background='#f0f0f0'; this.style.transform='scale(1)'">
                ✖
            </button>
            <div style="font-size: 120px; margin-bottom: 20px; animation: dinoWave 1.5s ease-in-out infinite; display: inline-block; transform-origin: bottom center; filter: hue-rotate(90deg) saturate(1.5);">
                
            </div>
            <p style="font-size: 18px; color: #2C3E50; margin: 0 0 20px 0; line-height: 1.4;">
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
        document.getElementById('dino-close-btn').addEventListener('click', function() {{
            var overlay = document.getElementById('dino-modal-overlay');
            overlay.style.opacity = '0';
            overlay.style.transition = 'opacity 0.3s ease';
            setTimeout(function() {{
                overlay.style.display = 'none';
            }}, 300);
        }});
    </script>
    """, unsafe_allow_html=True)


def render_secret_button():
    """Рендерит скрытую кнопку в футере для активации пасхалки."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    col1, col2, col3 = st.columns([0.85, 0.1, 0.05])
    
    with col3:
        if st.button("🦖", key="secret_dino_btn", help="Нажми меня!"):
            st.session_state.easter_egg_activated = True
            st.balloons()
            st.rerun()
    
    st.markdown("""
    <style>
        button[data-testid="stBaseButton-secondary"][key="secret_dino_btn"] {
            opacity: 0.3 !important;
            font-size: 16px !important;
            padding: 4px 8px !important;
            background: transparent !important;
            border: none !important;
        }
        button[data-testid="stBaseButton-secondary"][key="secret_dino_btn"]:hover {
            opacity: 0.8 !important;
        }
    </style>
    """, unsafe_allow_html=True)
