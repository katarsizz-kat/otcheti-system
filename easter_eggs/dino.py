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
    
    # Используем st.markdown с JavaScript для создания элементов в document.body
    st.markdown(f"""
    <script>
    (function() {{
        // Удаляем старые элементы
        const oldBtn = document.getElementById('dino-btn');
        if (oldBtn) oldBtn.remove();
        const oldOverlay = document.getElementById('dino-overlay');
        if (oldOverlay) oldOverlay.remove();
        
        const isActivated = {str(is_activated).lower()};
        
        // Создаем кнопку
        const btn = document.createElement('div');
        btn.id = 'dino-btn';
        btn.innerHTML = '🦖';
        btn.style.cssText = 'position: fixed !important; bottom: 20px !important; right: 20px !important; width: 50px !important; height: 50px !important; font-size: 32px !important; display: flex !important; align-items: center !important; justify-content: center !important; cursor: pointer !important; opacity: 0.15 !important; z-index: 999999 !important; background: transparent !important; border: none !important; transition: opacity 0.3s, transform 0.3s !important;';
        
        btn.onmouseover = function() {{ btn.style.opacity = '0.8'; btn.style.transform = 'scale(1.2)'; }};
        btn.onmouseout = function() {{ btn.style.opacity = '0.15'; btn.style.transform = 'scale(1)'; }};
        btn.onclick = function() {{
            const url = new URL(window.location);
            url.searchParams.set('activate_dino', '1');
            window.location.href = url.toString();
        }};
        document.body.appendChild(btn);
        
        // Если активировано - создаем модальное окно
        if (isActivated) {{
            const overlay = document.createElement('div');
            overlay.id = 'dino-overlay';
            overlay.style.cssText = 'position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; background: rgba(0, 0, 0, 0.5) !important; z-index: 1000000 !important; display: flex !important; justify-content: center !important; align-items: center !important;';
            
            const card = document.createElement('div');
            card.style.cssText = 'background: white; border-radius: 24px; padding: 40px; max-width: 400px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; position: relative;';
            
            const closeBtn = document.createElement('button');
            closeBtn.innerHTML = '✖';
            closeBtn.style.cssText = 'position: absolute; top: 15px; right: 15px; width: 36px; height: 36px; background: rgba(0,0,0,0.1); border: none; border-radius: 50%; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; color: #666;';
            closeBtn.onclick = function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.location.href = url.toString();
            }};
            
            const dinoEmoji = document.createElement('div');
            dinoEmoji.innerHTML = '🦖';
            dinoEmoji.style.cssText = 'font-size: 120px; margin-bottom: 20px;';
            
            const textP = document.createElement('p');
            textP.innerHTML = '{text}';
            textP.style.cssText = 'font-size: 18px; color: #2C3E50; margin: 0; line-height: 1.4;';
            
            card.appendChild(closeBtn);
            card.appendChild(dinoEmoji);
            card.appendChild(textP);
            overlay.appendChild(card);
            document.body.appendChild(overlay);
            
            setTimeout(function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.location.href = url.toString();
            }}, 10000);
        }}
    }})();
    </script>
    """, unsafe_allow_html=True)
