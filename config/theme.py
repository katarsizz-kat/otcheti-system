"""Цветовые темы приложения.

Архитектура v2.0 (дизайн-система "Sage & Sandstone"):

1. Две базовые палитры:
   - "light" (Вариант A, Premium Light) — утро и день;
   - "dark"  (Вариант B) — вечер и ночь.

2. Старые имена тем (morning, day, evening, night и праздничные)
   больше не имеют собственных цветов:
   - morning/day  -> light;
   - evening/night -> dark;
   - праздничные и сезонные (new_year, spring, magic, ...) НЕ меняют цвета,
     а только добавляют декоративные эффекты поверх базы
     (см. config/effects.py) и отключаются тумблером.

3. Все дизайн-токены (цвета, тени, радиусы, типографика, motion)
   собраны в этом файле — единый источник правды для styles.py.

4. Время — Москва (UTC+3).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

# Москва (правило проекта: UTC+3)
_MSK = timezone(timedelta(hours=3))

# =============================================================================
# БАЗОВЫЕ ПАЛИТРЫ (Sage & Sandstone, контраст WCAG AA)
# =============================================================================

BASE_THEMES = {
    # ----- Вариант A: Premium Light (утро/день) -----
    "light": {
        "bg_main": "#F7F5F1",
        "bg_sidebar": "#F1EEE8",
        "header_bg": "linear-gradient(135deg, #EDF0EA 0%, #E1E8DD 100%)",
        "header_text": "#2D3A2E",
        "text_primary": "#2D3A2E",
        "text_secondary": "#5D6A5C",          # исправлено: было ~4.3:1, стало ~5.2:1
        "card_bg": "#FFFFFF",
        "card_border": "#D9D4CB",
        "accent": "#8BA888",                  # декор: рамки, полоски, hover
        "accent_strong": "#557052",           # интерактив: ссылки, кнопки (~5.5:1 с белым)
        "button_bg": "#557052",
        "button_text": "#FFFFFF",
        "button_secondary_bg": "#FFFFFF",
        "button_secondary_text": "#2D3A2E",
        "button_secondary_border": "#C9C3B8",
        "success": "#4C7A50",
        "warning": "#8A6D3B",
        "error": "#B0563F",
        "info": "#5B7F95",
        "shadow_sm": "0 1px 2px rgba(45,58,46,0.05), 0 4px 12px rgba(45,58,46,0.08)",
        "shadow_md": "0 4px 8px rgba(45,58,46,0.08), 0 12px 28px rgba(45,58,46,0.12)",
        "focus_ring": "rgba(85,112,82,0.35)",
        "overlay": "rgba(30,36,32,0.45)",
        "logo_opacity": "0.6",
        "is_dark": False,
    },
    # ----- Вариант B: вечер/ночь -----
    "dark": {
        "bg_main": "#1E2420",
        "bg_sidebar": "#232A25",
        "header_bg": "linear-gradient(135deg, #2B3330 0%, #35403A 100%)",
        "header_text": "#ECEAE5",
        "text_primary": "#ECEAE5",
        "text_secondary": "#B0B8AD",
        "card_bg": "#2B3330",
        "card_border": "#45524A",
        "accent": "#A8C5A3",
        "accent_strong": "#A8C5A3",           # кнопки со светлым акцентом + тёмный текст (~8:1)
        "button_bg": "#A8C5A3",
        "button_text": "#1E2420",
        "button_secondary_bg": "#2B3330",
        "button_secondary_text": "#ECEAE5",
        "button_secondary_border": "#45524A",
        "success": "#8FCB94",
        "warning": "#D9B36A",
        "error": "#D98873",
        "info": "#8FB3C9",
        "shadow_sm": "0 1px 2px rgba(0,0,0,0.25), 0 4px 12px rgba(0,0,0,0.30)",
        "shadow_md": "0 4px 8px rgba(0,0,0,0.30), 0 12px 28px rgba(0,0,0,0.40)",
        "focus_ring": "rgba(168,197,163,0.40)",
        "overlay": "rgba(0,0,0,0.60)",
        "logo_opacity": "0.85",
        "is_dark": True,
    },
}

# =============================================================================
# ДИЗАЙН-ТОКЕНЫ (общие для обеих палитр)
# =============================================================================

DESIGN_TOKENS = {
    # Радиусы
    "radius_sm": "8px",
    "radius_md": "12px",
    "radius_lg": "16px",
    # Типографика (заголовки страниц уменьшены на 2-3px по договорённости)
    "font_stack": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Inter', 'Helvetica Neue', Arial, sans-serif",
    "type_xs": "12px",
    "type_sm": "14px",
    "type_md": "16px",
    "type_lg": "20px",
    "type_xl": "28px",
    "type_xxl": "34px",
    # Motion: короткий и спокойный
    "motion_fast": "0.15s",
    "motion_base": "0.2s",
    "motion_slow": "0.3s",
    # Отступы (сетка 4/8)
    "space_1": "4px",
    "space_2": "8px",
    "space_3": "12px",
    "space_4": "16px",
    "space_6": "24px",
    "space_8": "32px",
}

# =============================================================================
# МАППИНГ СТАРЫХ ТЕМ НА БАЗЫ
# =============================================================================

LIGHT_TIME_THEMES = {"morning", "day"}
DARK_TIME_THEMES = {"evening", "night"}

# Праздничные/сезонные спец-режимы: цвета НЕ меняют,
# только добавляют эффекты поверх базы (отключаются тумблером).
SPECIAL_THEMES = {
    "new_year", "spring", "summer", "childrens_day",
    "knowledge_day", "april_fools", "magic", "scifi", "military",
}

# Обратная совместимость: старые импорты THEMES не сломаются
THEMES = BASE_THEMES


# =============================================================================
# ФУНКЦИИ
# =============================================================================

def _msk_hour() -> int:
    """Текущий час по Москве (UTC+3)."""
    return datetime.now(_MSK).hour


def get_base_name(theme: str) -> str:
    """Возвращает имя базовой палитры ("light"/"dark") для любого имени темы.

    - morning, day   -> "light";
    - evening, night -> "dark";
    - спец-темы и неизвестные имена -> по времени суток (Москва):
      07:00–19:59 -> "light", 20:00–06:59 -> "dark".
    """
    if theme in LIGHT_TIME_THEMES:
        return "light"
    if theme in DARK_TIME_THEMES:
        return "dark"
    return "light" if 7 <= _msk_hour() <= 19 else "dark"


def get_base_colors(base: str) -> dict:
    """Палитра базы "light" или "dark" (фолбэк — light)."""
    return BASE_THEMES.get(base, BASE_THEMES["light"])


def get_theme_colors(theme: str) -> dict:
    """Обратно совместимая функция выбора цветов.

    Раньше возвращала собственные цвета для 13 тем.
    Теперь возвращает базовую палитру: цвета больше не зависят
    от праздников — только от режима A/B.
    """
    return get_base_colors(get_base_name(theme))


def is_dark_theme(theme: str) -> bool:
    """Тёмная ли база у темы (для логотипов, модалок и т.п.)."""
    return get_base_name(theme) == "dark"


def is_special_theme(theme: str) -> bool:
    """True, если тема — праздничный/сезонный спец-режим (эффекты поверх базы)."""
    return theme in SPECIAL_THEMES


def resolve_mode(override: Optional[str], time_theme: str) -> str:
    """Финальный режим A/B с учётом ручного переключения.

    override — выбор пользователя из query_params/localStorage
    ("light"/"dark"); имеет приоритет над автоопределением.
    time_theme — тема из greeting_data (morning/day/evening/night/спец).
    """
    if override in ("light", "dark"):
        return override
    return get_base_name(time_theme)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "BASE_THEMES",
    "DESIGN_TOKENS",
    "LIGHT_TIME_THEMES",
    "DARK_TIME_THEMES",
    "SPECIAL_THEMES",
    "THEMES",
    "get_base_name",
    "get_base_colors",
    "get_theme_colors",
    "is_dark_theme",
    "is_special_theme",
    "resolve_mode",
]