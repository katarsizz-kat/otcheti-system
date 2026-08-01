"""Стили интерфейса приложения."""
import streamlit as st
from config.theme import get_theme_colors
from config.effects import get_theme_effect, get_holiday_effects


def apply_theme(theme: str, holiday_effects: list = None):
    """
    Применяет тему и эффекты к приложению.
    Этапы:
    1. Принудительная светлая тема Streamlit
    2. Загрузка цветов темы
    3. Базовые стили интерфейса (header, sidebar, карточки)
    4. Подключение эффектов времени суток
    5. Подключение праздничных эффектов
    """
    if holiday_effects is None:
        holiday_effects = []

    # 1. Принудительная светлая тема Streamlit
    st.config.set_option("theme.base", "light")
    st.config.set_option("theme.backgroundColor", "#FFFFFF")
    st.config.set_option("theme.primaryColor", "#005F6B")
    st.config.set_option("theme.secondaryBackgroundColor", "#F5F5DC")
    st.config.set_option("theme.textColor", "#2C2C2C")

    # 2. Загрузка цветов темы
    colors = get_theme_colors(theme)

    # Определяем, тёмная ли тема (для логотипов)
    is_dark_theme = theme in ["night", "new_year", "magic", "scifi", "military"]
    logo_opacity = "0.85" if is_dark_theme else "0.6"

    # 3. Базовые стили интерфейса с CSS-переменными
    base_css = (
        "<style>"

        # ===== CSS-ПЕРЕМЕННЫЕ ДЛЯ ТЕМЫ =====
        ":root { "
        f"  --bg-main: {colors['bg_main']}; "
        f"  --bg-sidebar: {colors['bg_sidebar']}; "
        f"  --header-bg: {colors['header_bg']}; "
        f"  --header-text: {colors['header_text']}; "
        f"  --text-primary: {colors['text_primary']}; "
        f"  --text-secondary: {colors['text_secondary']}; "
        f"  --card-bg: {colors['card_bg']}; "
        f"  --card-border: {colors['card_border']}; "
        f"  --accent: {colors['accent']}; "
        f"  --button-bg: {colors['button_bg']}; "
        f"  --button-text: {colors['button_text']}; "
        f"  --logo-opacity: {logo_opacity}; "
        "} "

        # ===== ПРИНУДИТЕЛЬНАЯ СВЕТЛАЯ ТЕМА STREAMLIT =====
        " .stApp { "
        "   background: var(--bg-main) !important; "
        "   min-height: 100vh; "
        " } "

        # ===== ВЕРХНЯЯ ПАНЕЛЬ (продолжение фона) =====
        " header { "
        "   background: transparent !important; "
        "   border-bottom: none !important; "
        " } "
        " .stApp [data-testid='stHeader'] { "
        "   background: transparent !important; "
        " } "

        # ===== БОКОВАЯ ПАНЕЛЬ (полупрозрачная с оттенком фона) =====
        " section[data-testid='stSidebar'] { "
        "   background: var(--bg-sidebar) !important; "
        "   border-right: 1px solid var(--card-border); "
        "   opacity: 0.95; "
        " } "
        " section[data-testid='stSidebar'] > div { "
        "   background: transparent !important; "
        " } "
        " section[data-testid='stSidebar'] p, "
        " section[data-testid='stSidebar'] h1, "
        " section[data-testid='stSidebar'] h2, "
        " section[data-testid='stSidebar'] h3, "
        " section[data-testid='stSidebar'] .stMarkdown, "
        " section[data-testid='stSidebar'] label, "
        " section[data-testid='stSidebar'] button { "
        "   color: var(--text-primary) !important; "
        " } "

        # ===== ПРИВЕТСТВЕННЫЙ БЛОК =====
        " .welcome-block { "
        "   background: var(--header-bg); "
        "   padding: 32px; "
        "   border-radius: 20px; "
        "   margin-bottom: 32px; "
        "   box-shadow: 0 8px 24px rgba(0,0,0,0.15); "
        "   border: 2px solid rgba(255,255,255,0.3); "
        " } "
        " .welcome-icon { "
        "   font-size: 48px; "
        "   margin-bottom: 12px; "
        "   display: inline-block; "
        "   animation: float 3s ease-in-out infinite; "
        " } "
        " .welcome-title { "
        "   font-size: 36px; "
        "   font-weight: 700; "
        "   color: var(--header-text) !important; "
        "   margin: 0 0 8px 0; "
        "   text-shadow: 2px 2px 4px rgba(0,0,0,0.2); "
        " } "
        " .welcome-subtitle { "
        "   font-size: 18px; "
        "   color: var(--header-text) !important; "
        "   margin: 0 0 16px 0; "
        "   opacity: 0.95; "
        " } "
        " .welcome-hint { "
        "   font-size: 16px; "
        "   color: var(--header-text) !important; "
        "   margin: 0; "
        "   opacity: 0.9; "
        " } "

        # ===== HEADER-BLOCK (ЗАГОЛОВОК СТРАНИЦЫ С ГРАДИЕНТОМ) =====
        " .header-block { "
        "   background: var(--header-bg); "
        "   padding: 32px; "
        "   border-radius: 20px; "
        "   margin-bottom: 32px; "
        "   box-shadow: 0 8px 24px rgba(0,0,0,0.15); "
        "   border: 2px solid rgba(255,255,255,0.3); "
        " } "
        " .header-block h1 { "
        "   margin: 0 0 16px 0; "
        "   color: var(--header-text) !important; "
        "   font-size: 36px; "
        "   font-weight: 700; "
        "   text-shadow: 2px 2px 4px rgba(0,0,0,0.3); "
        " } "
        " .header-block p { "
        "   margin: 0 0 8px 0; "
        "   color: var(--header-text) !important; "
        "   font-size: 18px; "
        "   text-shadow: 1px 1px 2px rgba(0,0,0,0.2); "
        " } "
        " .header-block p:last-child { "
        "   margin-bottom: 0; "
        "   font-size: 16px; "
        "   opacity: 0.95; "
        " } "

        # ===== КАРТОЧКИ ОТЧЁТОВ (цветные, полупрозрачные) =====
        " .report-card { "
        "   background: var(--card-bg); "
        "   border: 2px solid var(--card-border); "
        "   border-radius: 16px; "
        "   padding: 24px; "
        "   margin-bottom: 20px; "
        "   cursor: pointer; "
        "   transition: all 0.3s ease; "
        "   backdrop-filter: blur(10px); "
        " } "
        " .report-card:hover { "
        "   transform: translateY(-6px) scale(1.02); "
        "   box-shadow: 0 12px 32px rgba(0,0,0,0.2); "
        "   border-color: var(--accent); "
        " } "
        " .card-icon { "
        "   font-size: 42px; "
        "   margin-bottom: 12px; "
        " } "
        " .card-title { "
        "   font-size: 22px; "
        "   font-weight: 700; "
        "   color: var(--text-primary) !important; "
        "   margin: 0 0 8px 0; "
        " } "
        " .card-description { "
        "   font-size: 14px; "
        "   color: var(--text-secondary) !important; "
        "   margin: 0 0 16px 0; "
        " } "
        " .card-link { "
        "   font-size: 14px; "
        "   font-weight: 600; "
        "   color: var(--accent) !important; "
        " } "

        # ===== КНОПКИ (УСИЛЕННЫЕ СЕЛЕКТОРЫ) =====
        " div[data-testid='stButton'] > button, "
        " div[data-testid='stButton'] > button[kind='primary'], "
        " div[data-testid='stButton'] > button[kind='secondary'], "
        " div[data-testid='stButton'] > button[kind='tertiary'], "
        " div[data-testid='stDownloadButton'] > button, "
        " .stButton > button, "
        " .stButton > button[kind='primary'], "
        " .stButton > button[kind='secondary'], "
        " .stButton > button[kind='tertiary'] { "
        f"   background: {colors['button_bg']} !important; "
        f"   color: {colors['button_text']} !important; "
        "   border: none !important; "
        "   border-radius: 10px !important; "
        "   font-weight: 600 !important; "
        "   font-size: 16px !important; "
        "   transition: all 0.3s ease !important; "
        "   text-shadow: 0 1px 2px rgba(0,0,0,0.3) !important; "
        "   padding: 0.5rem 1rem !important; "
        " } "

        " div[data-testid='stButton'] > button:hover, "
        " div[data-testid='stButton'] > button[kind='primary']:hover, "
        " div[data-testid='stButton'] > button[kind='secondary']:hover, "
        " div[data-testid='stButton'] > button[kind='tertiary']:hover, "
        " div[data-testid='stDownloadButton'] > button:hover, "
        " .stButton > button:hover, "
        " .stButton > button[kind='primary']:hover, "
        " .stButton > button[kind='secondary']:hover, "
        " .stButton > button[kind='tertiary']:hover { "
        "   filter: brightness(1.15) !important; "
        "   transform: translateY(-2px) !important; "
        "   box-shadow: 0 4px 12px rgba(0,0,0,0.25) !important; "
        " } "

        # ===== КОНТЕНТНЫЕ БЛОКИ =====
        " .content-block { "
        "   background: var(--card-bg); "
        "   padding: 24px; "
        "   border-radius: 12px; "
        "   margin-bottom: 24px; "
        "   border: 1px solid var(--card-border); "
        "   backdrop-filter: blur(10px); "
        " } "

        # ===== ТЕКСТ =====
        " h1, h2, h3, h4, h5, h6 { "
        "   color: var(--text-primary) !important; "
        " } "
        " p, label, div[data-testid='stMarkdownContainer'] p, "
        " div[data-testid='stMarkdownContainer'] label { "
        "   color: var(--text-primary) !important; "
        " } "

        # ===== ТАБЛИЦЫ (стандартные) =====
        " .stDataFrame { "
        "   border-radius: 8px; "
        "   overflow: hidden; "
        " } "

        # ===== ЗАГРУЗЧИКИ ФАЙЛОВ =====
        " .stFileUploader { "
        "   background: rgba(255,255,255,0.5); "
        "   padding: 15px; "
        "   border-radius: 10px; "
        "   border: 2px dashed var(--card-border); "
        " } "

        # ===== РАЗДЕЛИТЕЛИ =====
        " hr { "
        "   border: none; "
        "   border-top: 2px solid var(--card-border); "
        "   margin: 24px 0; "
        " } "

        # ===== АНИМАЦИИ =====
        " @keyframes float { "
        "   0%, 100% { transform: translateY(0); } "
        "   50% { transform: translateY(-10px); } "
        " } "
        " @keyframes pulse { "
        "   0%, 100% { transform: scale(1); } "
        "   50% { transform: scale(1.02); } "
        " } "
        " @keyframes fadeIn { "
        "   from { opacity: 0; transform: translateY(20px); } "
        "   to { opacity: 1; transform: translateY(0); } "
        " } "
        " @keyframes scaleIn { "
        "   from { opacity: 0; transform: scale(0.8); } "
        "   to { opacity: 1; transform: scale(1); } "
        " } "

        # ===== КЛАССЫ АНИМАЦИИ =====
        " .fade-in { animation: fadeIn 0.6s ease-out; } "
        " .scale-in { animation: scaleIn 0.4s ease-out; } "

        # ===== СТИЛИ ДЛЯ ЛОГОТИПОВ В ПОДВАЛЕ =====
        " .footer-logo img { "
        f"   opacity: {logo_opacity}; "
        "   transition: opacity 0.3s ease, filter 0.3s ease; "
        "   filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)); "
        " } "
        " .footer-logo img:hover { "
        "   opacity: 1; "
        "   filter: drop-shadow(0 4px 8px rgba(0,0,0,0.4)) brightness(1.1); "
        " } "

        # ===== СТИЛИ ДЛЯ КНОПКИ-ДИНОЗАВРА =====
        " .dino-footer-button { "
        "   text-align: left; "
        "   margin-bottom: 16px; "
        "   padding-left: 8px; "
        " } "
        " .dino-emoji-btn { "
        "   background: transparent !important; "
        "   border: none !important; "
        "   font-size: 32px; "
        "   cursor: pointer; "
        "   padding: 8px 12px; "
        "   transition: all 0.3s ease; "
        "   border-radius: 8px; "
        "   line-height: 1; "
        " } "
        " .dino-emoji-btn:hover { "
        "   transform: scale(1.2) rotate(-10deg); "
        "   background: rgba(255,255,255,0.1) !important; "
        " } "
        " .dino-emoji-btn:active { "
        "   transform: scale(1.1); "
        " } "

        # ===== СТИЛИ ДЛЯ МОДАЛЬНОГО ОКНА =====
        " .dino-modal-overlay { "
        "   display: none; "
        "   position: fixed; "
        "   z-index: 10000; "
        "   left: 0; "
        "   top: 0; "
        "   width: 100%; "
        "   height: 100%; "
        "   overflow: auto; "
        "   background-color: rgba(0, 0, 0, 0.75); "
        "   backdrop-filter: blur(4px); "
        "   animation: fadeIn 0.3s ease-out; "
        " } "
        " .dino-modal-content { "
        "   background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); "
        "   margin: 8% auto; "
        "   padding: 0; "
        "   border-radius: 20px; "
        "   width: 90%; "
        "   max-width: 500px; "
        "   box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6); "
        "   position: relative; "
        "   animation: scaleIn 0.4s ease-out; "
        " } "
        " .dino-modal-close { "
        "   position: absolute; "
        "   right: 20px; "
        "   top: 15px; "
        "   color: white; "
        "   font-size: 36px; "
        "   font-weight: bold; "
        "   cursor: pointer; "
        "   z-index: 10; "
        "   transition: all 0.3s ease; "
        "   width: 40px; "
        "   height: 40px; "
        "   display: flex; "
        "   align-items: center; "
        "   justify-content: center; "
        "   border-radius: 50%; "
        " } "
        " .dino-modal-close:hover { "
        "   color: #FFD700; "
        "   transform: scale(1.2); "
        "   background: rgba(255,255,255,0.1); "
        " } "
        " .dino-gif-container { "
        "   text-align: center; "
        "   padding: 30px 20px 20px 20px; "
        " } "
        " .dino-gif { "
        "   max-width: 100%; "
        "   height: auto; "
        "   border-radius: 15px; "
        "   box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3); "
        " } "
        " .dino-phrase { "
        "   background: rgba(255, 255, 255, 0.95); "
        "   padding: 24px; "
        "   margin: 0 20px 20px 20px; "
        "   border-radius: 12px; "
        "   text-align: center; "
        " } "
        " .dino-phrase p { "
        "   margin: 0; "
        "   font-size: 20px; "
        "   color: #2C3E50; "
        "   font-weight: 600; "
        "   line-height: 1.6; "
        " } "

        # ===== АДАПТИВНОСТЬ ДЛЯ МОБИЛЬНЫХ =====
        " @media (max-width: 768px) { "
        "   .dino-emoji-btn { font-size: 28px; } "
        "   .dino-modal-content { width: 95%; margin: 15% auto; } "
        "   .dino-phrase p { font-size: 18px; } "
        "   .welcome-title { font-size: 28px; } "
        "   .welcome-subtitle { font-size: 16px; } "
        "   .report-card { padding: 16px; } "
        "   .card-title { font-size: 18px; } "
        "   .footer-logo img { max-height: 30px; } "
        "   div[data-testid='stButton'] > button { font-size: 14px !important; } "
        "   .header-block { padding: 20px; } "
        "   .header-block h1 { font-size: 28px; } "
        "   .header-block p { font-size: 16px; } "
        " } "

        "</style>"
    )

    # 4. Эффекты времени суток
    effects_css = get_theme_effect(theme)

    # 5. Праздничные эффекты
    holiday_css = get_holiday_effects(holiday_effects)

    # Выводим всё вместе
    st.markdown(
        base_css + effects_css + holiday_css,
        unsafe_allow_html=True
    )
