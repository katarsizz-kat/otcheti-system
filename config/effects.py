"""Декоративные эффекты приложения.

Архитектура v3.1:
- Эффекты НЕ меняют цвета интерфейса — только декор поверх базы A/B.
- Три вида "веселья" (никогда не накладываются друг на друга):
  1) Шарики успеха — пастельные, градиент, блик, объёмная тень;
     крупные (46–64px) и непрозрачные; летят ТОЛЬКО после успешной
     генерации отчётов (celebrate_report_success -> consume_pending_balloons);
  2) Праздничные шарики — другой дизайн: ярче, градиент из двух цветов,
     верёвочка и покачивание; крупные (50–68px); летят на обычные
     праздники БЕЗ тематических эффектов;
  3) Тематические эффекты (снег, пицца, тыквы, конфетти, лепестки...) —
     только на праздники, где они прописаны; шарики в этот день не летят.
- Весь декор отключается тумблером (is_effects_enabled / set_effects_enabled),
  кроме шариков успеха (это feedback действия).
- prefers-reduced-motion уважается везде.
- Расстановка элементов детерминированная — не "мигает" при rerun.
"""

import streamlit as st
from typing import List, Optional

# =============================================================================
# КОНСТАНТЫ
# =============================================================================

# Пастельные цвета шариков успеха (утверждены)
BALLOON_COLORS = ["#D4C5F9", "#F9D4C5", "#C5E8D4", "#F5E6C8", "#C5DCF9"]

# Праздничные шарики: пары (светлый -> насыщенный) для градиента
HOLIDAY_BALLOON_GRADIENTS = [
    ("#FF9A9E", "#FAD0C4"),   # розово-персиковый
    ("#A18CD1", "#FBC2EB"),   # лаванда-розовый
    ("#84FAB0", "#8FD3F4"),   # мята-небо
    ("#FCCB90", "#D57EEB"),   # персик-фиалка
    ("#E0C3FC", "#8EC5FC"),   # сирень-голубой
]

# Ключи session_state
_FX_KEY = "fx_effects_enabled"
_BALLOONS_KEY = "fx_balloons_pending"

