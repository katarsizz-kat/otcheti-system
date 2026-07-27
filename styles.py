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
        "@keyframes mascotIdle { 0%, 100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-10px) rotate(3deg); } }"
        "@keyframes mascotWave { 0%, 100% { transform: rotate(0deg); } 25% { transform: rotate(-20deg); } 75% { transform: rotate(20deg); } }"
        ".fade-in { animation: fadeIn 0.6s ease-out; }"
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
