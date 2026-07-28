"""Пасхалка с динозавром - модальное окно с автоскрытием."""
import streamlit as st
import streamlit.components.v1 as components
from config.mascots import get_mascot_text


def init_easter_egg():
    """Инициализирует пасхалку."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False


def render_dino_modal():
    """Рендерит модальное окно с динозавром поверх всего окна."""
    if not st.session_state.get("easter_egg_activated"):
        return
    
    text = get_mascot_text("dino")
    
    # Полный HTML с iframe на всё окно (100vw x 100vh)
    components.html(f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ 
            width: 100vw; 
            height: 100vh; 
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        #overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            z-index: 9999;
            display: flex;
            justify-content: center;
            align-items: center;
            animation: fadeIn 0.3s ease-out;
        }}
        #modal {{
            background: white;
            border-radius: 24px;
            padding: 40px;
            max-width: 400px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
            animation: slideUp 0.5s ease-out;
            position: relative;
        }}
        #dino {{
            font-size: 120px;
            margin-bottom: 20px;
            animation: dinoWave 1.5s ease-in-out infinite;
            display: inline-block;
            transform-origin: bottom center;
            filter: hue-rotate(90deg) saturate(1.5);
        }}
        #text {{ 
            font-size: 18px; 
            color: #2C3E50; 
            margin: 0; 
            line-height: 1.4; 
        }}
        #close-btn {{
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
        }}
        #close-btn:hover {{ 
            background: rgba(0,0,0,0.2); 
            transform: scale(1.1); 
        }}
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
    </head>
    <body>
        <div id="overlay">
            <div id="modal">
                <button id="close-btn">✖</button>
                <div id="dino">🦖</div>
                <p id="text">{text}</p>
            </div>
        </div>
        <script>
            setTimeout(function() {{ closeModal(); }}, 10000);
            document.getElementById('close-btn').addEventListener('click', function() {{ closeModal(); }});
            function closeModal() {{
                var overlay = document.getElementById('overlay');
                overlay.style.opacity = '0';
                overlay.style.transition = 'opacity 0.3s ease';
                setTimeout(function() {{ overlay.style.display = 'none'; }}, 300);
            }}
        </script>
    </body>
    </html>
    """, height=1000, width=1000)


def render_secret_button():
    """Рендерит прозрачную кнопку с эмодзи динозавра внизу страницы."""
    if "easter_egg_activated" not in st.session_state:
        st.session_state.easter_egg_activated = False
    
    # Прозрачная кнопка через HTML с position: fixed внизу
    components.html("""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { 
            width: 100vw; 
            height: 100vh; 
            overflow: hidden;
            background: transparent;
        }
        #dino-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 40px;
            height: 40px;
            cursor: pointer;
            opacity: 0.15;
            transition: opacity 0.3s ease;
            z-index: 9998;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            user-select: none;
            background: transparent;
            border: none;
        }
        #dino-btn:hover { 
            opacity: 0.6; 
        }
    </style>
    </head>
    <body>
        <button id="dino-btn">🦖</button>
        <script>
            document.getElementById('dino-btn').addEventListener('click', function() {
                window.parent.postMessage({type: 'easter_egg_activate'}, '*');
            });
        </script>
    </body>
    </html>
    """, height=100, width=100)
