"""Пасхалка с динозавром - модальное окно поверх всей страницы."""
import streamlit as st
from config.mascots import get_mascot_text


def render_dino_easter_egg():
    """Рендерит кнопку и модальное окно с динозавром."""
    
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    query_params = st.query_params
    if "activate_dino" in query_params:
        st.session_state.easter_egg_activated = True
        st.query_params = {}
        st.rerun()
    elif "close_dino" in query_params:
        st.session_state.easter_egg_activated = False
        st.query_params = {}
        st.rerun()
    
    text = get_mascot_text("dino")
    is_activated = st.session_state.easter_egg_activated
    
    # Используем components.html вместо st.markdown - он не создаёт контейнер в потоке
    from streamlit.components.v1 import html
    
    html(f"""
    <div id="dino-container" style="position: fixed; top: 0; left: 0; width: 0; height: 0; overflow: visible; z-index: 99999;">
        <div id="dino-easter-egg-btn" style="
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            cursor: pointer;
            opacity: 0.15;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            user-select: none;
            background: transparent;
            border: none;
        " onmouseover="this.style.opacity='0.6'; this.style.transform='scale(1.1)'" 
           onmouseout="this.style.opacity='0.15'; this.style.transform='scale(1)'">
            
        </div>
    </div>
    
    <script>
        const btn = document.getElementById('dino-easter-egg-btn');
        btn.onclick = function() {{
            const url = new URL(window.location);
            url.searchParams.set('activate_dino', '1');
            window.location.href = url.toString();
        }};
    </script>
    """, height=0, width=0)
    
    if is_activated:
        html(f"""
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
        ">
            <div style="
                background: white;
                border-radius: 24px;
                padding: 40px;
                max-width: 400px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
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
                ">✖</button>
                <div style="font-size: 120px; margin-bottom: 20px;">🦖</div>
                <p style="font-size: 18px; color: #2C3E50; margin: 0;">{text}</p>
            </div>
        </div>
        
        <script>
            document.getElementById('dino-close-btn').onclick = function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.location.href = url.toString();
            }};
            
            setTimeout(function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.location.href = url.toString();
            }}, 10000);
        </script>
        """, height=0, width=0)
