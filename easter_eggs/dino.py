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
        btn.style.position = 'fixed';
        btn.style.bottom = '20px';
        btn.style.right = '20px';
        btn.style.width = '50px';
        btn.style.height = '50px';
        btn.style.fontSize = '32px';
        btn.style.display = 'flex';
        btn.style.alignItems = 'center';
        btn.style.justifyContent = 'center';
        btn.style.cursor = 'pointer';
        btn.style.opacity = '0.15';
        btn.style.zIndex = '999999';
        btn.style.background = 'transparent';
        btn.style.border = 'none';
        btn.style.transition = 'opacity 0.3s, transform 0.3s';
        
        btn.onmouseover = function() {{
            btn.style.opacity = '0.8';
            btn.style.transform = 'scale(1.2)';
        }};
        btn.onmouseout = function() {{
            btn.style.opacity = '0.15';
            btn.style.transform = 'scale(1)';
        }};
        
        btn.onclick = function() {{
            const url = new URL(window.location);
            url.searchParams.set('activate_dino', '1');
            window.location.href = url.toString();
        }};
        
        document.body.appendChild(btn);
        
        // Если активировано - показываем модальное окно
        if (isActivated) {{
            const overlay = document.createElement('div');
            overlay.id = 'dino-overlay';
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100vw';
            overlay.style.height = '100vh';
            overlay.style.background = 'rgba(0, 0, 0, 0.5)';
            overlay.style.zIndex = '1000000';
            overlay.style.display = 'flex';
            overlay.style.justifyContent = 'center';
            overlay.style.alignItems = 'center';
            
            const card = document.createElement('div');
            card.style.background = 'white';
            card.style.borderRadius = '24px';
            card.style.padding = '40px';
            card.style.maxWidth = '400px';
            card.style.boxShadow = '0 20px 60px rgba(0,0,0,0.3)';
            card.style.textAlign = 'center';
            card.style.position = 'relative';
            
            const closeBtn = document.createElement('button');
            closeBtn.innerHTML = '✖';
            closeBtn.style.position = 'absolute';
            closeBtn.style.top = '15px';
            closeBtn.style.right = '15px';
            closeBtn.style.width = '36px';
            closeBtn.style.height = '36px';
            closeBtn.style.background = 'rgba(0,0,0,0.1)';
            closeBtn.style.border = 'none';
            closeBtn.style.borderRadius = '50%';
            closeBtn.style.fontSize = '20px';
            closeBtn.style.cursor = 'pointer';
            closeBtn.style.display = 'flex';
            closeBtn.style.alignItems = 'center';
            closeBtn.style.justifyContent = 'center';
            closeBtn.style.color = '#666';
            
            closeBtn.onclick = function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.location.href = url.toString();
            }};
            
            const dinoEmoji = document.createElement('div');
            dinoEmoji.innerHTML = '🦖';
            dinoEmoji.style.fontSize = '120px';
            dinoEmoji.style.marginBottom = '20px';
            
            const textP = document.createElement('p');
            textP.innerHTML = '{text}';
            textP.style.fontSize = '18px';
            textP.style.color = '#2C3E50';
            textP.style.margin = '0';
            textP.style.lineHeight = '1.4';
            
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
