# report/complaints/data.py

"""
Слой данных отчёта «Анализ жалоб».

Принимает загруженные файлы (site_file, agg_file, geo_file, os_file),
читает их, нормализует, фильтрует по датам и дедуплицирует по телефону.

Возвращает ComplaintsPreparedData:
- reviews      — нормализованные отзывы (для позитива);
- complaints   — жалобы без дублей;
- duplicates   — вырезанные дубли по телефону;
- deleted_geo  — удалённые отзывы геосервисов;
- warnings     — предупреждения.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd

# ----------------------------------------------------------
# ИМПОРТ КОНСТАНТ
# ----------------------------------------------------------
try:
    from . import constants as c
except Exception:
    try:
        from report.complaints import constants as c
    except Exception:
        c = None

try:
    from report.kr.constants import (
        COMPLAINT_KEYWORDS,
        RESTAURANT_MAP_FILE1,
        ADDRESS_MAP,
    )
except Exception:
    COMPLAINT_KEYWORDS = {}
    RESTAURANT_MAP_FILE1 = {}
    ADDRESS_MAP = {}


def _const(name: str, default: Any) -> Any:
    if c is not None and hasattr(c, name):
        return getattr(c, name)
    return default


OS_SHEET_NAME = _const("OS_SHEET_NAME", "Обращения")
COMPLAINT_MAX_RATING = _const("COMPLAINT_MAX_RATING", 3)
OS_COMPLAINT_NORMALIZE = _const("OS_COMPLAINT_NORMALIZE", {})
RESTAURANT_NUMBER_MAP = _const("RESTAURANT_NUMBER_MAP", {})
NAME_TO_NUMBER = {name: num for num, name in RESTAURANT_NUMBER_MAP.items()}


# ----------------------------------------------------------
# КОНТЕЙНЕР
# ----------------------------------------------------------
@dataclass
class ComplaintsPreparedData:
    reviews: pd.DataFrame
    complaints: pd.DataFrame
    duplicates: pd.DataFrame
    deleted_geo: pd.DataFrame
    warnings: List[str] = field(default_factory=list)

    def add_warning(self, message: str) -> None:
        message = str(message or "").strip()
        if message and message not in self.warnings:
            self.warnings.append(message)


# ----------------------------------------------------------
# ЧТЕНИЕ ФАЙЛОВ (принимает и файл, и DataFrame)
# ----------------------------------------------------------
def _to_dataframe(source: Any, sheet_name: Any = 0) -> Optional[pd.DataFrame]:
    if source is None:
        return None
    if isinstance(source, pd.DataFrame):
        return source
    try:
        return pd.read_excel(source, sheet_name=sheet_name)
    except Exception:
        try:
            return pd.read_excel(source)
        except Exception:
            return None


def _read_os(source: Any) -> Optional[pd.DataFrame]:
    if source is None:
        return None
    if isinstance(source, pd.DataFrame):
        return source
    try:
        return pd.read_excel(source, sheet_name=OS_SHEET_NAME)
    except Exception:
        try:
            return pd.read_excel(source)
        except Exception:
            return None


# ----------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ
# ----------------------------------------------------------
def normalize_phone(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return ""
    if len(digits) == 11 and digits[0] in "78":
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def _parse_review_date(value: Any) -> Optional[date]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(str(value), dayfirst=True).date()
    except Exception:
        return None


def _parse_os_date(value: Any, start_date: Optional[date], end_date: Optional[date]) -> Optional[date]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
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
    years: List[int] = []
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


def _map_file1(value: Any) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return RESTAURANT_MAP_FILE1.get(str(value).strip())


def _map_address(value: Any) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    v = str(value).lower()
    for key, name in ADDRESS_MAP.items():
        if key in v:
            return name
    return None


def _match_category(text: Any) -> Optional[str]:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    s = str(text)
    for cat, pattern in COMPLAINT_KEYWORDS.items():
        try:
            if re.search(pattern, s, flags=re.IGNORECASE):
                return cat
        except Exception:
            continue
    return None


def _in_range(d: Optional[date], start_date: Optional[date], end_date: Optional[date]) -> bool:
    if d is None:
        return True
    if start_date and d < start_date:
        return False
    if end_date and d > end_date:
        return False
    return True


# ----------------------------------------------------------
# ЗАГРУЗКА ИСТОЧНИКОВ ОТЗЫВОВ
# ----------------------------------------------------------
def _load_reviews(df: Optional[pd.DataFrame], source: str,
                  start_date: Optional[date], end_date: Optional[date],
                  rest_col: str, rest_mapper, text_col: str,
                  rating_col: str, phone_col: Optional[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Дата", "Источник", "Ресторан", "Номер ресторана", "Рейтинг", "Текст", "Телефон"])

    out = pd.DataFrame()
    out["Дата"] = df.get("Дата" if "Дата" in df.columns else df.columns[0]).map(_parse_review_date) \
        if source != "site" else df.get("Date", pd.Series([None] * len(df))).map(_parse_review_date)
    out["Источник"] = source
    out["Ресторан"] = df.get(rest_col, pd.Series([None] * len(df))).map(rest_mapper)
    out["Номер ресторана"] = out["Ресторан"].map(lambda n: NAME_TO_NUMBER.get(n))
    out["Рейтинг"] = pd.to_numeric(df.get(rating_col, pd.Series([None] * len(df))), errors="coerce")
    out["Текст"] = df.get(text_col, pd.Series([""] * len(df))).fillna("")
    out["Телефон"] = df.get(phone_col, pd.Series([None] * len(df))).map(normalize_phone) if phone_col else ""

    out = out[out["Ресторан"].notna()]
    out = out[out["Дата"].map(lambda d: _in_range(d, start_date, end_date))]
    return out


def _load_site(df, start_date, end_date):
    if df is None or df.empty:
        return pd.DataFrame(columns=["Дата", "Источник", "Ресторан", "Номер ресторана", "Рейтинг", "Текст", "Телефон"])
    out = pd.DataFrame()
    out["Дата"] = df.get("Date", pd.Series([None] * len(df))).map(_parse_review_date)
    out["Источник"] = "Сайт"
    out["Ресторан"] = df.get("Ресторан", pd.Series([None] * len(df))).map(_map_file1)
    out["Номер ресторана"] = out["Ресторан"].map(lambda n: NAME_TO_NUMBER.get(n))
    out["Рейтинг"] = pd.to_numeric(df.get("Рейтинг", pd.Series([None] * len(df))), errors="coerce")
    out["Текст"] = df.get("Комментарий", pd.Series([""] * len(df))).fillna("")
    out["Телефон"] = df.get("Телефон", pd.Series([None] * len(df))).map(normalize_phone)
    out = out[out["Ресторан"].notna()]
    out = out[out["Дата"].map(lambda d: _in_range(d, start_date, end_date))]
    return out


def _load_agg(df, start_date, end_date):
    return _load_reviews(df, "Агрегаторы", start_date, end_date,
                         "Адрес", _map_address, "Отзыв", "Оценка", None)


def _load_geo(df, start_date, end_date):
    if df is None or df.empty:
        empty = pd.DataFrame(columns=["Дата", "Источник", "Ресторан", "Номер ресторана", "Рейтинг", "Текст", "Телефон"])
        return empty, pd.DataFrame(columns=["Дата", "Ресторан", "Текст", "Статус отзыва"])

    status_col = "Статус отзыва" if "Статус отзыва" in df.columns else None
    deleted_mask = pd.Series([False] * len(df), index=df.index)
    if status_col:
        deleted_mask = df[status_col].astype(str).str.strip().str.lower() == "удален"

    deleted = df[deleted_mask]
    deleted_out = pd.DataFrame({
        "Дата": deleted.get("Дата написания отзыва", pd.Series([None] * len(deleted))).map(_parse_review_date),
        "Ресторан": deleted.get("Адрес филиала", pd.Series([None] * len(deleted))).map(_map_address),
        "Текст": deleted.get("Текст отзыва", pd.Series([""] * len(deleted))).fillna(""),
        "Статус отзыва": deleted.get(status_col, pd.Series([""] * len(deleted))).fillna(""),
    })

    active = df[~deleted_mask]
    reviews = _load_reviews(active, "Геосервисы", start_date, end_date,
                            "Адрес филиала", _map_address, "Текст отзыва", "Оценка",
                            "Книга отзывов - Номер телефона автора")
    return reviews, deleted_out


def _load_os(df, start_date, end_date, warnings):
    cols = ["Дата", "Телефон", "Ресторан", "Номер ресторана", "Вид жалобы", "Текст", "Источник"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)

    date_col = OS_SHEET_NAME and (df.columns[0] if "Дата" not in df.columns else "Дата")
    rows = []
    for _, r in df.iterrows():
        # пропускаем повторные шапки
        phone_raw = r.get("Номер телефона")
        complaint_raw = r.get("Жалоба")
        if str(phone_raw).strip() == "Номер телефона" or str(complaint_raw).strip() == "Жалоба":
            continue
        if pd.isna(complaint_raw) and pd.isna(phone_raw):
            continue

        d = _parse_os_date(r.get(date_col), start_date, end_date)
        if not _in_range(d, start_date, end_date):
            continue

        num_raw = r.get("Ресторан")
        num = pd.to_numeric(num_raw, errors="coerce")
        num_int = int(num) if not pd.isna(num) else None
        name = RESTAURANT_NUMBER_MAP.get(num_int) if num_int is not None else None

        cat_raw = str(complaint_raw).strip()
        category = OS_COMPLAINT_NORMALIZE.get(cat_raw.lower(), cat_raw)

        rows.append({
            "Дата": d,
            "Телефон": normalize_phone(phone_raw),
            "Ресторан": name,
            "Номер ресторана": num_int,
            "Вид жалобы": category,
            "Текст": str(r.get("Комментарий") or ""),
            "Источник": "ОС",
        })

    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


# ----------------------------------------------------------
# ДЕДУПЛИКАЦИЯ ПО ТЕЛЕФОНУ
# ----------------------------------------------------------
def _dedup_by_phone(complaints: pd.DataFrame):
    cols = list(complaints.columns)
    if complaints.empty:
        return complaints, pd.DataFrame(columns=cols + ["Причина дубля"])

    seen = set()
    kept = []
    dups = []
    for _, r in complaints.iterrows():
        phone = r.get("Телефон") or ""
        if phone:
            if phone in seen:
                row = r.to_dict()
                row["Причина дубля"] = "Совпадение номера телефона"
                dups.append(row)
                continue
            seen.add(phone)
        kept.append(r.to_dict())

    kept_df = pd.DataFrame(kept, columns=cols) if kept else pd.DataFrame(columns=cols)
    dups_df = pd.DataFrame(dups, columns=cols + ["Причина дубля"]) if dups else pd.DataFrame(columns=cols + ["Причина дубля"])
    return kept_df, dups_df


# ----------------------------------------------------------
# ГЛАВНАЯ ФУНКЦИЯ
# ----------------------------------------------------------
def prepare_complaints_data(
    site_file: Any = None,
    agg_file: Any = None,
    geo_file: Any = None,
    os_file: Any = None,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
    # алиасы для совместимости со старыми вызовами
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> ComplaintsPreparedData:
    # date_start/date_end — основные имена (их передаёт builder),
    # start_date/end_date — алиасы для обратной совместимости.
    start_date = date_start if date_start is not None else start_date
    end_date = date_end if date_end is not None else end_date

    warnings: List[str] = []

    site_df = _to_dataframe(site_file)
    agg_df = _to_dataframe(agg_file)
    geo_df = _to_dataframe(geo_file)
    os_df = _read_os(os_file)

    reviews_site = _load_site(site_df, start_date, end_date)
    reviews_agg = _load_agg(agg_df, start_date, end_date)
    reviews_geo, deleted_geo = _load_geo(geo_df, start_date, end_date)

    reviews = pd.concat([reviews_site, reviews_agg, reviews_geo], ignore_index=True)

    # Жалобы из отзывов: рейтинг <= max И совпадение с категорией
    review_complaint_rows = []
    for _, r in reviews.iterrows():
        rating = r.get("Рейтинг")
        if rating is None or pd.isna(rating) or rating > COMPLAINT_MAX_RATING:
            continue
        category = _match_category(r.get("Текст"))
        if category is None:
            continue
        review_complaint_rows.append({
            "Дата": r.get("Дата"),
            "Телефон": r.get("Телефон") or "",
            "Ресторан": r.get("Ресторан"),
            "Номер ресторана": r.get("Номер ресторана"),
            "Вид жалобы": category,
            "Текст": r.get("Текст"),
            "Источник": r.get("Источник"),
        })

    review_complaints = pd.DataFrame(review_complaint_rows)

    os_complaints = _load_os(os_df, start_date, end_date, warnings)

    # ОС сначала — они имеют приоритет при дедупликации
    combined = pd.concat([os_complaints, review_complaints], ignore_index=True)
    complaints, duplicates = _dedup_by_phone(combined)

    if not duplicates.empty:
        warnings.append(f"Дублей по номеру телефона: {len(duplicates)}.")

    return ComplaintsPreparedData(
        reviews=reviews,
        complaints=complaints,
        duplicates=duplicates,
        deleted_geo=deleted_geo,
        warnings=warnings,
    )