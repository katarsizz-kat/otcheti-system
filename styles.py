"""Стили интерфейса приложения (дизайн-система v2.2, Sage & Sandstone).

Архитектура:
- Один общий CSS-билдер (_BASE_CSS) + лёгкие дополнения режимов:
  * apply_theme        -> full (главная страница: анимации, эффекты);
  * apply_subtle_theme -> lite (страницы отчётов: без фоновых эффектов,
    спокойнее тени, но тот же визуальный язык).
- Все цвета — из config/theme.py (базы light/dark), никаких хардкодов.
- Кнопки: primary / secondary / ghost (download = primary).
  Текст кнопок крашен через внутренние span/p/div (color: inherit).
- Вкладки: pill-tabs. Метрики, алерты, таблицы, uploader — на переменных.
- Модалки (stDialog/stModal) и инпуты/селекты принудительно темизированы.
- Доступность: focus-visible, prefers-reduced-motion, контраст AA.
- Шарики успеха подключаются автоматически в обоих режимах.
- v2.2: override темы живёт в query_params И дублируется в session_state,
  поэтому выбор сохраняется при переходах между страницами.
"""

import streamlit as st
from typing import Optional

from config.theme import (
    DESIGN_TOKENS,
    get_base_colors,
    resolve_mode,
)
from config.effects import (
    consume_pending_balloons,
    get_holiday_effects,
    get_theme_effect,
)

# =============================================================================
# СЛУЖЕБНОЕ
# =============================================================================

def _get_override() -> Optional[str]:
    """Ручной выбор темы пользователем.

    Приоритет источников:
    1) st.query_params["theme"] — полные перезагрузки, закладки;
    2) st.session_state["theme_override"] — переживает внутренние
       переходы между страницами, где query-параметр теряется.

    Найденное в URL значение запоминаем в session_state.
    """
    try:
        value = st.query_params.get("theme")
    except Exception:
        value = None
    if value in ("light", "dark"):
        st.session_state["theme_override"] = value
        return value
    value = st.session_state.get("theme_override")
    return value if value in ("light", "dark") else None


