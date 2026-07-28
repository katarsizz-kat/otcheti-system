"""Пасхалка с динозавром - модальное окно поверх всей страницы."""
import streamlit as st
from config.mascots import get_mascot_text


def init_easter_egg():
    """Инициализирует пасхалку."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False


def render_dino_modal():
    """Рендерит модальное окно с динозавром поверх всей страницы."""
    if not st.session_state.get("easter_egg_activated"):
        return
    
    text = get_mascot_text("dino")
    
    # Скрытый чекбокс для корректного закрытия через JS
    close_trigger = st.checkbox(
        "", 
        key="close_dino_checkbox", 
        label_visibility="collapsed"
    )
    
    if close_trigger:
        st.session_state.easter_egg_activated = False
        st.rerun()

    # Модальное окно через st.markdown с position: fixed
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
        /* Скрываем чекбокс закрытия полностью */
        div[data-testid="stCheckbox"] > label:has(input[key="close_dino_checkbox"]) {{
            display: none !important;
        }}
    </style>
    
    <script>
        // Функция для программного нажатия на скрытый чекбокс Streamlit
        function triggerClose() {{
            var checkboxes = document.querySelectorAll('input[type="checkbox"]');
            for (var i = 0; i < checkboxes.length; i++) {{
                if (checkboxes[i].id.includes('close_dino_checkbox')) {{
                    checkboxes[i].click();
                    break;
                }}
            }}
        }}

        // Автозакрытие через 10 секунд
        setTimeout(function() {{
            var overlay = document.getElementById('dino-overlay');
            if (overlay) {{
                overlay.style.opacity = '0';
                overlay.style.transition = 'opacity 0.3s ease';
                setTimeout(function() {{
                    overlay.style.display = 'none';
                    triggerClose();
                }}, 300);
            }}
        }}, 10000);
        
        // Закрытие по клику на крестик
        document.addEventListener('click', function(e) {{
            if (e.target.id === 'dino-close-btn' || e.target.closest('#dino-close-btn')) {{
                var overlay = document.getElementById('dino-overlay');
                if (overlay) {{
                    overlay.style.opacity = '0';
                    overlay.style.transition = 'opacity 0.3s ease';
                    setTimeout(function() {{
                        overlay.style.display = 'none';
                        triggerClose();
                    }}, 300);
                }}
            }}
        }});
    </script>
    """, unsafe_allow_html=True)


def render_secret_button():
    """Рендерит прозрачную кнопку с эмодзи динозавра внизу страницы."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    # Прозрачная кнопка через HTML с позиционированием внизу
    st.markdown("""
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
      onmouseout="this.style.opacity='0.15'; this.style.transform='scale(1)'"
      onclick="document.querySelector('input[key=\"activate_dino_checkbox\"]').click()">
        🦖
    </div>
    """, unsafe_allow_html=True)
    
    # Скрытый checkbox для активации - размещаем в самом низу
    activate = st.checkbox("", key="activate_dino_checkbox", label_visibility="collapsed")
    
    if activate:
        st.session_state.easter_egg_activated = True
        st.balloons()
        st.rerun()
    
    # Стили для полного скрытия checkbox активации
    st.markdown("""
    <style>
        div[data-testid="stCheckbox"] > label:has(input[key="activate_dino_checkbox"]) {
            display: none !important;
        }
        /* Убираем любые отступы у контейнера чекбокса */
        div[data-testid="stCheckbox"]:has(input[key="activate_dino_checkbox"]) {
            position: fixed !important;
            bottom: 20px !important;
            right: 20px !important;
            width: 50px !important;
            height: 50px !important;
            margin: 0 !important;
            padding: 0 !important;
            z-index: 9999 !important;
        }
    </style>
    """, unsafe_allow_html=True)
