"""
Слой данных модуля «Контроль жалоб» (ТЗ §2, §4.1, §4.6).

Загружает и нормализует все 5 источников:
- главная таблица СПб («ОС и компенсации», лист «Обращения» + «Сводная»);
- главная таблица Тюмень («Обратная_связь_Тюмень», лист «Лист1»);
- чат «Гости ОС Тюмень» (CSV);
- чат «Обратная связь Гости» (CSV, СПб);
- issues_report (Excel, вся сеть).

Без Streamlit и openpyxl-стилей — только pandas.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from . import constants as c
from .phone import normalize_phone, find_phones_in_text


# ============================================================
# ЧТЕНИЕ ФАЙЛОВ
# ============================================================
def _read_excel_sheet(source: Any, sheet_name: Any = 0) -> Optional[pd.DataFrame]:
    if source is None:
        return None
    if isinstance(source, pd.DataFrame):
        return source
    try:
        source.seek(0)
    except Exception:
        pass
    try:
        return pd.read_excel(source, sheet_name=sheet_name)
    except Exception:
        try:
            source.seek(0)
        except Exception:
            pass
        try:
            return pd.read_excel(source)
        except Exception:
            return None


def _read_excel_raw(source: Any, sheet_name: Any = 0) -> Optional[pd.DataFrame]:
    """Без парсинга заголовка — для листов со сдвинутой шапкой (Тюмень)."""
    if source is None:
        return None
    try:
        source.seek(0)
    except Exception:
        pass
    try:
        return pd.read_excel(source, sheet_name=sheet_name, header=None)
    except Exception:
        return None


def _read_csv_any_encoding(source: Any) -> Optional[pd.DataFrame]:
    if source is None:
        return None
    if isinstance(source, pd.DataFrame):
        return source
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            source.seek(0)
        except Exception:
            pass
        try:
            return pd.read_csv(source, encoding=enc)
        except Exception:
            continue
    return None


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ============================================================
def _has_value(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, float) and pd.isna(v):
        return False
    return str(v).strip() != ""


def _clean_str(value: Any) -> str:
    return str(value).strip() if _has_value(value) else ""


_COST_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)")


def parse_cost(value: Any) -> Optional[float]:
    """Стоимость компенсации: число, либо мусор вроде "35 см" — берём
    только ведущее число, отбрасываем нечисловое (ТЗ §2.1, столбец 9)."""
    if not _has_value(value):
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    m = _COST_RE.match(str(value))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def _parse_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if not _has_value(value):
        return None
    s = str(value).strip().lower()
    if s in ("true", "1", "да", "yes"):
        return True
    if s in ("false", "0", "нет", "no"):
        return False
    return None


def _parse_main_date(value: Any, start_date: Optional[date], end_date: Optional[date]) -> Optional[date]:
    """Дата в главных таблицах: обычно полная дата, иногда короткая dd.mm
    (без года) — используем период отчёта, чтобы подобрать год."""
    if not _has_value(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    m = re.match(r"^(\d{1,2})[./](\d{1,2})$", s)
    if not m:
        try:
            return pd.to_datetime(s, dayfirst=True).date()
        except Exception:
            return None
    day, month = int(m.group(1)), int(m.group(2))
    years = []
    if start_date:
        years.append(start_date.year)
    if end_date and end_date.year not in years:
        years.append(end_date.year)
    if not years:
        years = [datetime.now().year]
    for y in years:
        try:
            cand = date(y, month, day)
        except ValueError:
            continue
        if start_date and cand < start_date:
            continue
        if end_date and cand > end_date:
            continue
        return cand
    return None


def _in_range(d: Optional[date], start_date: Optional[date], end_date: Optional[date]) -> bool:
    if d is None:
        return True
    if start_date and d < start_date:
        return False
    if end_date and d > end_date:
        return False
    return True


# ============================================================
# СПРАВОЧНИК РЕСТОРАНОВ СПБ — ЛИСТ «СВОДНАЯ» (ТЗ §2.1)
# ============================================================
_RESTAURANT_LINE_RE = re.compile(r"(\d+)\s+(.*)")


def parse_restaurant_map(summary_df: Optional[pd.DataFrame]) -> Dict[int, str]:
    """Парсит лист «Сводная»/«Сводная неделя»: ячейки вида "01 Транспортный",
    "18 Науки " (с пробелами). НЕ хардкодится — маппинг может меняться при
    открытии новых точек, поэтому парсится заново при каждой загрузке."""
    mapping: Dict[int, str] = {}
    if summary_df is None or summary_df.empty:
        return mapping
    for value in summary_df.values.flatten():
        if not _has_value(value):
            continue
        m = _RESTAURANT_LINE_RE.match(str(value).strip())
        if not m:
            continue
        try:
            num = int(m.group(1))
        except ValueError:
            continue
        name = m.group(2).strip()
        if name:
            mapping.setdefault(num, name)
    return mapping


def _load_restaurant_map_from_file(file: Any, warnings: Optional[List[str]]) -> Dict[int, str]:
    # header=None: лист «Сводная» — не табличные данные с формальной шапкой,
    # первая строка может содержать код ресторана (например, "01 Транспортный") —
    # обычный pd.read_excel съел бы её как имя столбца и потерял бы запись.
    for sheet in c.OS_SUMMARY_SHEET_CANDIDATES:
        df = _read_excel_raw(file, sheet_name=sheet)
        mapping = parse_restaurant_map(df)
        if mapping:
            return mapping
    if warnings is not None:
        warnings.append(
            "«ОС и компенсации» (СПб): не найден лист «Сводная» — расшифровка "
            "номеров ресторанов недоступна, в отчёте останутся числовые коды."
        )
    return {}


# ============================================================
# ГЛАВНАЯ ТАБЛИЦА СПБ (лист «Обращения», ТЗ §2.1)
# ============================================================
MAIN_COLS = [
    "Дата", "Телефон", "Город", "Источник", "Ресторан", "Номер ресторана",
    "Вид жалобы", "Вид позиции", "Текст", "Решение", "Стоимость компенсации",
    "Статус возмещения", "Сотрудник", "Отклонение", "Комментарий2",
]


def load_main_spb(file: Any, warnings: Optional[List[str]] = None) -> pd.DataFrame:
    """Главная таблица СПб. Фильтрует по непустой «Жалоба» — таблица «живёт»
    и растёт, хвост пустых строк-заготовок нужно отбросить (ТЗ §2.1)."""
    if file is None:
        return pd.DataFrame(columns=MAIN_COLS)

    restaurant_map = _load_restaurant_map_from_file(file, warnings)
    df = _read_excel_sheet(file, sheet_name=c.OS_SHEET_NAME)
    if df is None or df.empty:
        if warnings is not None:
            warnings.append("«ОС и компенсации» (СПб): не удалось прочитать лист «Обращения».")
        return pd.DataFrame(columns=MAIN_COLS)

    date_col = "Дата" if "Дата" in df.columns else df.columns[0]
    phone_col = "Номер телефона" if "Номер телефона" in df.columns else (
        df.columns[1] if len(df.columns) > 1 else None
    )

    rows = []
    unmapped = 0
    for _, r in df.iterrows():
        complaint_raw = r.get("Жалоба")
        if not _has_value(complaint_raw):
            continue
        if str(complaint_raw).strip() == "Жалоба":
            continue  # повторная шапка

        num = pd.to_numeric(r.get("Ресторан"), errors="coerce")
        num_int = int(num) if not pd.isna(num) else None
        rest_name = restaurant_map.get(num_int) if num_int is not None else None
        if rest_name is None and num_int is not None:
            unmapped += 1

        phone_raw = r.get(phone_col) if phone_col else None

        rows.append({
            "Дата": r.get(date_col),
            "Телефон": normalize_phone(phone_raw),
            "Город": "Санкт-Петербург",
            "Источник": _clean_str(r.get("источник")),
            "Ресторан": rest_name,
            "Номер ресторана": num_int,
            "Вид жалобы": _clean_str(complaint_raw),
            "Вид позиции": _clean_str(r.get("Вид позиции")),
            "Текст": _clean_str(r.get("Комментарий")),
            "Решение": _clean_str(r.get("Решение")) or None,
            "Стоимость компенсации": parse_cost(r.get("Стоимость компенсации")),
            "Статус возмещения": _parse_bool(r.get("Статус возмещения")),
            "Сотрудник": _clean_str(r.get("Имя в системе 1С ответственного")) or None,
            "Отклонение": _clean_str(r.get("Отклонение")) or None,
            "Комментарий2": _clean_str(r.get("Комментарий (если нет отклонения)"))
                or _clean_str(r.get("Комментарий2")) or None,
        })

    if unmapped and warnings is not None:
        warnings.append(
            f"«ОС и компенсации» (СПб): не удалось определить ресторан для {unmapped} строк(и) "
            "(нет в листе «Сводная»)."
        )

    out = pd.DataFrame(rows, columns=MAIN_COLS) if rows else pd.DataFrame(columns=MAIN_COLS)
    return out


# ============================================================
# ГЛАВНАЯ ТАБЛИЦА ТЮМЕНЬ (лист «Лист1», ТЗ §2.2)
# ============================================================
def _find_tyumen_header_row(raw: pd.DataFrame) -> int:
    """Реальные данные начинаются с 7-й строки (1-6 — шапка/пример).
    Ищем строку-заголовок динамически (первая ячейка == "Дата"), с
    запасным вариантом — жёстко 6-я строка (индекс 5)."""
    max_scan = min(len(raw), 10)
    for i in range(max_scan):
        first_cell = str(raw.iloc[i, 0]).strip() if raw.shape[1] > 0 else ""
        if first_cell == "Дата":
            return i
    return 5  # запасной вариант: строка 6 (0-based) = 7-я строка файла


def load_main_tyumen(file: Any, warnings: Optional[List[str]] = None) -> pd.DataFrame:
    if file is None:
        return pd.DataFrame(columns=MAIN_COLS)

    raw = _read_excel_raw(file, sheet_name=c.TMN_SHEET_NAME)
    if raw is None or raw.empty:
        if warnings is not None:
            warnings.append("«Обратная_связь_Тюмень»: не удалось прочитать лист «Лист1».")
        return pd.DataFrame(columns=MAIN_COLS)

    header_row = _find_tyumen_header_row(raw)
    headers = [str(h).strip() for h in raw.iloc[header_row].tolist()]
    df = raw.iloc[header_row + 1:].copy()
    df.columns = headers

    def col(name: str, idx: int):
        if name in df.columns:
            return df[name]
        if idx < df.shape[1]:
            return df.iloc[:, idx]
        return pd.Series([None] * len(df), index=df.index)

    dates = col("Дата", 0)
    orders = col("Номер заказа", 1)
    rests = col("Ресторан", 2)
    complaints = col("Жалоба", 3)
    comments = col("Комментарий", 4)
    decisions = col("Решение", 5)
    costs = col("Стоимость компенсации", 6)
    refunds = col("Статус возмещения", 7)
    staff = col("ФИО сотрудника", 8)

    rows = []
    for i in df.index:
        complaint_raw = complaints.get(i)
        if not _has_value(complaint_raw):
            continue

        rest_raw = rests.get(i)
        rest_name = _clean_str(rest_raw)
        if not rest_name:
            continue
        if rest_name.strip().lower() in c.TMN_EXCLUDED_RESTAURANTS:
            continue  # «Сочи» — не наш город (ТЗ §2.2)

        rows.append({
            "Дата": dates.get(i),
            "Телефон": normalize_phone(orders.get(i)),
            "Город": "Тюмень",
            "Источник": "",
            "Ресторан": rest_name,
            "Номер ресторана": None,
            "Вид жалобы": _clean_str(complaint_raw),
            "Вид позиции": "",
            "Текст": _clean_str(comments.get(i)),
            "Решение": _clean_str(decisions.get(i)) or None,
            "Стоимость компенсации": parse_cost(costs.get(i)),
            "Статус возмещения": _parse_bool(refunds.get(i)),
            "Сотрудник": _clean_str(staff.get(i)) or None,
            "Отклонение": None,  # поля нет в тюменской таблице
            "Комментарий2": None,
        })

    if not rows:
        return pd.DataFrame(columns=MAIN_COLS)
    return pd.DataFrame(rows, columns=MAIN_COLS)


def finalize_main_table(df: pd.DataFrame, start_date: Optional[date], end_date: Optional[date]) -> pd.DataFrame:
    """Парсит даты (с учётом коротких dd.mm) и фильтрует по периоду."""
    if df.empty:
        return df
    out = df.copy()
    out["Дата"] = out["Дата"].map(lambda v: _parse_main_date(v, start_date, end_date))
    out = out[out["Дата"].map(lambda d: _in_range(d, start_date, end_date))]
    return out


# ============================================================
# ЧАТЫ (CSV, ТЗ §2.3, §2.4)
# ============================================================
def _is_meta_message(text: str) -> bool:
    """Мета-сообщение (автоматический аналитический отчёт, вставленный в
    канал вручную) — не жалоба гостя (ТЗ §2.4)."""
    return "[b]" in text or "|---|" in text


def load_chat_messages(file: Any, source_label: str, warnings: Optional[List[str]] = None) -> pd.DataFrame:
    """Читает CSV-экспорт чата поддержки. Возвращает сырые сообщения
    (без группировки) с колонками: Дата, Автор, Текст, Источник."""
    cols = ["Дата", "Автор", "Текст", "Источник"]
    if file is None:
        return pd.DataFrame(columns=cols)

    df = _read_csv_any_encoding(file)
    if df is None or df.empty:
        if warnings is not None:
            warnings.append(f"«{source_label}»: не удалось прочитать CSV.")
        return pd.DataFrame(columns=cols)

    author_col = "Автор" if "Автор" in df.columns else None
    text_col = "Текст сообщения" if "Текст сообщения" in df.columns else (
        "Текст" if "Текст" in df.columns else None
    )
    date_col = "Дата" if "Дата" in df.columns else None

    if author_col is None or text_col is None or date_col is None:
        if warnings is not None:
            warnings.append(
                f"«{source_label}»: не найдены ожидаемые столбцы (Дата/Автор/Текст сообщения)."
            )
        return pd.DataFrame(columns=cols)

    out = pd.DataFrame()
    out["Дата"] = pd.to_datetime(df[date_col], errors="coerce", utc=True).dt.tz_localize(None)
    out["Автор"] = df[author_col].fillna("")
    out["Текст"] = df[text_col].fillna("").astype(str)
    out["Источник"] = source_label

    out = out[out["Автор"].str.strip() != "Система"]
    out = out[~out["Текст"].map(_is_meta_message)]
    return out


# ============================================================
# ГРУППИРОВКА ПО (ТЕЛЕФОН, ДЕНЬ) — ТЗ §4.6
# ============================================================
GROUPED_COLS = ["Телефон", "Дата", "Авторы", "Текст", "Кол-во сообщений", "Источник"]


def group_messages_by_phone_day(messages: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame):
    """Возвращает (grouped, no_phone). `grouped` — одна строка на
    (телефон, календарный день); `no_phone` — сообщения без определённого
    телефона (статус «нужна ручная проверка»)."""
    if messages is None or messages.empty:
        return pd.DataFrame(columns=GROUPED_COLS), pd.DataFrame(columns=["Дата", "Автор", "Текст", "Источник"])

    work = messages.copy()
    work["_phones"] = work["Текст"].map(find_phones_in_text)
    work["_phone"] = work["_phones"].map(lambda lst: lst[0] if lst else "")
    work["_day"] = work["Дата"].map(lambda d: d.date() if pd.notna(d) else None)

    no_phone = work[(work["_phone"] == "")][["Дата", "Автор", "Текст", "Источник"]].copy()

    has_phone = work[(work["_phone"] != "") & (work["_day"].notna())]
    if has_phone.empty:
        return pd.DataFrame(columns=GROUPED_COLS), no_phone

    rows = []
    for (phone, day), grp in has_phone.groupby(["_phone", "_day"]):
        rows.append({
            "Телефон": phone,
            "Дата": day,
            "Авторы": ", ".join(sorted(set(a for a in grp["Автор"] if a))),
            "Текст": " || ".join(t for t in grp["Текст"] if t),
            "Кол-во сообщений": len(grp),
            "Источник": grp["Источник"].iloc[0],
        })
    return pd.DataFrame(rows, columns=GROUPED_COLS), no_phone


# ============================================================
# issues_report (Excel, ТЗ §2.5)
# ============================================================
ISSUES_COLS = [
    "№", "Номер обращения", "Дата отзыва", "Статус", "Исполнитель", "Город",
    "Ресторан", "Источник", "Причина обращения", "Телефон", "E-mail",
    "Первичное сообщение",
]


def load_issues_report(file: Any, warnings: Optional[List[str]] = None) -> pd.DataFrame:
    if file is None:
        return pd.DataFrame(columns=ISSUES_COLS)

    df = _read_excel_sheet(file)
    if df is None or df.empty:
        if warnings is not None:
            warnings.append("«issues_report»: не удалось прочитать файл.")
        return pd.DataFrame(columns=ISSUES_COLS)

    missing = [col for col in ISSUES_COLS if col not in df.columns]
    if missing and warnings is not None:
        warnings.append(f"«issues_report»: не найдены столбцы: {', '.join(missing)}.")

    out = pd.DataFrame()
    for col in ISSUES_COLS:
        out[col] = df[col] if col in df.columns else None

    out["Дата отзыва"] = pd.to_datetime(out["Дата отзыва"], errors="coerce", utc=True).dt.tz_localize(None)

    # Только СПб и Тюмень — в файле есть Москва, Казань и др. (ТЗ §2.5, п.6)
    city = out["Город"].astype(str).str.strip()
    out = out[city.isin(["Санкт-Петербург", "Тюмень"])]

    out["Телефон"] = out["Телефон"].map(normalize_phone)
    return out
