"""Стили интерфейса приложения."""
import streamlit as st
from config.theme import get_theme_colors
from config.effects import get_theme_effect, get_holiday_effects

def apply_theme(theme: str, holiday_effects: list = None):
    """
    Применяет тему и эффекты к приложению.
    Этапы:
     1. Загрузка цветов темы
     2. Загрузка базовых стилей интерфейса
     3. Подключение эффектов времени суток
     4. Подключение праздничных эффектов
    """
    if holiday_effects is None:
        holiday_effects = []
    
    # 1. Загрузка цветов темы
    colors = get_theme_colors(theme)
    
    # 2. Базовые стили интерфейса
    base_css = (
        "<style>"
        ".stApp { background: " + colors['bg_main'] + " !important; min-height: 100vh; }"
        "section[data-testid='stSidebar'] { background: " + colors['bg_sidebar'] + " !important; border-right: 1px solid " + colors['card_border'] + "; }"
        "section[data-testid='stSidebar'] > div { background: transparent !important; }"
        "section[data-testid='stSidebar'] p, section[data-testid='stSidebar'] h1, section[data-testid='stSidebar'] .stMarkdown { color: " + colors['text_primary'] + " !important; }"
        "header { background: transparent !important; }"
        ".welcome-block { background: " + colors['header_bg'] + "; padding: 32px; border-radius: 20px; margin-bottom: 32px; box-shadow: 0 8px 24px rgba(0,0,0,0.15); border: 2px solid rgba(255,255,255,0.2); }"
        ".welcome-icon { font-size: 48px; margin-bottom: 12px; display: inline-block; animation: float 3s ease-in-out infinite; }"
        ".welcome-title { font-size: 36px; font-weight: 700; color: " + colors['header_text'] + " !important; margin: 0 0 8px 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }"
        ".welcome-subtitle { font-size: 18px; color: " + colors['header_text'] + " !important; margin: 0 0 16px 0; opacity: 0.95; }"
        ".welcome-hint { font-size: 16px; color: " + colors['header_text'] + " !important; margin: 0; opacity: 0.9; }"
        ".report-card { background: " + colors['card_bg'] + "; border: 2px solid " + colors['card_border'] + "; border-radius: 16px; padding: 24px; margin-bottom: 20px; cursor: pointer; transition: all 0.3s ease; }"
        ".report-card:hover { transform: translateY(-6px) scale(1.02); box-shadow: 0 12px 32px rgba(0,0,0,0.2); border-color: " + colors['accent'] + "; }"
        ".card-icon { font-size: 42px; margin-bottom: 12px; }"
        ".card-title { font-size: 22px; font-weight: 700; color: " + colors['text_primary'] + " !important; margin: 0 0 8px 0; }"
        ".card-description { font-size: 14px; color: " + colors['text_secondary'] + " !important; margin: 0 0 16px 0; }"
        ".card-link { font-size: 14px; font-weight: 600; color: " + colors['accent'] + " !important; }"
        ".stButton>button { background: " + colors['button_bg'] + " !important; color: " + colors['button_text'] + " !important; border: none !important; border-radius: 10px !important; font-weight: 600 !important; }"
        ".content-block { background: " + colors['card_bg'] + "; padding: 24px; border-radius: 12px; margin-bottom: 24px; border: 1px solid " + colors['card_border'] + "; }"
        "h1, h2, h3, h4, h5, h6, p, label, div[data-testid='stMarkdownContainer'] p { color: " + colors['text_primary'] + " !important; }"
        "button[data-testid='stBaseButton-secondary'] { background: linear-gradient(135deg, #2980B9 0%, #1F618D 100%) !important; border: none !important; border-radius: 16px !important; padding: 24px 40px !important; margin-bottom: 24px !important; color: #FFFFFF !important; font-size: 32px !important; font-weight: 700 !important; text-align: center !important; white-space: pre-line !important; line-height: 1.6 !important; animation: pulse 2s ease-in-out infinite !important; cursor: pointer !important; width: 50% !important; max-width: 600px !important; margin-left: auto !important; margin-right: auto !important; display: block !important; }"
        "button[data-testid='stBaseButton-secondary']:hover { transform: scale(1.02) !important; box-shadow: 0 8px 24px rgba(41, 128, 185, 0.4) !important; }"
        "@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }"
        "@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.02); } }"
        "@keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }"
        "@keyframes scaleIn { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }"
        "@keyframes mascotIdle { 0%, 100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-10px) rotate(3deg); } }"
        "@keyframes mascotWave { 0%, 100% { transform: rotate(0deg); } 25% { transform: rotate(-20deg); } 75% { transform: rotate(20deg); } }"
        ".fade-in { animation: fadeIn 0.6s ease-out; }"
        
        # Стили для кнопки-динозавра в подвале (только эмодзи, без фона)
        ".dino-footer-button { text-align: left; margin-bottom: 16px; padding-left: 8px; }"
        ".dino-emoji-btn { background: none !important; border: none !important; font-size: 32px; cursor: pointer; padding: 8px 12px; transition: all 0.3s ease; border-radius: 8px; line-height: 1; }"
        ".dino-emoji-btn:hover { transform: scale(1.2) rotate(-10deg); background: rgba(255,255,255,0.1) !important; }"
        ".dino-emoji-btn:active { transform: scale(1.1); }"
        
        # Стили для модального окна
        ".dino-modal { display: none; position: fixed; z-index: 10000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0, 0, 0, 0.75); backdrop-filter: blur(4px); animation: fadeIn 0.3s ease-out; }"
        ".dino-modal-content { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 8% auto; padding: 0; border-radius: 20px; width: 90%; max-width: 500px; box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6); position: relative; animation: scaleIn 0.4s ease-out; }"
        ".dino-modal-close { position: absolute; right: 20px; top: 15px; color: white; font-size: 36px; font-weight: bold; cursor: pointer; z-index: 10; transition: all 0.3s ease; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 50%; }"
        ".dino-modal-close:hover { color: #FFD700; transform: scale(1.2); background: rgba(255,255,255,0.1); }"
        ".dino-gif-container { text-align: center; padding: 30px 20px 20px 20px; }"
        ".dino-gif { max-width: 100%; height: auto; border-radius: 15px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3); }"
        ".dino-phrase { background: rgba(255, 255, 255, 0.95); padding: 24px; margin: 0 20px 20px 20px; border-radius: 12px; text-align: center; }"
        ".dino-phrase p { margin: 0; font-size: 20px; color: #2C3E50; font-weight: 600; line-height: 1.6; }"
        
        # Адаптивность для мобильных
        "@media (max-width: 768px) { .dino-emoji-btn { font-size: 28px; } .dino-modal-content { width: 95%; margin: 15% auto; } .dino-phrase p { font-size: 18px; } }"
        
        "</style>"
    )
    
    # 3. Эффекты времени суток
    effects_css = get_theme_effect(theme)
    
    # 4. Праздничные эффекты
    holiday_css = get_holiday_effects(holiday_effects)
    
    # Выводим всё вместе
    st.markdown(
        base_css + effects_css + holiday_css,
        unsafe_allow_html=True
    )
