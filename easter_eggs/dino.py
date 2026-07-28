"""Пасхалка с динозавром - модальное окно поверх всей страницы."""
import streamlit as st
from config.mascots import get_mascot_text


def render_dino_easter_egg():
    """Рендерит кнопку и модальное окно с динозавром."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    # Безопасная работа с параметрами URL
    qp = st.query_params
    if "activate_dino" in qp:
        st.session_state.easter_egg_activated = True
        if hasattr(qp, 'clear'): qp.clear()
        else: st.query_params = {}
        st.rerun()
    elif "close_dino" in qp:
        st.session_state.easter_egg_activated = False
        if hasattr(qp, 'clear'): qp.clear()
        else: st.query_params = {}
        st.rerun()
    
    text = get_mascot_text("dino")
    is_activated = st.session_state.easter_egg_activated
    
    # Используем st.markdown с чистым JS, который внедряется в document.body
    st.markdown(f"""
    <script>
    (function() {{
        // Защита от дубликатов при перезагрузке
        if (document.getElementById('dino-global-btn')) return;
        
        // 1. Создаем кнопку внизу справа
        const btn = document.createElement('div');
        btn.id = 'dino-global-btn';
        btn.innerText = '';
        btn.style.cssText = 'position: fixed; bottom: 20px; right: 20px; width: 50px; height: 50px; font-size: 32px; display: flex; align-items: center; justify-content: center; cursor: pointer; opacity: 0.2; z-index: 999999; transition: all 0.3s; background: transparent; border: none;';
        
        btn.onmouseover = function() {{ btn.style.opacity = '1'; btn.style.transform = 'scale(1.2)'; }};
        btn.onmouseout = function() {{ btn.style.opacity = '0.2'; btn.style.transform = 'scale(1)'; }};
        btn.onclick = function() {{
            const url = new URL(window.location);
            url.searchParams.set('activate_dino', '1');
            window.location.href = url.toString();
        }};
        document.body.appendChild(btn);

        // 2. Если активировано - создаем модальное окно
        if ({str(is_activated).lower()}) {{
            if (document.getElementById('dino-global-overlay')) return;
            
            const overlay = document.createElement('div');
            overlay.id = 'dino-global-overlay';
            overlay.style.cssText = 'position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.5); z-index: 1000000; display: flex; justify-content: center; align-items: center;';

                      overlay.innerHTML = '<div style="background:white; border-radius:24px; padding:40px; max-width:400px; box-shadow:0 20px 60px rgba(0,0,0,0.3); text-align:center; position:relative;">' +
                '<button id="dino-close-fixed" style="position:absolute; top:15px; right:15px; width:36px; height:36px; background:#eee; border:none; border-radius:50%; font-size:20px; cursor:pointer;">✖</button>' +
                '<div style="font-size:120px; margin-bottom:20px;">🦖</div>' +
                '<p style="font-size:18px; color:#333; margin:0; line-height:1.4;">{text}</p>' +
                '</div>';
   
                
            document.body.appendChild(overlay);
            
            document.getElementById('dino-global-close').onclick = function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.location.href = url.toString();
            }};
            
            // Автозакрытие через 10 секунд
            setTimeout(function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.location.href = url.toString();
            }}, 10000);
        }}
    }})();
    </script>
    """, unsafe_allow_html=True)