def _hex_to_rgba(value: str, alpha: float) -> str:
    """#RRGGBB -> rgba(r, g, b, alpha). Фолбэк — исходная строка."""
    try:
        v = value.strip().lstrip("#")
        if len(v) == 3:
            v = "".join(ch * 2 for ch in v)
        r, g, b = (int(v[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha})"
    except Exception:
        return value


def _css_variables(colors: dict) -> str:
    """CSS-переменные: палитра + производные + дизайн-токены."""
    t = DESIGN_TOKENS
    dark = bool(colors.get("is_dark"))
    hover_bg = "rgba(236,234,229,0.08)" if dark else "rgba(45,58,46,0.06)"
    active_bg = "rgba(236,234,229,0.14)" if dark else "rgba(45,58,46,0.10)"
    return (
        ":root { "
        f"--bg-main: {colors['bg_main']}; "
        f"--bg-sidebar: {colors['bg_sidebar']}; "
        f"--header-bg: {colors['header_bg']}; "
        f"--header-text: {colors['header_text']}; "
        f"--text-primary: {colors['text_primary']}; "
        f"--text-secondary: {colors['text_secondary']}; "
        f"--card-bg: {colors['card_bg']}; "
        f"--card-border: {colors['card_border']}; "
        f"--accent: {colors['accent']}; "
        f"--accent-strong: {colors['accent_strong']}; "
        f"--button-bg: {colors['button_bg']}; "
        f"--button-text: {colors['button_text']}; "
        f"--button-secondary-bg: {colors['button_secondary_bg']}; "
        f"--button-secondary-text: {colors['button_secondary_text']}; "
        f"--button-secondary-border: {colors['button_secondary_border']}; "
        f"--success: {colors['success']}; "
        f"--warning: {colors['warning']}; "
        f"--error: {colors['error']}; "
        f"--info: {colors['info']}; "
        f"--success-bg: {_hex_to_rgba(colors['success'], 0.14)}; "
        f"--warning-bg: {_hex_to_rgba(colors['warning'], 0.16)}; "
        f"--error-bg: {_hex_to_rgba(colors['error'], 0.14)}; "
        f"--info-bg: {_hex_to_rgba(colors['info'], 0.14)}; "
        f"--shadow-sm: {colors['shadow_sm']}; "
        f"--shadow-md: {colors['shadow_md']}; "
        f"--focus-ring: {colors['focus_ring']}; "
        f"--overlay: {colors['overlay']}; "
        f"--logo-opacity: {colors['logo_opacity']}; "
        f"--hover-bg: {hover_bg}; "
        f"--active-bg: {active_bg}; "
        f"--radius-sm: {t['radius_sm']}; "
        f"--radius-md: {t['radius_md']}; "
        f"--radius-lg: {t['radius_lg']}; "
        f"--font-stack: {t['font_stack']}; "
        f"--type-xs: {t['type_xs']}; "
        f"--type-sm: {t['type_sm']}; "
        f"--type-md: {t['type_md']}; "
        f"--type-lg: {t['type_lg']}; "
        f"--type-xl: {t['type_xl']}; "
        f"--type-xxl: {t['type_xxl']}; "
        f"--motion-fast: {t['motion_fast']}; "
        f"--motion-base: {t['motion_base']}; "
        f"--motion-slow: {t['motion_slow']}; "
        "} "
    )

# =============================================================================
# ОБЩАЯ БАЗА (full и lite)
# =============================================================================

_BASE_CSS = (
    "<style>"

    # ===== ПРИЛОЖЕНИЕ И ВЕРХНЯЯ ПАНЕЛЬ =====
    " .stApp { "
    "   background: var(--bg-main) !important; "
    "   color: var(--text-primary); "
    "   font-family: var(--font-stack); "
    "   min-height: 100vh; "
    " } "
    " header[data-testid='stHeader'], "
    " .stApp [data-testid='stHeader'] { "
    "   background: transparent !important; "
    "   border-bottom: none !important; "
    " } "

    # ===== БОКОВАЯ ПАНЕЛЬ (без opacity — текст всегда чёткий) =====
    " section[data-testid='stSidebar'] { "
    "   background: var(--bg-sidebar) !important; "
    "   border-right: 1px solid var(--card-border); "
    " } "
    " section[data-testid='stSidebar'] > div { "
    "   background: transparent !important; "
    " } "
    " section[data-testid='stSidebar'] p, "
    " section[data-testid='stSidebar'] h1, "
    " section[data-testid='stSidebar'] h2, "
    " section[data-testid='stSidebar'] h3, "
    " section[data-testid='stSidebar'] label, "
    " section[data-testid='stSidebar'] .stMarkdown { "
    "   color: var(--text-primary) !important; "
    " } "

    # ===== НАВИГАЦИЯ В САЙДБАРЕ =====
    " div[data-testid='stSidebarNav'] { padding: 8px 0 !important; } "
    " div[data-testid='stSidebarNav'] a, "
    " section[data-testid='stSidebar'] nav a { "
    "   color: var(--text-primary) !important; "
    "   font-size: var(--type-md) !important; "
    "   font-weight: 600 !important; "
    "   padding: 10px 14px !important; "
    "   margin: 2px 8px !important; "
    "   border-radius: var(--radius-sm) !important; "
    "   border-left: 3px solid transparent !important; "
    "   transition: background-color var(--motion-fast) ease, "
    "     border-color var(--motion-fast) ease !important; "
    "   display: block !important; "
    "   text-decoration: none !important; "
    " } "
    " div[data-testid='stSidebarNav'] a:hover, "
    " section[data-testid='stSidebar'] nav a:hover { "
    "   background: var(--hover-bg) !important; "
    " } "
    " div[data-testid='stSidebarNav'] a[aria-current='page'], "
    " section[data-testid='stSidebar'] nav a[aria-current='page'] { "
    "   background: var(--active-bg) !important; "
    "   border-left-color: var(--accent-strong) !important; "
    " } "

    # ===== ТЕКСТ =====
    " h1, h2, h3, h4, h5, h6 { "
    "   color: var(--text-primary) !important; "
    "   text-shadow: none !important; "
    " } "
    " p, label, "
    " div[data-testid='stMarkdownContainer'] p, "
    " div[data-testid='stMarkdownContainer'] label { "
    "   color: var(--text-primary) !important; "
    "   line-height: 1.6 !important; "
    " } "
    " .stCaption, small { "
    "   color: var(--text-secondary) !important; "
    " } "

    # ===== ИНПУТЫ, СЕЛЕКТЫ, ТЕКСТ-АРЕИ (на переменных) =====
    " input, textarea, "
    " div[data-baseweb='select'] > div, "
    " div[data-baseweb='input'] > input, "
    " div[data-baseweb='textarea'] > textarea { "
    "   background-color: var(--card-bg) !important; "
    "   color: var(--text-primary) !important; "
    "   border-color: var(--card-border) !important; "
    " } "
    " div[data-baseweb='menu'], ul[role='listbox'] { "
    "   background-color: var(--card-bg) !important; "
    "   color: var(--text-primary) !important; "
    " } "
    " input::placeholder, textarea::placeholder { "
    "   color: var(--text-secondary) !important; "
    " } "

    # ===== МОДАЛКИ (динозавр и любые st.dialog) на переменных =====
    " div[data-testid='stModal'], div[data-testid='stDialog'] { "
    "   background-color: var(--card-bg) !important; "
    "   color: var(--text-primary) !important; "
    "   border: 1px solid var(--card-border) !important; "
    "   border-radius: var(--radius-lg) !important; "
    " } "
    " div[data-testid='stDialog'] h1, "
    " div[data-testid='stDialog'] h2, "
    " div[data-testid='stDialog'] h3, "
    " div[data-testid='stDialog'] p, "
    " div[data-testid='stDialog'] span, "
    " div[data-testid='stDialog'] label { "
    "   color: var(--text-primary) !important; "
    " } "

    # ===== ПРИВЕТСТВЕННЫЙ БЛОК (главная) =====
    " .welcome-block { "
    "   background: var(--header-bg); "
    "   padding: 32px; "
    "   border-radius: var(--radius-lg); "
    "   margin-bottom: 28px; "
    "   box-shadow: var(--shadow-sm); "
    "   border: 1px solid var(--card-border); "
    " } "
    " .welcome-icon { "
    "   font-size: 48px; "
    "   margin-bottom: 12px; "
    "   display: inline-block; "
    " } "
    " .welcome-title { "
    "   font-size: 36px; "
    "   font-weight: 700; "
    "   color: var(--header-text) !important; "
    "   margin: 0 0 8px 0; "
    " } "
    " .welcome-subtitle { "
    "   font-size: 18px; "
    "   color: var(--header-text) !important; "
    "   margin: 0 0 12px 0; "
    "   opacity: 0.92; "
    " } "
    " .welcome-hint { "
    "   font-size: 15px; "
    "   color: var(--header-text) !important; "
    "   margin: 0; "
    "   opacity: 0.85; "
    " } "

    # ===== HEADER-BLOCK (страницы отчётов, -2..3px по договорённости) =====
    " .header-block { "
    "   background: var(--header-bg); "
    "   padding: 29px; "
    "   border-radius: var(--radius-lg); "
    "   margin-bottom: 28px; "
    "   box-shadow: var(--shadow-sm); "
    "   border: 1px solid var(--card-border); "
    " } "
    " .header-block h1 { "
    "   margin: 0 0 14px 0; "
    "   color: var(--header-text) !important; "
    "   font-size: var(--type-xxl); "
    "   font-weight: 700; "
    " } "
    " .header-block p { "
    "   margin: 0 0 8px 0; "
    "   color: var(--header-text) !important; "
    "   font-size: 17px; "
    "   font-weight: 500; "
    "   opacity: 0.92; "
    " } "
    " .header-block p:last-child { margin-bottom: 0; font-size: 15px; } "

    # ===== КАРТОЧКИ И КОНТЕНТНЫЕ БЛОКИ (без blur) =====
    " .report-card, .content-block, .universal-card { "
    "   background: var(--card-bg); "
    "   border: 1px solid var(--card-border); "
    "   border-radius: var(--radius-md); "
    "   box-shadow: var(--shadow-sm); "
    " } "
    " .report-card { "
    "   padding: 22px; "
    "   margin-bottom: 20px; "
    "   cursor: pointer; "
    "   transition: transform var(--motion-base) ease, "
    "     box-shadow var(--motion-base) ease, "
    "     border-color var(--motion-base) ease; "
    " } "
    " .report-card:hover { "
    "   transform: translateY(-3px); "
    "   box-shadow: var(--shadow-md); "
    "   border-color: var(--accent); "
    " } "
    " .content-block { padding: 24px; margin-bottom: 24px; } "
    " .card-icon { font-size: 40px; margin-bottom: 12px; } "
    " .card-title { "
    "   font-size: 21px; "
    "   font-weight: 700; "
    "   color: var(--text-primary) !important; "
    "   margin: 0 0 8px 0; "
    " } "
    " .card-description { "
    "   font-size: var(--type-sm); "
    "   color: var(--text-secondary) !important; "
    "   margin: 0 0 14px 0; "
    " } "
    " .card-link { "
    "   font-size: var(--type-sm); "
    "   font-weight: 600; "
    "   color: var(--accent-strong) !important; "
    " } "

    # ===== КНОПКИ: БАЗА =====
    " div[data-testid='stButton'] > button, "
    " div[data-testid='stDownloadButton'] > button { "
    "   border-radius: var(--radius-sm) !important; "
    "   font-weight: 600 !important; "
    "   font-size: var(--type-md) !important; "
    "   padding: 0.5rem 1rem !important; "
    "   text-shadow: none !important; "
    "   transition: transform var(--motion-fast) ease, "
    "     box-shadow var(--motion-fast) ease, "
    "     filter var(--motion-fast) ease, "
    "     background-color var(--motion-fast) ease, "
    "     border-color var(--motion-fast) ease !important; "
    " } "
    # ----- текст кнопок доходит до внутренних элементов -----
    " div[data-testid='stButton'] > button span, "
    " div[data-testid='stButton'] > button p, "
    " div[data-testid='stButton'] > button div, "
    " div[data-testid='stDownloadButton'] > button span, "
    " div[data-testid='stDownloadButton'] > button p, "
    " div[data-testid='stDownloadButton'] > button div { "
    "   color: inherit !important; "
    "   text-shadow: none !important; "
    " } "
    # ----- primary + download -----
    " div[data-testid='stButton'] > button[kind='primary'], "
    " div[data-testid='stDownloadButton'] > button { "
    "   background: var(--button-bg) !important; "
    "   color: var(--button-text) !important; "
    "   border: 1px solid transparent !important; "
    "   box-shadow: var(--shadow-sm) !important; "
    " } "
    # ----- secondary (по умолчанию) -----
    " div[data-testid='stButton'] > button[kind='secondary'] { "
    "   background: var(--button-secondary-bg) !important; "
    "   color: var(--button-secondary-text) !important; "
    "   border: 1px solid var(--button-secondary-border) !important; "
    "   box-shadow: none !important; "
    " } "
    # ----- ghost / tertiary -----
    " div[data-testid='stButton'] > button[kind='tertiary'] { "
    "   background: transparent !important; "
    "   color: var(--accent-strong) !important; "
    "   border: 1px solid transparent !important; "
    "   box-shadow: none !important; "
    " } "
    # ----- hover / active / focus -----
    " div[data-testid='stButton'] > button:hover, "
    " div[data-testid='stDownloadButton'] > button:hover { "
    "   filter: brightness(1.05) !important; "
    "   transform: translateY(-2px) !important; "
    "   box-shadow: var(--shadow-md) !important; "
    " } "
    " div[data-testid='stButton'] > button:active, "
    " div[data-testid='stDownloadButton'] > button:active { "
    "   transform: translateY(0) !important; "
    " } "
    " div[data-testid='stButton'] > button:focus-visible, "
    " div[data-testid='stDownloadButton'] > button:focus-visible { "
    "   outline: 2px solid var(--accent-strong) !important; "
    "   outline-offset: 2px !important; "
    "   box-shadow: 0 0 0 4px var(--focus-ring) !important; "
    " } "

    # ===== ВКЛАДКИ (pill-tabs) =====
    " div[data-testid='stTabs'] { margin-bottom: 24px; } "
    " div[data-testid='stTabs'] [role='tablist'] { "
    "   gap: 8px !important; "
    "   border-bottom: none !important; "
    "   flex-wrap: wrap !important; "
    " } "
    " div[data-testid='stTabs'] button { "
    "   background: var(--hover-bg) !important; "
    "   color: var(--text-secondary) !important; "
    "   border: 1px solid transparent !important; "
    "   border-radius: 999px !important; "
    "   padding: 8px 18px !important; "
    "   font-weight: 600 !important; "
    "   transition: background-color var(--motion-fast) ease, "
    "     color var(--motion-fast) ease !important; "
    " } "
    " div[data-testid='stTabs'] button span { color: inherit !important; } "
    " div[data-testid='stTabs'] button:hover { "
    "   background: var(--active-bg) !important; "
    "   color: var(--text-primary) !important; "
    " } "
    " div[data-testid='stTabs'] button[aria-selected='true'] { "
    "   background: var(--button-bg) !important; "
    "   color: var(--button-text) !important; "
    " } "

    # ===== МЕТРИКИ =====
    " div[data-testid='stMetric'] { "
    "   background: var(--card-bg) !important; "
    "   border: 1px solid var(--card-border) !important; "
    "   border-radius: var(--radius-md) !important; "
    "   padding: 18px !important; "
    "   box-shadow: var(--shadow-sm) !important; "
    " } "
    " div[data-testid='stMetric'] label { "
    "   color: var(--text-secondary) !important; "
    "   font-size: var(--type-xs) !important; "
    "   font-weight: 700 !important; "
    "   text-transform: uppercase !important; "
    "   letter-spacing: 0.05em !important; "
    " } "
    " div[data-testid='stMetric'] div[data-testid='stMetricValue'] { "
    "   color: var(--text-primary) !important; "
    "   font-size: 30px !important; "
    "   font-weight: 800 !important; "
    " } "

    # ===== ТАБЛИЦЫ И ГРАФИКИ =====
    " div[data-testid='stDataFrame'], .stTable { "
    "   border-radius: var(--radius-md) !important; "
    "   border: 1px solid var(--card-border) !important; "
    "   overflow: hidden !important; "
    "   box-shadow: var(--shadow-sm); "
    " } "
    " div[data-testid='stPlotlyChart'], "
    " div[data-testid='stAltairChart'], "
    " .stPlotlyChart, .stAltairChart, .stBokehChart { "
    "   background: var(--card-bg) !important; "
    "   border: 1px solid var(--card-border) !important; "
    "   border-radius: var(--radius-md) !important; "
    "   padding: 12px !important; "
    " } "

    # ===== АЛЕРТЫ =====
    " div[data-testid='stAlert'] { "
    "   border-radius: var(--radius-md) !important; "
    "   border: 1px solid transparent !important; "
    " } "
    " .stSuccess, div[data-testid='stAlert'].stSuccess { "
    "   background: var(--success-bg) !important; "
    "   border-color: var(--success) !important; "
    " } "
    " .stInfo, div[data-testid='stAlert'].stInfo { "
    "   background: var(--info-bg) !important; "
    "   border-color: var(--info) !important; "
    " } "
    " .stWarning, div[data-testid='stAlert'].stWarning { "
    "   background: var(--warning-bg) !important; "
    "   border-color: var(--warning) !important; "
    " } "
    " .stError, div[data-testid='stAlert'].stError { "
    "   background: var(--error-bg) !important; "
    "   border-color: var(--error) !important; "
    " } "

    # ===== ЗАГРУЗЧИКИ ФАЙЛОВ =====
    " div[data-testid='stFileUploader'], .stFileUploader { "
    "   background: var(--card-bg) !important; "
    "   border: 1.5px dashed var(--card-border) !important; "
    "   border-radius: var(--radius-md) !important; "
    "   padding: 16px !important; "
    "   transition: border-color var(--motion-fast) ease !important; "
    " } "
    " div[data-testid='stFileUploader']:hover, .stFileUploader:hover { "
    "   border-color: var(--accent) !important; "
    " } "
    " .stFileUploader small { color: var(--text-secondary) !important; } "

    # ===== РАЗДЕЛИТЕЛИ =====
    " hr { "
    "   border: none !important; "
    "   border-top: 1px solid var(--card-border) !important; "
    "   margin: 24px 0 !important; "
    " } "

    # ===== ЛОГОТИПЫ В ПОДВАЛЕ =====
    " .footer-logo img { "
    "   opacity: var(--logo-opacity); "
    "   transition: opacity var(--motion-slow) ease; "
    " } "
    " .footer-logo img:hover { opacity: 1; } "

    # ===== ДИНОЗАВР (в цветах темы) =====
    " .dino-footer-button { text-align: left; margin-bottom: 12px; } "
    " .dino-emoji-btn { "
    "   background: transparent !important; "
    "   border: none !important; "
    "   font-size: 30px; "
    "   cursor: pointer; "
    "   padding: 8px 10px; "
    "   border-radius: var(--radius-sm); "
    "   line-height: 1; "
    "   transition: transform var(--motion-fast) ease, "
    "     background-color var(--motion-fast) ease; "
    " } "
    " .dino-emoji-btn:hover { "
    "   transform: scale(1.12) rotate(-8deg); "
    "   background: var(--hover-bg) !important; "
    " } "
    " .dino-modal-overlay { "
    "   display: none; "
    "   position: fixed; "
    "   z-index: 10000; "
    "   inset: 0; "
    "   overflow: auto; "
    "   background-color: var(--overlay); "
    "   animation: fadeIn 0.25s ease-out; "
    " } "
    " .dino-modal-content { "
    "   background: var(--card-bg); "
    "   border: 1px solid var(--card-border); "
    "   margin: 8% auto; "
    "   padding: 0; "
    "   border-radius: var(--radius-lg); "
    "   width: 90%; "
    "   max-width: 500px; "
    "   box-shadow: var(--shadow-md); "
    "   position: relative; "
    "   animation: scaleIn 0.25s ease-out; "
    " } "
    " .dino-modal-close { "
    "   position: absolute; "
    "   right: 16px; "
    "   top: 12px; "
    "   color: var(--text-primary); "
    "   font-size: 30px; "
    "   font-weight: bold; "
    "   cursor: pointer; "
    "   z-index: 10; "
    "   width: 38px; "
    "   height: 38px; "
    "   display: flex; "
    "   align-items: center; "
    "   justify-content: center; "
    "   border-radius: 50%; "
    "   transition: background-color var(--motion-fast) ease; "
    " } "
    " .dino-modal-close:hover { background: var(--hover-bg); } "
    " .dino-gif-container { text-align: center; padding: 28px 20px 16px 20px; } "
    " .dino-gif { "
    "   max-width: 100%; "
    "   height: auto; "
    "   border-radius: var(--radius-md); "
    "   border: 1px solid var(--card-border); "
    " } "
    " .dino-phrase { "
    "   background: var(--bg-main); "
    "   padding: 20px; "
    "   margin: 0 20px 20px 20px; "
    "   border-radius: var(--radius-md); "
    "   text-align: center; "
    " } "
    " .dino-phrase p { "
    "   margin: 0; "
    "   font-size: 19px; "
    "   color: var(--text-primary) !important; "
    "   font-weight: 600; "
    "   line-height: 1.5; "
    " } "

    # ===== АНИМАЦИИ (однострочные keyframes) =====
    " @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } } "
    " @keyframes fadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } } "
    " @keyframes scaleIn { from { opacity: 0; transform: scale(0.92); } to { opacity: 1; transform: scale(1); } } "
    " .fade-in { animation: fadeIn 0.4s ease-out; } "
    " .scale-in { animation: scaleIn 0.3s ease-out; } "

    # ===== ДОСТУПНОСТЬ: REDUCED MOTION =====
    " @media (prefers-reduced-motion: reduce) { "
    "   *, *::before, *::after { "
    "     animation-duration: 0.01ms !important; "
    "     animation-iteration-count: 1 !important; "
    "     transition-duration: 0.01ms !important; "
    "   } "
    " } "

    # ===== АДАПТИВНОСТЬ =====
    " @media (max-width: 768px) { "
    "   .welcome-block, .header-block { padding: 20px; } "
    "   .welcome-title { font-size: 28px; } "
    "   .header-block h1 { font-size: 26px; } "
    "   .report-card, .content-block { padding: 16px; } "
    "   .card-title { font-size: 18px; } "
    "   div[data-testid='stButton'] > button { font-size: 14px !important; } "
    "   div[data-testid='stTabs'] button { padding: 6px 14px !important; font-size: 14px !important; } "
    "   div[data-testid='stSidebarNav'] a, "
    "   section[data-testid='stSidebar'] nav a { font-size: 14px !important; } "
    "   .dino-emoji-btn { font-size: 26px; } "
    "   .dino-modal-content { width: 95%; margin: 15% auto; } "
    " } "

    "</style>"
)

# =============================================================================
# ДОПОЛНЕНИЯ РЕЖИМОВ
# =============================================================================

_FULL_CSS = (
    "<style>"
    " .welcome-icon { animation: float 3.5s ease-in-out infinite; } "
    " .welcome-block { box-shadow: var(--shadow-md); } "
    "</style>"
)

_LITE_CSS = (
    "<style>"
    " :root { "
    "   --shadow-md: var(--shadow-sm); "
    " } "
    " .welcome-icon { animation: none !important; } "
    " .report-card:hover { transform: none; } "
    "</style>"
)

# =============================================================================
# ПУБЛИЧНЫЕ ФУНКЦИИ
# =============================================================================

def apply_theme(theme: str, holiday_effects: list = None):
    """Полный режим для главной страницы."""
    if holiday_effects is None:
        holiday_effects = []

    override = _get_override()
    mode = resolve_mode(override, theme)
    colors = get_base_colors(mode)

    css = "<style>" + _css_variables(colors) + "</style>" + _BASE_CSS + _FULL_CSS

    effect_theme = theme if override is None else ("day" if mode == "light" else "night")

    effects_css = get_theme_effect(effect_theme)
    holiday_css = get_holiday_effects(holiday_effects)
    balloons = consume_pending_balloons()

    st.markdown(
        css + effects_css + holiday_css + balloons,
        unsafe_allow_html=True,
    )


def apply_subtle_theme(theme: str, holiday_effects: list = None):
    """Лёгкий режим для страниц отчётов."""
    override = _get_override()
    mode = resolve_mode(override, theme)
    colors = get_base_colors(mode)

    css = "<style>" + _css_variables(colors) + "</style>" + _BASE_CSS + _LITE_CSS
    balloons = consume_pending_balloons()

    st.markdown(css + balloons, unsafe_allow_html=True)


def apply_universal_report_styles():
    """Стили универсального отчёта (pages/10_MINI.py) — на переменных."""
    st.markdown(
        "<style>"
        " .universal-card { "
        "   background: var(--card-bg, #FFFFFF); "
        "   border: 1px solid var(--card-border, #D9D4CB); "
        "   border-radius: var(--radius-md, 12px); "
        "   padding: 24px 28px; "
        "   margin-bottom: 24px; "
        "   box-shadow: var(--shadow-sm); "
        " } "
        " .universal-card h3 { margin: 0 0 12px 0; color: var(--text-primary); } "
        " .universal-card h4 { margin: 16px 0 8px 0; color: var(--text-primary); } "
        " .universal-card p { margin: 0 0 12px 0; } "
        " .universal-card ul { margin: 0 0 8px 0; padding-left: 22px; } "
        " .universal-card li { margin-bottom: 6px; } "
        " .universal-card code { "
        "   background: var(--hover-bg, rgba(0,0,0,0.06)); "
        "   color: var(--text-primary); "
        "   padding: 2px 6px; "
        "   border-radius: 6px; "
        " } "
        " [data-testid='stTextArea'] textarea { "
        "   background: var(--card-bg, #FFFFFF) !important; "
        "   color: var(--text-primary, #2D3A2E) !important; "
        "   border: 1px solid var(--card-border, #D9D4CB) !important; "
        "   border-radius: var(--radius-sm, 8px) !important; "
        "   padding: 12px !important; "
        "   font-size: 14px !important; "
        "   min-height: 300px !important; "
        " } "
        " [data-testid='stTextArea'] textarea:focus { "
        "   border-color: var(--accent-strong, #557052) !important; "
        "   box-shadow: 0 0 0 3px var(--focus-ring, rgba(85,112,82,0.35)) !important; "
        "   outline: none !important; "
        " } "
        " [data-testid='stTextArea'] textarea::placeholder { "
        "   color: var(--text-secondary, #5D6A5C) !important; "
        "   font-style: italic; "
        "   opacity: 0.8; "
        " } "
        " [data-testid='stTextArea'] label { "
        "   font-weight: 600; "
        "   color: var(--text-primary, #2D3A2E); "
        "   margin-bottom: 8px; "
        " } "
        "</style>",
        unsafe_allow_html=True,
    )


def get_os_styles() -> str:
    """Дополнения для страницы ОС поверх apply_subtle_theme."""
    return (
        "<style>"
        " .stCaption { "
        "   font-size: var(--type-sm) !important; "
        "   color: var(--text-secondary) !important; "
        "   font-style: italic !important; "
        " } "
        " div[data-testid='stPlotlyChart'] { padding: 16px !important; } "
        " div[data-testid='stMetric'] div[data-testid='stMetricValue'] { "
        "   font-size: 32px !important; "
        " } "
        " div[data-testid='stTabs'] { margin-bottom: 28px !important; } "
        "</style>"
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "apply_theme",
    "apply_subtle_theme",
    "apply_universal_report_styles",
    "get_os_styles",
]