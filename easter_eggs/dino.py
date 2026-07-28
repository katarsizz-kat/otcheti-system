"""Пасхалка с динозавром - модальное окно поверх всей страницы."""
import streamlit as st
from config.mascots import get_mascot_text


def render_dino_easter_egg():
    """Рендерит кнопку и модальное окно с динозавром. Вызывать в КОНЦЕ app.py"""
    
    # Инициализация состояния
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    # Обработка активации
    if "activate_dino" in st.query_params:
        st.session_state.easter_egg_activated = True
        st.query_params.pop("activate_dino", None)
        st.rerun()
    
    # Обработка закрытия
    if "close_dino" in st.query_params:
        st.session_state.easter_egg_activated = False
        st.query_params.pop("close_dino", None)
        st.rerun()
    
    if not st.session_state.easter_egg_activated:
        # Показываем только кнопку
        text = get_mascot_text("dino")
        st.markdown(f"""
        <div id="secret-dino-btn" style="
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            cursor: pointer;
            opacity: 0.15;
            transition: all 0.3s ease;
            z-index: 9998;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            user-select: none;
            background: transparent;
            border: none;
            filter: grayscale(0.3);
        " onmouseover="this.style.opacity='0.6'; this.style.transform='scale(1.1)'" 
          onmouseout="this.style.opacity='0.15'; this.style.transform='scale(1)'">
            🦖
        </div>
        
        <script>
            document.getElementById('secret-dino-btn').addEventListener('click', function() {{
                const url = new URL(window.location);
                url.searchParams.set('activate_dino', '1');
                window.history.pushState({{}}, '', url);
                window.location.reload();
            }});
        </script>
        """, unsafe_allow_html=True)
    else:
        # Показываем модальное окно
        text = get_mascot_text("dino")
        st.markdown(f"""
        <div id="dino-overlay" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.5);
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
                    background: rgba(0,0,0,0.1);
                    border: none;
                    border-radius: 50%;
                    font-size: 20px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #666;
                    transition: all 0.2s ease;
                " onmouseover="this.style.background='rgba(0,0,0,0.2)'; this.style.transform='scale(1.1)'" 
                  onmouseout="this.style.background='rgba(0,0,0,0.1)'; this.style.transform='scale(1)'">
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
            // Закрытие по клику на крестик
            document.getElementById('dino-close-btn').addEventListener('click', function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.history.pushState({{}}, '', url);
                window.location.reload();
            }});
            
            // Автозакрытие через 10 секунд
            setTimeout(function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.history.pushState({{}}, '', url);
                window.location.reload();
            }}, 10000);
        </script>
        """, unsafe_allow_html=True)
