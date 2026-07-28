"""Пасхалка с динозавром - модальное окно поверх всей страницы."""
import streamlit as st
from config.mascots import get_mascot_text


def render_dino_easter_egg():
    """Рендерит кнопку и модальное окно с динозавром. Вызывать в КОНЦЕ app.py"""
    
    # Инициализация состояния
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    # Проверяем URL параметры для активации/закрытия
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
    
    # Чистый JavaScript - создаёт элементы напрямую в document.body
    st.markdown(f"""
    <script>
    (function() {{
        // Удаляем старые элементы если есть
        const oldBtn = document.getElementById('dino-easter-egg-btn');
        if (oldBtn) oldBtn.remove();
        const oldOverlay = document.getElementById('dino-overlay');
        if (oldOverlay) oldOverlay.remove();
        
        const isActivated = {str(is_activated).lower()};
        
        // Создаем кнопку внизу справа
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
            background: transparent;
            border: none;
        `;
        
        btn.onmouseover = function() {{
            btn.style.opacity = '0.6';
            btn.style.transform = 'scale(1.1)';
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
            
            const closeBtn = document.createElement('button');
            closeBtn.id = 'dino-close-btn';
            closeBtn.innerHTML = '✖';
            closeBtn.style.cssText = `
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
            `;
            closeBtn.onmouseover = function() {{
                closeBtn.style.background = 'rgba(0,0,0,0.2)';
                closeBtn.style.transform = 'scale(1.1)';
            }};
            closeBtn.onmouseout = function() {{
                closeBtn.style.background = 'rgba(0,0,0,0.1)';
                closeBtn.style.transform = 'scale(1)';
            }};
            closeBtn.onclick = function() {{
                const url = new URL(window.location);
                url.searchParams.set('close_dino', '1');
                window.location.href = url.toString();
            }};
            
            const dinoEmoji = document.createElement('div');
            dinoEmoji.innerHTML = '🦖';
            dinoEmoji.style.cssText = `
                font-size: 120px;
                margin-bottom: 20px;
                animation: dinoWave 1.5s ease-in-out infinite;
                display: inline-block;
                transform-origin: bottom center;
                filter: hue-rotate(90deg) saturate(1.5);
            `;
            
            const textP = document.createElement('p');
            textP.innerHTML = `{text}`;
            textP.style.cssText = `
                font-size: 18px;
                color: #2C3E50;
                margin: 0;
                line-height: 1.4;
            `;
            
            const card = document.createElement('div');
            card.style.cssText = `
                background: white;
                border-radius: 24px;
                padding: 40px;
                max-width: 400px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
                animation: slideUp 0.5s ease-out;
                position: relative;
            `;
            
            card.appendChild(closeBtn);
            card.appendChild(dinoEmoji);
            card.appendChild(textP);
            overlay.appendChild(card);
            
            // Добавляем стили анимации
            const style = document.createElement('style');
            style.innerHTML = `
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
            `;
            document.head.appendChild(style);
            
            document.body.appendChild(overlay);
            
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
