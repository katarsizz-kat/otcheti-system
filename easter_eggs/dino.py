"""Пасхалка с динозавром — исправленная версия (не открывается автоматически).

v2.1: принудительная темизация ВСЕХ внутренних слоёв модалки st.dialog
(Baseweb-портал рендерит вложенные контейнеры со своим фоном —
теперь каждый слой перекрашен в var(--card-bg), текст в var(--text-primary)).
Логика сохранена полностью: ключи, счётчик кликов,
"Кристина лучшая ❤️" каждый 5-й клик, автозвук, фолбэк-gif.
st.dialog нативно закрывается по Esc и клику вне окна.

v3: кнопка-пасхалка незаметна и изредка покачивается; ночью Дино спит,
в праздники — в костюме. JS-пасхалки (Konami-код, 10 кликов по заголовку,
редкая прогулка) — в dino_tricks.js.
"""

import os
import html
import random
import base64
import streamlit as st
import streamlit.components.v1 as components

from config.mascots import get_random_phrase
from config.greetings import get_current_hour
from config.holidays import get_today_holiday, get_holiday_theme
from config.effects import is_effects_enabled

# Лежит в static/, чтобы JS-пасхалки могли взять его по URL
# (server.enableStaticServing в .streamlit/config.toml).
ROAR_PATH = os.path.join("static", "dino_roar.mp3")
ROAR_URL = "app/static/dino_roar.mp3"
TRICKS_JS_PATH = os.path.join(os.path.dirname(__file__), "dino_tricks.js")

SLEEPY_PHRASES = [
    "Я сплю. И тебе пора 😴",
    "Ррр… ещё пять минуточек… 💤",
    "Отчёты никуда не убегут. А я сплю 🌙",
    "Тсс! Динозавры спят по 12 часов. Завидуй молча 😴",
]

# Тема праздника (config.holidays.get_holiday_theme) -> костюм Дино
COSTUMES = {
    "pizza": "🍕",
    "chef": "🧑‍🍳",
    "new_year": "🎅",
    "love": "💘",
    "spring": "🌷",
    "knowledge": "🎓",
    "halloween": "🎃",
    "patriot": "🎖️",
    "space": "🚀",
    "humor": "🤡",
    "children": "🎈",
    "marketing": "📣",
}


def _is_night() -> bool:
    """Ночь — те же часы, что и ночное приветствие (23:00–05:00 МСК)."""
    hour = get_current_hour()
    return hour >= 23 or hour < 5


def _costume() -> str:
    """Костюм Дино на сегодняшний праздник (или пустая строка)."""
    holiday = get_today_holiday()
    if not holiday:
        return ""
    return COSTUMES.get(get_holiday_theme(holiday.get("title", "")), "")


@st.cache_data
def _load_tricks_js() -> str:
    with open(TRICKS_JS_PATH, encoding="utf-8") as f:
        return f.read()


def render_dino_tricks():
    """Невидимый iframe с JS-пасхалками для всей страницы."""
    js = (
        _load_tricks_js()
        .replace("__ROAR_URL__", ROAR_URL)
        .replace("__WALK_ENABLED__", "true" if is_effects_enabled() else "false")
    )
    components.html(f"<script>{js}</script>", height=0)


