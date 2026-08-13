"""Логика праздничных дней.

Архитектура v2.0 (дизайн-система Sage & Sandstone):
- Время — Москва (UTC+3), по правилу проекта.
- holidays.json — единый источник всех 366 дат:
  * "богатые" записи (mascot/effects/button/secret) — главные праздники;
  * "весёлые" записи {"title", "emoji"} — обычные дни.
- Все 1-е числа месяца автоматически становятся богатыми
  (конфетти + фраза Дино), если не прописаны в json вручную.
- Плавающие даты вычисляются кодом:
  * пончики   — 1-я пятница июня;
  * мороженое — 3-е воскресенье июля;
  * Масленица — таблица по годам (MASLENITSA_DATES).
- Фразы Дино: базовый игривый пул + тематические пулы;
  подбираются по названию праздника, детерминированно в течение дня.
- "Ближайшие праздники" — 5 дней вперёд по умолчанию.
- API обратно совместим: get_today_holiday(), get_upcoming_holidays(days).
"""
import json
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from functools import lru_cache

# Москва (правило проекта: UTC+3)
MSK = timezone(timedelta(hours=3))

# Масленица (последний день) по годам — обновлять при необходимости
MASLENITSA_DATES = {
    2026: "02-22",
    2027: "03-07",
}

# =============================================================================
# ФРАЗЫ ДИНО
# =============================================================================

DINO_BASE_PHRASES = [
    "Ррр! Сегодня праздник — и это здорово! Я пошёл праздновать с пиццей! 🦖",
    "Дино сообщает: настроение — отличное! Причина: сегодня праздник! 🎉",
    "Рык! Перевод: поздравляю тебя с праздником! 🦖",
    "Я не большой, я просто хорошо кушаю! А сегодня кушаю вдвойне! 😋",
    "Дино уже надел праздничную шляпу. А ты? 🥳",
    "Ррр-праздник! Раздаю обнимашки и пиццу всем желающим! 🍕",
    "Знаешь, почему я зелёный? Потому что завидую твоему настроению сегодня! 💚",
    "Ррр! Перевод: ты лучший(ая), и это научный факт 🧪",
]

DINO_THEMED_PHRASES = {
    "pizza": [
        "Динозавры вымерли, а моя любовь к пицце — никогда! Ррр-пепперони! 🍕🦖",
        "День пиццы! Я дежурный по печке — уже съел три с утра! 😋",
        "Ррр! Пицца без корочки — как динозавр без хвоста: невозможно! 🍕",
    ],
    "new_year": [
        "Ррр! С Новым годом! Желаю столько пиццы, сколько поместится в пасть! 🎄",
        "Дино уже под ёлкой! Подарки будут? Я умею делать «ррр»! 🎄",
        "Новый год — новые пиццы! Это моя философия! 🎆",
    ],
    "love": [
        "Ррр-любовь! Дино дарит тебе самое большое сердце! 💚",
        "Ты лучше всех цветов юрского периода! 💐",
        "Дино влюблён — и это очень милый динозавр! 🦖💘",
    ],
    "spring": [
        "Дино любит весну! И труд — особенно когда после него пицца! 🌷",
        "Ррр-весна! Пора греть спинку на солнышке! 🌞",
    ],
    "knowledge": [
        "Дино любит учиться! Сегодня выучу слово «диета»… и забуду! 📚",
        "Ррр! Знания — сила, а пицца — энергия! 🎓",
    ],
    "halloween": [
        "Бу! …Шучу, я добрый динозавр-привидение! Конфеты или рык! 🎃🦖",
        "Дино нарядился скелетом — получилось очень правдоподобно! 💀",
    ],
    "patriot": [
        "Дино чтит память героев! Мир — это когда пиццу никто не отбирает! 🕊️",
        "Ррр! Вместе мы съедим любую пиццу — в этом и есть единство! 🤝",
    ],
    "space": [
        "Дино мечтает о космосе! Метеориты — это же космическая пицца! 🚀",
    ],
    "humor": [
        "Дино шутит: я не большой, я просто хорошо кушаю! А ещё я спрятал твой степлер! 😄",
        "Ррр! Почему динозавр не играет в прятки? Потому что его всегда видно издалека! 🦖",
    ],
    "children": [
        "Дино любит играть с детьми! Кто со мной в догонялки через миллион лет? 🎈",
    ],
    "marketing": [
        "Ррр! Сегодня мой день — ведь я главный маркетолог юрского периода! 📣",
    ],
}

# Ключевые слова в названии -> тематический пул (порядок важен)
_THEME_KEYWORDS = [
    (("пицц",), "pizza"),
    (("новым годом", "новый год", "соельник", "канун"), "new_year"),
    (("валентин", "женский", "8 марта", "любви", "семьи", "поцелуя"), "love"),
    (("весны", "труда", "подснежник", "тюльпан", "лето"), "spring"),
    (("знаний", "учител", "студент", "книг", "грамот", "школьн"), "knowledge"),
    (("хэллоуин",), "halloween"),
    (("защитника", "побед", "единства", "россии", "флаг", "героев"), "patriot"),
    (("космонавт", "гагарин"), "space"),
    (("смех", "апрел", "юмор", "фокус", "клоун", "комед"), "humor"),
    (("дет",), "children"),
    (("маркетолог",), "marketing"),
]

