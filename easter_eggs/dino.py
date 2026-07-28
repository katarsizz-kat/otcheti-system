"""Пасхалка с динозавром - модальное окно поверх всей страницы."""
import streamlit as st
from config.mascots import get_mascot_text


def render_dino_easter_egg():
    """Рендерит кнопку и модальное окно с динозавром. Вызывать в КОНЦЕ app.py"""
    
    # Инициализация состояния
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    text = get_mascot_text("dino")
    
    # JavaScript код для создания кнопки и модального окна
    st.markdown(f"""
    <script>
    (function() {{
        // Проверяем, не созданы ли уже элементы
        if (document.getElementById('dino-easter-egg-btn')) return;
        
        const isActivated = {str(st.session_state.easter_egg_activated).lower()};
        
        // Создаем кнопку
        const btn = document.createElement('div');
        btn.id = 'dino-easter-egg-btn';
        btn.innerHTML = '';
        btn.style.cssText = `
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
            filter: grayscale(0.3);
        `;
        
        btn.onmouseover = () => {{
            btn.style.opacity = '0.6';
            btn.style.transform = 'scale(1.1)';
        }};
        btn.onmouseout = () => {{
            btn.style.opacity = '0.15';
            btn.style.transform = 'scale(1)';
        }};
        
        btn.onclick = () => {{
            // Активируем через Streamlit
            const checkbox = document.querySelector('input[key="activate_dino_checkbox"]');
            if (checkbox) checkbox.click();
        }};
        
        document.body.appendChild(btn);
        
        // Если активировано - показываем модальное окно
        if (isActivated) {{
            const overlay = document.createElement('div');
            overlay.id = 'dino-overlay';
            overlay.style.cssText = `
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
            `;
            
            overlay.innerHTML = `
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
                    "></button>
                    <div style="font-size: 120px; margin-bottom: 20px; animation: dinoWave 1.5s ease-in-out infinite; display: inline-block; transform-origin: bottom center; filter: hue-rotate(90deg) saturate(1.5);">
                        🦖
                    </div>
                    <p style="font-size: 18px; color: #2C3E50; margin: 0; line-height: 1.4;">
                        {text}
                    </p>
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
            `;
            
            document.body.appendChild(overlay);
            
            // Закрытие по крестику
            document.getElementById('dino-close-btn').onclick = () => {{
                const checkbox = document.querySelector('input[key="close_dino_checkbox"]');
                if (checkbox) checkbox.click();
            }};
            
            // Автозакрытие через 10 секунд
            setTimeout(() => {{
                const checkbox = document.querySelector('input[key="close_dino_checkbox"]');
                if (checkbox) checkbox.click();
            }}, 10000);
        }}
    }})();
    </script>
    """, unsafe_allow_html=True)
    
    # Скрытые чекбоксы ТОЛЬКО для управления состоянием (не рендерятся визуально)
    col1, col2 = st.columns(2)
    with col1:
        activate = st.checkbox("", key="activate_dino_checkbox", label_visibility="collapsed")
        if activate:
            st.session_state.easter_egg_activated = True
            st.balloons()
            st.rerun()
    
    with col2:
        close = st.checkbox("", key="close_dino_checkbox", label_visibility="collapsed")
        if close:
            st.session_state.easter_egg_activated = False
            st.rerun()
    
    # Скрываем чекбоксы полностью
    st.markdown("""
    <style>
        div[data-testid="stCheckbox"] {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