# Маппинг спец-тем на наборы эффектов (поверх базы A/B)
SPECIAL_EFFECT_MAP = {
    "new_year": ["snow", "confetti"],
    "spring": ["petals"],
    "summer": ["motes"],
    "childrens_day": ["balloons_festive"],
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
# ШАРИКИ УСПЕХА (пастельные) — ТОЛЬКО после генерации отчётов
# =============================================================================

def celebrate_report_success() -> None:
    """Отметить успешное формирование отчёта.

    Вызывается на страницах отчётов после успешной генерации.
    Анимацию забирает styles.py через consume_pending_balloons().
    """
    st.session_state[_BALLOONS_KEY] = True


def consume_pending_balloons() -> str:
    """Возвращает HTML пастельных шариков и сбрасывает флаг.

    Шарики успеха — feedback действия, поэтому тумблером
    праздничных эффектов НЕ отключаются.
    """
    if not st.session_state.get(_BALLOONS_KEY):
        return ""
    st.session_state[_BALLOONS_KEY] = False
    return _report_balloons()

# =============================================================================
# ПРАЗДНИЧНЫЕ ШАРИКИ (другой дизайн) — на обычные праздники
# =============================================================================

def should_show_holiday_balloons(holiday: dict) -> bool:
    """True, если на праздник летят праздничные шарики.

    Правило "не накладывается": если у праздника есть тематические
    эффекты (снег/пицца/тыквы/...) — летят они, шарики НЕТ.
    Если эффектов нет — летят праздничные шарики.
    """
    if not isinstance(holiday, dict):
        return False
    if not is_effects_enabled():
        return False
    effects = holiday.get("effects") or []
    return len(effects) == 0


def get_holiday_balloons_html() -> str:
    """HTML праздничных шариков (яркие, градиент, верёвочка, покачивание)."""
    if not is_effects_enabled():
        return ""
    return _festive_balloons()

# =============================================================================
# ПУБЛИЧНЫЕ ГЕНЕРАТОРЫ (обратно совместимый API)
# =============================================================================

def get_theme_effect(theme: str) -> str:
    """Эффекты темы времени суток / спец-темы.

    - morning/day   -> лёгкие облака;
    - evening/night -> звёзды;
    - спец-темы     -> свой набор эффектов;
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

    Неизвестные имена игнорируются — старые конфиги не сломают код.
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
    """Фиксированный декоративный слой + reduced-motion."""
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
# ШАРИКИ УСПЕХА: пастельные, крупные, непрозрачные, с объёмом
# v3.1: размер 46–64px, opacity 1, сочнее градиент, тени объёма
# =============================================================================

def _report_balloons() -> str:
    css = (
        ".fx-balloon { position: absolute; bottom: -110px; "
        "border-radius: 50% 50% 48% 52% / 55% 55% 45% 45%; "
        "box-shadow: 0 8px 20px rgba(0,0,0,0.12), "
        "inset -6px -8px 14px rgba(0,0,0,0.08); "
        "animation: fxRise 6s ease-in forwards; } "
        "@keyframes fxRise { 0% { transform: translateY(0) translateX(0); opacity: 0; } 10% { opacity: 1; } 50% { transform: translateY(-58vh) translateX(26px); } 100% { transform: translateY(-118vh) translateX(-14px); opacity: 0; } } "
    )
    inner = []
    for i in range(24):
        left = (i * 47) % 100
        color = BALLOON_COLORS[i % len(BALLOON_COLORS)]
        w = 46 + (i % 4) * 6          # 46 / 52 / 58 / 64 px
        h = round(w * 1.25)
        dur = round(5.5 + (i % 5) * 0.5, 1)
        delay = round((i * 0.18) % 1.5, 2)
        bg = (
            f"radial-gradient(circle at 30% 25%, rgba(255,255,255,0.55), "
            f"{color} 50%)"
        )
        inner.append(
            f"<div class='fx-balloon' style='left:{left}%;width:{w}px;height:{h}px;"
            f"background:{bg};animation-duration:{dur}s;"
            f"animation-delay:{delay}s;'></div>"
        )
    return _wrap(css, "".join(inner))

# =============================================================================
# ПРАЗДНИЧНЫЕ ШАРИКИ: яркий градиент + верёвочка + покачивание
# v3.1: размер 50–68px, opacity 1, верёвочка длиннее и заметнее
# =============================================================================

def _festive_balloons() -> str:
    css = (
        ".fx-hballoon { position: absolute; bottom: -150px; "
        "border-radius: 50% 50% 47% 53% / 55% 55% 45% 45%; "
        "box-shadow: 0 8px 20px rgba(0,0,0,0.14), "
        "inset -6px -8px 14px rgba(0,0,0,0.10); "
        "animation: fxRiseSway 7s ease-in forwards; } "
        ".fx-hballoon::after { content: ''; position: absolute; left: 50%; top: 99%; "
        "width: 2px; height: 60px; background: rgba(120,120,120,0.45); "
        "transform: translateX(-50%); } "
        "@keyframes fxRiseSway { 0% { transform: translateY(0) translateX(0) rotate(0deg); opacity: 0; } 10% { opacity: 1; } 25% { transform: translateY(-30vh) translateX(18px) rotate(6deg); } 50% { transform: translateY(-60vh) translateX(-16px) rotate(-6deg); } 75% { transform: translateY(-90vh) translateX(14px) rotate(4deg); } 100% { transform: translateY(-125vh) translateX(-8px) rotate(0deg); opacity: 0; } } "
    )
    inner = []
    for i in range(16):
        left = (i * 53) % 100
        c1, c2 = HOLIDAY_BALLOON_GRADIENTS[i % len(HOLIDAY_BALLOON_GRADIENTS)]
        w = 50 + (i % 4) * 6          # 50 / 56 / 62 / 68 px
        h = round(w * 1.25)
        dur = round(6.0 + (i % 4) * 0.6, 1)
        delay = round((i * 0.22) % 1.8, 2)
        bg = (
            f"radial-gradient(circle at 30% 25%, rgba(255,255,255,0.85), "
            f"{c1} 45%, {c2} 100%)"
        )
        inner.append(
            f"<div class='fx-hballoon' style='left:{left}%;width:{w}px;height:{h}px;"
            f"background:{bg};animation-duration:{dur}s;"
            f"animation-delay:{delay}s;'></div>"
        )
    return _wrap(css, "".join(inner))

# =============================================================================
# ТЕМАТИЧЕСКИЕ ЭФФЕКТЫ
# =============================================================================

def _clouds() -> str:
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
    css = (
        ".fx-snow { position: absolute; top: -6%; color: var(--text-secondary, #B0B8AD); "
        "opacity: 0.5; animation: fxFall linear infinite; } "
        "@keyframes fxFall { 0% { transform: translateY(-8vh) translateX(0); } 50% { transform: translateY(52vh) translateX(18px); } 100% { transform: translateY(112vh) translateX(-12px); } } "
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
    css = (
        ".fx-petal { position: absolute; top: -6%; width: 10px; height: 10px; "
        "border-radius: 60% 40% 55% 45%; background: #F9D4C5; opacity: 0.7; "
        "animation: fxFall linear infinite; } "
        "@keyframes fxFall { 0% { transform: translateY(-8vh) translateX(0) rotate(0deg); } 50% { transform: translateY(52vh) translateX(20px) rotate(160deg); } 100% { transform: translateY(112vh) translateX(-12px) rotate(320deg); } } "
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
    css = (
        ".fx-confetti { position: absolute; top: -6%; width: 8px; height: 12px; "
        "border-radius: 2px; opacity: 0.85; animation: fxSpin linear infinite; } "
        "@keyframes fxSpin { from { transform: translateY(-8vh) rotate(0deg); } to { transform: translateY(112vh) rotate(680deg); } } "
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
    css = (
        ".fx-sparkle { position: absolute; color: var(--accent, #A8C5A3); opacity: 0.6; "
        "animation: fxTwinkle 2.6s ease-in-out infinite; } "
        "@keyframes fxTwinkle { 0%, 100% { opacity: 0.2; transform: scale(0.9); } 50% { opacity: 0.8; transform: scale(1.1); } } "
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
    css = (
        ".fx-mote { position: absolute; bottom: -4%; width: 6px; height: 6px; "
        "border-radius: 50%; background: #F5E6C8; opacity: 0.6; "
        "animation: fxFloatUp linear infinite; } "
        "@keyframes fxFloatUp { from { transform: translateY(0); opacity: 0; } 15% { opacity: 0.7; } to { transform: translateY(-110vh); opacity: 0; } } "
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


def _falling_pizza() -> str:
    css = (
        ".fx-pizza { position: absolute; top: -8%; opacity: 0.8; "
        "animation: fxPizzaFall linear infinite; } "
        "@keyframes fxPizzaFall { 0% { transform: translateY(-8vh) rotate(0deg); } 100% { transform: translateY(115vh) rotate(360deg); } } "
    )
    inner = []
    for i in range(12):
        left = (i * 49) % 100
        size = 14 + (i * 5) % 12
        dur = 7 + (i * 3) % 6
        delay = -((i * 2) % dur)
        inner.append(
            f"<span class='fx-pizza' style='left:{left}%;font-size:{size}px;"
            f"animation-duration:{dur}s;animation-delay:{delay}s;'>🍕</span>"
        )
    return _wrap(css, "".join(inner))


def _pumpkins() -> str:
    css = (
        ".fx-pumpkin { position: absolute; top: -8%; opacity: 0.85; "
        "filter: drop-shadow(0 0 6px rgba(243,156,18,0.6)); "
        "animation: fxPumpkinFall linear infinite; } "
        "@keyframes fxPumpkinFall { 0% { transform: translateY(-8vh) translateX(0) rotate(-8deg); } 50% { transform: translateY(52vh) translateX(22px) rotate(8deg); } 100% { transform: translateY(115vh) translateX(-14px) rotate(-8deg); } } "
    )
    inner = []
    for i in range(10):
        left = (i * 57) % 100
        size = 16 + (i * 5) % 12
        dur = 8 + (i * 3) % 7
        delay = -((i * 3) % dur)
        inner.append(
            f"<span class='fx-pumpkin' style='left:{left}%;font-size:{size}px;"
            f"animation-duration:{dur}s;animation-delay:{delay}s;'>🎃</span>"
        )
    return _wrap(css, "".join(inner))


def _balloons_festive_loop() -> str:
    """Зацикленные праздничные шарики (для спец-тем, например 1 июня)."""
    return _festive_balloons().replace("forwards", "infinite")

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
    "falling_pizza": _falling_pizza,
    "pumpkins": _pumpkins,
    "balloons": _report_balloons,
    "balloons_festive": _festive_balloons,
}

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "BALLOON_COLORS",
    "HOLIDAY_BALLOON_GRADIENTS",
    "SPECIAL_EFFECT_MAP",
    "EFFECT_PRESETS",
    "is_effects_enabled",
    "set_effects_enabled",
    "celebrate_report_success",
    "consume_pending_balloons",
    "should_show_holiday_balloons",
    "get_holiday_balloons_html",
    "get_theme_effect",
    "get_holiday_effects",
]