# =============================================================================
# ЗАГРУЗКА JSON
# =============================================================================

@lru_cache(maxsize=1)
def _load_holidays():
    """Загружает holidays.json один раз и кэширует."""
    holidays_path = Path(__file__).parent.parent / "holidays.json"
    if holidays_path.exists():
        with open(holidays_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# =============================================================================
# ПЛАВАЮЩИЕ ДАТЫ
# =============================================================================

def _nth_weekday(year: int, month: int, weekday: int, n: int) -> datetime:
    """n-й нужный день недели месяца (weekday: пн=0 … вс=6)."""
    first = datetime(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _floating_holiday(d: datetime):
    """Возвращает полный dict плавающего праздника или None."""
    base = {
        "theme": None, "button": None, "popup": None,
        "animation": None, "sound": None, "mascot": {}, "secret": None,
    }
    if d.month == 6 and d.date() == _nth_weekday(d.year, 6, 4, 1).date():
        return {**base, "title": "День пончиков", "emoji": "🍩",
                "message": "Сладкий день!", "effects": []}
    if d.month == 7 and d.date() == _nth_weekday(d.year, 7, 6, 3).date():
        return {**base, "title": "День мороженого", "emoji": "🍦",
                "message": "Холодный и вкусный день!", "effects": []}
    if MASLENITSA_DATES.get(d.year) == d.strftime("%m-%d"):
        return {**base, "title": "Масленица", "emoji": "🥞",
                "message": "С Масленицей! Весёлых блинов и весеннего настроения!",
                "effects": ["confetti"]}
    return None

# =============================================================================
# ФРАЗА ДИНО
# =============================================================================

def _pick_dino_phrase(title: str, seed: str) -> str:
    """Подбирает игривую фразу Дино по названию праздника (детерминированно)."""
    t = (title or "").lower()
    pool = None
    for keywords, name in _THEME_KEYWORDS:
        if any(k in t for k in keywords):
            pool = DINO_THEMED_PHRASES.get(name)
            break
    if not pool:
        pool = DINO_BASE_PHRASES
    return random.Random(seed + title).choice(pool)

# =============================================================================
# СБОРКА ПРАЗДНИКА ДЛЯ ДАТЫ
# =============================================================================

def _holiday_for_date(d: datetime):
    """Собирает полный dict праздника для даты (json -> плавающие) или None."""
    key = d.strftime("%m-%d")
    data = _load_holidays().get(key)
    holiday = None

    if isinstance(data, dict):
        mascot = data.get("mascot") if isinstance(data.get("mascot"), dict) else {}
        holiday = {
            "title": data.get("title", "Праздник"),
            "emoji": data.get("emoji", ""),
            "message": data.get("message", ""),
            "effects": data.get("effects", []) or [],
            "theme": data.get("theme"),
            "button": data.get("button"),
            # popup оставляем в данных для совместимости, но UI его больше не рендерит
            "popup": data.get("popup"),
            "animation": None,
            "sound": None,
            "mascot": mascot,
            "secret": data.get("secret"),
        }
    elif isinstance(data, str):
        holiday = {
            "title": data, "emoji": "", "message": data, "effects": [],
            "theme": None, "button": None, "popup": None,
            "animation": None, "sound": None, "mascot": {}, "secret": None,
        }
    else:
        holiday = _floating_holiday(d)

    if holiday is None:
        return None

    # 1-е числа месяца — автоматически богатые (конфетти), если не прописаны вручную
    if d.day == 1 and not holiday.get("effects") and not (holiday.get("mascot") or {}).get("text"):
        holiday["effects"] = ["confetti"]

    # Фраза Дино — всегда (если нет своей в json)
    if not (holiday.get("mascot") or {}).get("text"):
        seed = f"{d.year}-{key}"
        holiday["mascot"] = {"text": _pick_dino_phrase(holiday.get("title", ""), seed)}

    return holiday

# =============================================================================
# ПУБЛИЧНЫЙ API
# =============================================================================

def get_today_holiday():
    """Возвращает информацию о сегодняшнем празднике (МСК) или None."""
    return _holiday_for_date(datetime.now(MSK))


def get_upcoming_holidays(days=5):
    """Возвращает список предстоящих праздников (json + плавающие).

    По умолчанию — 5 дней вперёд (договорённость).
    """
    today = datetime.now(MSK)
    upcoming = []
    for i in range(1, days + 1):
        d = today + timedelta(days=i)
        h = _holiday_for_date(d)
        if h:
            upcoming.append({
                "date": d.strftime("%d.%m"),
                "title": h["title"],
                "emoji": h.get("emoji", ""),
            })
    return upcoming


__all__ = [
    "MSK",
    "MASLENITSA_DATES",
    "DINO_BASE_PHRASES",
    "DINO_THEMED_PHRASES",
    "get_today_holiday",
    "get_upcoming_holidays",
]