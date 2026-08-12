"""Декоративные эффекты приложения.

Архитектура v2.0:

1. Эффекты НЕ меняют цвета интерфейса — они накладываются поверх
   базовой палитры A/B (см. config/theme.py).
2. Темы времени суток: morning/day -> облака, evening/night -> звёзды.
3. Праздничные/сезонные спец-темы маппятся на наборы эффектов
   (снег, лепестки, конфетти, шарики и т.д.).
4. Весь декор отключается тумблером (is_effects_enabled / set_effects_enabled).
5. Пастельные шарики после успешного формирования отчёта:
   страница вызывает celebrate_report_success(),
   а styles.py при рендере забирает анимацию через consume_pending_balloons().
6. Все анимации уважают prefers-reduced-motion.
7. Расстановка элементов детерминированная — не "мигает" при rerun.
"""

import streamlit as st
from typing import List, Optional

# =============================================================================
# КОНСТАНТЫ
# =============================================================================

# Пастельные цвета шариков (утверждено)
BALLOON_COLORS = ["#D4C5F9", "#F9D4C5", "#C5E8D4", "#F5E6C8", "#C5DCF9"]

# Ключи session_state
_FX_KEY = "fx_effects_enabled"
_BALLOONS_KEY = "fx_balloons_pending"

# Маппинг спец-тем на наборы эффектов (поверх базы A/B)
SPECIAL_EFFECT_MAP = {
    "new_year": ["snow"],
    "spring": ["petals"],
    "summer": ["motes"],
    "childrens_day": ["balloons"],
    "knowledge_day": ["confetti"],
    "april_fools": ["confetti"],
    "magic": ["sparkles", "stars"],
    "scifi": ["scifi"],
    "military": [],
}

# =============================================================================
# ТУМБЛЕР ЭФФЕКТОВ
# =============================================================================

def is_effects_enabled() -> bool:
    """Включён ли праздничный декор (по умолчанию — да)."""
    return bool(st.session_state.get(_FX_KEY, True))


def set_effects_enabled(enabled: bool) -> None:
    """Включить/выключить праздничный декор."""
    st.session_state[_FX_KEY] = bool(enabled)

# =============================================================================
# ШАРИКИ ПОСЛЕ УСПЕШНОГО ОТЧЁТА
# =============================================================================

def celebrate_report_success() -> None:
    """Отметить успешное формирование отчёта.

    Вызывается на страницах отчётов (КР месяц, КР неделя, ОС, Продукт)
    после успешной генерации файла. Анимацию заберёт styles.py
    через consume_pending_balloons() при следующем рендере.
    """
    st.session_state[_BALLOONS_KEY] = True


def consume_pending_balloons() -> str:
    """Возвращает HTML одноразовых шариков и сбрасывает флаг.

    Шарики успеха — это feedback действия, поэтому тумблером
    праздничных эффектов НЕ отключаются (только prefers-reduced-motion).
    """
    if not st.session_state.get(_BALLOONS_KEY):
        return ""
    st.session_state[_BALLOONS_KEY] = False
    return _balloons(loop=False)

# =============================================================================
# ПУБЛИЧНЫЕ ГЕНЕРАТОРЫ (обратно совместимый API)
# =============================================================================

def get_theme_effect(theme: str) -> str:
    """Эффекты темы времени суток / спец-темы.

    - morning/day  -> лёгкие облака;
    - evening/night -> звёзды;
    - спец-темы -> свой набор эффектов поверх базы;
    - выключенный тумблер -> пустая строка.
    """
    if not is_effects_enabled():
        return ""
    if theme in ("morning", "day"):
        return _clouds()
    if theme in ("evening", "night"):
        return _stars()
    parts = []
    for name in SPECIAL_EFFECT_MAP.get(theme, []):
        gen = EFFECT_PRESETS.get(name)
        if gen:
            parts.append(gen())
    return "".join(parts)


def get_holiday_effects(effects: Optional[List[str]]) -> str:
    """Эффекты из конфига праздника (список имён).

    Неизвестные имена игнорируются — старые конфиги не сломают новый код.
    """
    if not effects or not is_effects_enabled():
        return ""
    parts = []
    for name in effects:
        gen = EFFECT_PRESETS.get(str(name).lower())
        if gen:
            parts.append(gen())
    return "".join(parts)

# =============================================================================
# СЛУЖЕБНОЕ
# =============================================================================

def _wrap(css: str, inner: str) -> str:
    """Оборачивает эффект: фиксированный слой + reduced-motion."""
    base = (
        ".fx-layer { position: fixed; inset: 0; pointer-events: none; "
        "z-index: 1; overflow: hidden; } "
    )
    reduced = (
        "@media (prefers-reduced-motion: reduce) { "
        ".fx-layer * { animation: none !important; opacity: 0.3; } } "
    )
    return (
        f"<style>{base}{css}{reduced}</style>"
        f"<div class='fx-layer' aria-hidden='true'>{inner}</div>"
    )

