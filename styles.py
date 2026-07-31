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
    
    # 3. Базовые стили интерфейса
    base_css = (
        "<style>"
        
        # ===== ПРИНУДИТЕЛЬНАЯ СВЕТЛАЯ ТЕМА =====
        " .stApp { "
        "   background: " + colors['bg_main'] + " !important; "
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
        "   background: " + colors['bg_sidebar'] + " !important; "
        "   border-right: 1px solid " + colors['card_border'] + "; "
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
        "   color: " + colors['text_primary'] + " !important; "
        " } "
        
        # ===== ПРИВЕТСТВЕННЫЙ БЛОК =====
        " .welcome-block { "
        "   background: " + colors['header_bg'] + "; "
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
        "   color: " + colors['header_text'] + " !important; "
        "   margin: 0 0 8px 0; "
        "   text-shadow: 2px 2px 4px rgba(0,0,0,0.2); "
        " } "
        " .welcome-subtitle { "
        "   font-size: 18px; "
        "   color: " + colors['header_text'] + " !important; "
        "   margin: 0 0 16px 0; "
        "   opacity: 0.95; "
        " } "
        " .welcome-hint { "
        "   font-size: 16px; "
        "   color: " + colors['header_text'] + " !important; "
        "   margin: 0; "
        "   opacity: 0.9; "
        " } "
        
        # ===== КАРТОЧКИ ОТЧЁТОВ (цветные, полупрозрачные) =====
        " .report-card { "
        "   background: " + colors['card_bg'] + "; "
        "   border: 2px solid " + colors['card_border'] + "; "
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
        "   border-color: " + colors['accent'] + "; "
        " } "
        " .card-icon { "
        "   font-size: 42px; "
        "   margin-bottom: 12px; "
        " } "
        " .card-title { "
        "   font-size: 22px; "
        "   font-weight: 700; "
        "   color: " + colors['text_primary'] + " !important; "
        "   margin: 0 0 8px 0; "
        " } "
        " .card-description { "
        "   font-size: 14px; "
        "   color: " + colors['text_secondary'] + " !important; "
        "   margin: 0 0 16px 0; "
        " } "
        " .card-link { "
        "   font-size: 14px; "
        "   font-weight: 600; "
        "   color: " + colors['accent'] + " !important; "
        " } "
        
        # ===== КНОПКИ =====
        " .stButton>button { "
        "   background: " + colors['button_bg'] + " !important; "
        "   color: " + colors['button_text'] + " !important; "
        "   border: none !important; "
        "   border-radius: 10px !important; "
        "   font-weight: 600 !important; "
        "   transition: all 0.3s ease !important; "
        " } "
        " .stButton>button:hover { "
        "   filter: brightness(1.1) !important; "
        "   transform: translateY(-2px) !important; "
        "   box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important; "
        " } "
        
        # ===== КОНТЕНТНЫЕ БЛОКИ =====
        " .content-block { "
        "   background: " + colors['card_bg'] + "; "
        "   padding: 24px; "
        "   border-radius: 12px; "
        "   margin-bottom: 24px; "
        "   border: 1px solid " + colors['card_border'] + "; "
        "   backdrop-filter: blur(10px); "
        " } "
        
        # ===== ТЕКСТ =====
        " h1, h2, h3, h4, h5, h6 { "
        "   color: " + colors['text_primary'] + " !important; "
        " } "
        " p, label, div[data-testid='stMarkdownContainer'] p, "
        " div[data-testid='stMarkdownContainer'] label { "
        "   color: " + colors['text_primary'] + " !important; "
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
        "   border: 2px dashed " + colors['card_border'] + "; "
        " } "
        
        # ===== РАЗДЕЛИТЕЛИ =====
        " hr { "
        "   border: none; "
        "   border-top: 2px solid " + colors['card_border'] + "; "
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
        
        # ===== СТИЛИ ДЛЯ КНОПКИ-ДИНОЗАВРА В ПОДВАЛЕ =====
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
