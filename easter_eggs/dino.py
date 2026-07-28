"""Пасхалка с динозавром - модальное окно с автоскрытием."""
import streamlit as st
from config.mascots import get_mascot_text


def init_easter_egg():
    """Инициализирует пасхалку с Konami Code."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    # JavaScript для перехвата Konami Code через st.markdown
    konami_js = """
    <script>
        // Konami Code: ↑↑↓↓←→←→BA
        const konamiCode = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 
                           'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
        let konamiIndex = 0;
        
        document.addEventListener('keydown', function(e) {
            const key = e.key;
            if (key === konamiCode[konamiIndex]) {
                konamiIndex++;
                if (konamiIndex === konamiCode.length) {
                    // Активируем чекбокс
                    var checkbox = document.getElementById('easter-egg-checkbox');
                    if (checkbox) {
                        checkbox.checked = true;
                        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    konamiIndex = 0;
                }
            } else {
                konamiIndex = 0;
            }
        });
    </script>
    """
    st.markdown(konami_js, unsafe_allow_html=True)


def render_dino_modal():
    """Рендерит модальное окно с динозавром."""
    if not st.session_state.get("easter_egg_activated"):
        return
    
    text = get_mascot_text("dino")
    
    # Модальное окно через st.markdown
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
            <button id="dino-close-btn" style="
                position: absolute;
                top: 15px;
                right: 15px;
                width: 36px;
                height: 36px;
                background: rgba(255,255,255,0.8);
                border: none;
                border-radius: 50%;
                font-size: 20px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #666;
                opacity: 0.5;
                transition: all 0.2s ease;
                z-index: 100000;
            " onmouseover="this.style.opacity='1'; this.style.transform='scale(1.1)'" 
              onmouseout="this.style.opacity='0.5'; this.style.transform='scale(1)'">
                ✖
            </button>
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
        
        // Закрытие по клику на крестик
        document.getElementById('dino-close-btn').addEventListener('click', function() {{
            var overlay = document.getElementById('dino-overlay');
            overlay.style.opacity = '0';
            overlay.style.transition = 'opacity 0.3s ease';
            setTimeout(function() {{
                overlay.style.display = 'none';
            }}, 300);
        }});
    </script>
    """, unsafe_allow_html=True)


def render_secret_button():
    """Рендерит видимую кнопку в правом нижнем углу."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    # Создаём колонку с кнопкой
    col1, col2 = st.columns([0.92, 0.08])
    
    with col2:
        # Видимая кнопка с эмодзи динозавра
        if st.button("🦖", key="secret_dino_btn", help="Секретная пасхалка!"):
            st.session_state.easter_egg_activated = True
            st.balloons()
            st.rerun()
    
    # Стили для кнопки
    st.markdown("""
    <style>
        button[data-testid="stBaseButton-secondary"][key="secret_dino_btn"] {
            background: rgba(255,255,255,0.2) !important;
            border: 2px solid rgba(255,255,255,0.3) !important;
            border-radius: 12px !important;
            font-size: 24px !important;
            padding: 8px 12px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
            transition: all 0.3s ease !important;
        }
        button[data-testid="stBaseButton-secondary"][key="secret_dino_btn"]:hover {
            background: rgba(255,255,255,0.4) !important;
            transform: scale(1.1) !important;
            box-shadow: 0 6px 16px rgba(0,0,0,0.2) !important;
        }
    </style>
    """, unsafe_allow_html=True)