# =============================================================================
# ГЕНЕРАТОРЫ ЭФФЕКТОВ
# =============================================================================

def _clouds() -> str:
    """Лёгкие облака для светлой базы."""
    css = (
        ".fx-cloud { position: absolute; left: -30%; border-radius: 999px; "
        "background: radial-gradient(closest-side, rgba(255,255,255,0.9), rgba(255,255,255,0)); "
        "opacity: 0.45; animation: fxDrift linear infinite; } "
        "@keyframes fxDrift { from { transform: translateX(0); } to { transform: translateX(165vw); } } "
    )
    inner = []
    for i in range(4):
        top = 6 + i * 9 + (i * 13) % 5
        w = 180 + (i * 97) % 140
        h = w // 3
        dur = 70 + (i * 29) % 50
        delay = -((i * 31) % dur)
        inner.append(
            f"<div class='fx-cloud' style='top:{top}%;width:{w}px;height:{h}px;"
            f"animation-duration:{dur}s;animation-delay:{delay}s;'></div>"
        )
    return _wrap(css, "".join(inner))


def _stars() -> str:
    """Мерцающие звёзды для тёмной базы."""
    css = (
        ".fx-star { position: absolute; width: 3px; height: 3px; border-radius: 50%; "
        "background: var(--text-primary, #ECEAE5); opacity: 0.5; "
        "animation: fxTwinkle 3.2s ease-in-out infinite; } "
        "@keyframes fxTwinkle { 0%, 100% { opacity: 0.2; } 50% { opacity: 0.75; } } "
    )
    inner = []
    for i in range(18):
        left = (i * 53) % 100
        top = (i * 37) % 90
        delay = round((i * 0.4) % 3.2, 1)
        inner.append(
            f"<div class='fx-star' style='left:{left}%;top:{top}%;"
            f"animation-delay:{delay}s;'></div>"
        )
    return _wrap(css, "".join(inner))


def _snow() -> str:
    """Снежинки (новый год)."""
    css = (
        ".fx-snow { position: absolute; top: -6%; color: var(--text-secondary, #B0B8AD); "
        "opacity: 0.5; animation: fxFall linear infinite; } "
        "@keyframes fxFall { 0% { transform: translateY(-8vh) translateX(0); } "
        "50% { transform: translateY(52vh) translateX(18px); } "
        "100% { transform: translateY(112vh) translateX(-12px); } } "
    )
    inner = []
    for i in range(14):
        left = (i * 47) % 100
        size = 10 + (i * 7) % 10
        dur = 9 + (i * 3) % 8
        delay = -((i * 2) % dur)
        inner.append(
            f"<span class='fx-snow' style='left:{left}%;font-size:{size}px;"
            f"animation-duration:{dur}s;animation-delay:{delay}s;'>❄</span>"
        )
    return _wrap(css, "".join(inner))


def _petals() -> str:
    """Лепестки (весна)."""
    css = (
        ".fx-petal { position: absolute; top: -6%; width: 10px; height: 10px; "
        "border-radius: 60% 40% 55% 45%; background: #F9D4C5; opacity: 0.7; "
        "animation: fxFall linear infinite; } "
        "@keyframes fxFall { 0% { transform: translateY(-8vh) translateX(0) rotate(0deg); } "
        "50% { transform: translateY(52vh) translateX(20px) rotate(160deg); } "
        "100% { transform: translateY(112vh) translateX(-12px) rotate(320deg); } } "
    )
    inner = []
    for i in range(12):
        left = (i * 61) % 100
        dur = 10 + (i * 5) % 8
        delay = -((i * 3) % dur)
        inner.append(
            f"<div class='fx-petal' style='left:{left}%;animation-duration:{dur}s;"
            f"animation-delay:{delay}s;'></div>"
        )
    return _wrap(css, "".join(inner))


def _confetti() -> str:
    """Конфети (1 сентября, 1 апреля, праздники)."""
    css = (
        ".fx-confetti { position: absolute; top: -6%; width: 8px; height: 12px; "
        "border-radius: 2px; opacity: 0.85; animation: fxSpin linear infinite; } "
        "@keyframes fxSpin { from { transform: translateY(-8vh) rotate(0deg); } "
        "to { transform: translateY(112vh) rotate(680deg); } } "
    )
    inner = []
    for i in range(16):
        left = (i * 43) % 100
        color = BALLOON_COLORS[i % len(BALLOON_COLORS)]
        dur = 6 + (i * 3) % 6
        delay = -((i * 2) % dur)
        inner.append(
            f"<div class='fx-confetti' style='left:{left}%;background:{color};"
            f"animation-duration:{dur}s;animation-delay:{delay}s;'></div>"
        )
    return _wrap(css, "".join(inner))


