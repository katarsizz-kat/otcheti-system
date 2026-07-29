"""Пасхалка с динозавром - модальное окно поверх всей страницы."""
import streamlit as st
from config.mascots import get_mascot_text


def render_dino_easter_egg():
    """Рендерит кнопку и модальное окно с динозавром."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False

    qp = st.query_params
    if "activate_dino" in qp:
        st.session_state.easter_egg_activated = True
        st.query_params = {}
        st.rerun()
    elif "close_dino" in qp:
        st.session_state.easter_egg_activated = False
        st.query_params = {}
        st.rerun()

    text = get_mascot_text("dino")
    is_activated = st.session_state.easter_egg_activated

    st.markdown(f"""
    <script>
    console.log("Скрипт динозавра запущен! Активирован: {str(is_activated).lower()}");
    
    (function() {{
        if (document.getElementById('dino-btn-fixed')) return;
        
        const btn = document.createElement('div');
        btn.id = 'dino-btn-fixed';
        btn.innerText = '';
        btn.style.cssText = 'position:fixed!important; bottom:20px!important; right:20px!important; width:50px!important; height:50px!important; font-size:32px!important; display:flex!important; align-items:center!important; justify-content:center!important; cursor:pointer!important; opacity:0.3!important; z-index:999999!important; background:transparent!important; border:none!important; transition:all 0.3s!important;';
        
        btn.onmouseover = function() {{ btn.style.opacity = '1'; btn.style.transform = 'scale(1.2)'; }};
        btn.onmouseout = function() {{ btn.style.opacity = '0.3'; btn.style.transform = 'scale(1)'; }};
        btn.onclick = function() {{
            const url = new URL(window.location);
            url.searchParams.set('activate_dino', '1');
            window.location.href = url.toString();
        }};
        document.body.appendChild(btn);
        console.log("Кнопка динозавра добавлена в document.body");
        
        if ({str(is_activated).lower()}) {{
            if (document.getElementById('dino-overlay-fixed')) return;
            const overlay = document.createElement('div');
            overlay.id = 'dino-overlay-fixed';
            overlay.style.cssText = 'position:fixed!important; top:0!important; left:0!important; width:100vw!important; height:100vh!important; background:rgba(0,0,0,0.5)!important; z-index:1000000!important; display:flex!important; justify-content:center!important; align-items:center!important;';
            overlay.innerHTML = '<div style="background:white; border-radius:24px; padding:40px; max-width:400px; box-shadow:0 20px 60px rgba(0,0,0,0.3); text-align:center; position:relative;">' +
                '<button id="dino-close-fixed" style="position:absolute; top:15px; right:15px; width:36px; height:36px; background:#eee; border:none; border-radius:50%; font-size:20px; cursor:pointer;"></button>' +
                '<div style="font-size:120px; margin-bottom:20px;">🦖</div>' +
                '<p style="font-size:18px; color:#333; margin:0; line-height:1.4;">{text}</p>' +
                '</div>';
            document.body.appendChild(overlay);
            console.log("Модальное окно добавлено в document.body");
            
            document.getElementById('dino-close-fixed').onclick = function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.location.href = url.toString();
            }};
            setTimeout(function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.location.href = url.toString();
            }}, 10000);
        }}
    }})();
    </script>
    """, unsafe_allow_html=True)