@st.cache_data
def load_gif_base64(gif_path: str) -> str:
    """Кэшированная загрузка GIF в base64."""
    try:
        with open(gif_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


@st.dialog("🦖 Динозавр приветствует тебя!")
def dino_dialog(phrase: str, gif_src: str):
    """Нативная модалка Streamlit (Esc / клик вне — закрытие)."""
    st.markdown(
        """
        <style>
        /* ===== v2.1: КРАСИМ ВСЕ СЛОИ МОДАЛКИ (Baseweb-портал) ===== */
        div[data-testid="stModal"], div[data-testid="stModal"] > div,
        div[data-testid="stDialog"], div[data-testid="stDialog"] > div,
        div[role="dialog"], div[role="dialog"] > div {
            background-color: var(--card-bg, #FFFFFF) !important;
            color: var(--text-primary, #2D3A2E) !important;
            border: 1px solid var(--card-border, #D9D4CB) !important;
            border-radius: 16px !important;
        }
        /* Заголовок диалога */
        div[data-testid="stDialog"] h3 {
            color: var(--accent-strong, #557052) !important;
            font-size: 24px !important;
            font-weight: bold !important;
            text-align: center !important;
            margin-bottom: 20px !important;
        }
        /* Весь текст внутри диалога */
        div[data-testid="stDialog"] p,
        div[data-testid="stDialog"] span {
            color: var(--text-primary, #2D3A2E) !important;
        }
        /* Маленькая круглая кнопка закрытия (крестик портала) */
        div[data-testid="stDialog"] button[kind="secondary"] {
            background: var(--hover-bg, rgba(45,58,46,0.06)) !important;
            border: none !important;
            border-radius: 50% !important;
            width: 36px !important;
            height: 36px !important;
            min-width: 36px !important;
            padding: 0 !important;
            font-size: 20px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            margin: 10px auto 0 auto !important;
            transition: transform 0.15s ease,
                background-color 0.15s ease !important;
        }
        div[data-testid="stDialog"] button[kind="secondary"]:hover {
            background: var(--active-bg, rgba(45,58,46,0.10)) !important;
            transform: scale(1.1) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Гифка
    st.image(gif_src, width="stretch")

    # Фраза (экранирована)
    st.markdown(
        f"""
        <div style="text-align: center; font-size: 22px; font-weight: 700;
            color: var(--text-primary, #2D3A2E); padding: 20px 0;">
            {html.escape(str(phrase))}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Звук. Голый <audio src="assets/..."> не работает: Streamlit не раздаёт
    # папку assets по HTTP. st.audio сам отдаёт файл; плеер прячем CSS-ом.
    if os.path.exists(ROAR_PATH):
        st.markdown(
            '<style>div[data-testid="stDialog"] [data-testid="stAudio"]'
            '{display:none !important;}</style>',
            unsafe_allow_html=True,
        )
        st.audio(ROAR_PATH, format="audio/mpeg", autoplay=True)

    # Кнопка закрытия
    if st.button("✖", key="dino_close_btn", help="Закрыть"):
        st.session_state.main_page_dino_modal_open = False
        st.rerun()


def render_dino_footer():
    """Рендерит кнопку динозавра в подвале (всегда видна, открывается только по клику)."""
    # Уникальные ключи для главной страницы (не конфликтуют с другими страницами)
    if "main_page_dino_modal_open" not in st.session_state:
        st.session_state.main_page_dino_modal_open = False
    if "main_page_dino_phrase" not in st.session_state:
        st.session_state.main_page_dino_phrase = get_random_phrase()
    if "main_page_dino_click_count" not in st.session_state:
        st.session_state.main_page_dino_click_count = 0

    # Пасхалка должна быть незаметной: полупрозрачная, без рамки,
    # изредка покачивается; при наведении проявляется.
    st.markdown(
        "<style>"
        ".st-key-dino_open_btn div[data-testid='stButton'] > button[kind] {"
        "  background: transparent !important; border: none !important;"
        "  box-shadow: none !important; padding: 0 4px !important;"
        "  min-height: 0 !important; opacity: 0.25;"
        "  transition: opacity 0.3s ease;"
        "}"
        ".st-key-dino_open_btn div[data-testid='stButton'] > button[kind]:hover {"
        "  opacity: 1; background: transparent !important;"
        "}"
        ".st-key-dino_open_btn button p {"
        "  font-size: 18px !important; display: inline-block; white-space: nowrap;"
        "  transform-origin: 50% 90%;"
        "  animation: dino-wobble 9s ease-in-out infinite;"
        "}"
        "@keyframes dino-wobble {"
        "  0%, 88%, 100% { transform: rotate(0deg); }"
        "  90% { transform: rotate(-12deg); }"
        "  92% { transform: rotate(10deg); }"
        "  94% { transform: rotate(-6deg); }"
        "  96% { transform: rotate(3deg); }"
        "}"
        "@media (prefers-reduced-motion: reduce) {"
        "  .st-key-dino_open_btn button p { animation: none; }"
        "}"
        "</style>",
        unsafe_allow_html=True,
    )

    night = _is_night()
    label = "🦖💤" if night else "🦖" + _costume()

    col1, col2 = st.columns([1, 10])
    with col1:
        if st.button(label, key="dino_open_btn"):
            st.session_state.main_page_dino_click_count += 1
            if st.session_state.main_page_dino_click_count % 5 == 0:
                st.session_state.main_page_dino_phrase = "Кристина лучшая ❤️"
            elif night:
                st.session_state.main_page_dino_phrase = random.choice(SLEEPY_PHRASES)
            else:
                st.session_state.main_page_dino_phrase = get_random_phrase()
            st.session_state.main_page_dino_modal_open = True
            st.rerun()

    render_dino_tricks()

    # Если модалка открыта — показываем диалог и сразу сбрасываем состояние
    if st.session_state.main_page_dino_modal_open:
        gif_num = random.choice([1, 2])
        gif_path = f"assets/dino{gif_num}.gif"
        gif_base64 = load_gif_base64(gif_path)
        if gif_base64:
            gif_src = f"data:image/gif;base64,{gif_base64}"
        else:
            gif_src = "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"

        # Вызываем диалог
        dino_dialog(st.session_state.main_page_dino_phrase, gif_src)

        # Сбрасываем состояние после открытия (чтобы не открывался
        # автоматически при следующем рендере)
        st.session_state.main_page_dino_modal_open = False