def _sparkles() -> str:
    """Искры (магия)."""
    css = (
        ".fx-sparkle { position: absolute; color: var(--accent, #A8C5A3); opacity: 0.6; "
        "animation: fxTwinkle 2.6s ease-in-out infinite; } "
        "@keyframes fxTwinkle { 0%, 100% { opacity: 0.2; transform: scale(0.9); } "
        "50% { opacity: 0.8; transform: scale(1.1); } } "
    )
    inner = []
    for i in range(12):
        left = (i * 59) % 100
        top = (i * 41) % 90
        size = 12 + (i * 5) % 8
        delay = round((i * 0.3) % 2.6, 1)
        sym = "✦" if i % 2 == 0 else "✨"
        inner.append(
            f"<span class='fx-sparkle' style='left:{left}%;top:{top}%;font-size:{size}px;"
            f"animation-delay:{delay}s;'>{sym}</span>"
        )
    return _wrap(css, "".join(inner))


def _motes() -> str:
    """Тёплые пылинки, плывущие вверх (лето)."""
    css = (
        ".fx-mote { position: absolute; bottom: -4%; width: 6px; height: 6px; "
        "border-radius: 50%; background: #F5E6C8; opacity: 0.6; "
        "animation: fxFloatUp linear infinite; } "
        "@keyframes fxFloatUp { from { transform: translateY(0); opacity: 0; } "
        "15% { opacity: 0.7; } to { transform: translateY(-110vh); opacity: 0; } } "
    )
    inner = []
    for i in range(10):
        left = (i * 71) % 100
        dur = 12 + (i * 7) % 10
        delay = -((i * 4) % dur)
        inner.append(
            f"<div class='fx-mote' style='left:{left}%;animation-duration:{dur}s;"
            f"animation-delay:{delay}s;'></div>"
        )
    return _wrap(css, "".join(inner))


def _scifi() -> str:
    """Медленная сканирующая линия (sci-fi)."""
    css = (
        ".fx-scan { position: absolute; left: 0; width: 100%; height: 2px; "
        "background: linear-gradient(90deg, transparent, var(--accent, #A8C5A3), transparent); "
        "opacity: 0.25; animation: fxScan 9s linear infinite; } "
        "@keyframes fxScan { from { top: -5%; } to { top: 105%; } } "
    )
    inner = (
        "<div class='fx-scan' style='animation-delay:0s;'></div>"
        "<div class='fx-scan' style='animation-delay:-4.5s;'></div>"
    )
    return _wrap(css, inner)


def _balloons(loop: bool = True) -> str:
    """Пастельные шарики.

    loop=True  — праздничные (летают постоянно);
    loop=False — одноразовые после успешного отчёта (~6 сек и исчезают).
    """
    mode = "infinite" if loop else "forwards"
    css = (
        ".fx-balloon { position: absolute; bottom: -90px; width: 34px; height: 42px; "
        "border-radius: 50% 50% 48% 52% / 55% 55% 45% 45%; "
        f"animation: fxRise 6s ease-in {mode}; }} "
        "@keyframes fxRise { 0% { transform: translateY(0) translateX(0); opacity: 0; } "
        "12% { opacity: 0.95; } "
        "50% { transform: translateY(-58vh) translateX(26px); } "
        "100% { transform: translateY(-118vh) translateX(-14px); opacity: 0; } } "
    )
    inner = []
    count = 14 if loop else 20
    for i in range(count):
        left = (i * 47) % 100
        color = BALLOON_COLORS[i % len(BALLOON_COLORS)]
        dur = round(5.5 + (i % 5) * 0.5, 1)
        if loop:
            delay = -round((i * 1.3) % 6, 1)
        else:
            delay = round((i * 0.18) % 1.5, 2)
        bg = f"radial-gradient(circle at 30% 25%, rgba(255,255,255,0.75), {color} 65%)"
        inner.append(
            f"<div class='fx-balloon' style='left:{left}%;background:{bg};"
            f"animation-duration:{dur}s;animation-delay:{delay}s;'></div>"
        )
    return _wrap(css, "".join(inner))

# =============================================================================
# РЕЕСТР ПРЕСЕТОВ (имя -> генератор)
# =============================================================================

EFFECT_PRESETS = {
    "clouds": _clouds,
    "stars": _stars,
    "snow": _snow,
    "petals": _petals,
    "confetti": _confetti,
    "sparkles": _sparkles,
    "motes": _motes,
    "scifi": _scifi,
    "balloons": _balloons,
}

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "BALLOON_COLORS",
    "SPECIAL_EFFECT_MAP",
    "EFFECT_PRESETS",
    "is_effects_enabled",
    "set_effects_enabled",
    "celebrate_report_success",
    "consume_pending_balloons",
    "get_theme_effect",
    "get_holiday_effects",
]