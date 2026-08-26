# report/complaints/data.py

"""
Слой данных отчёта «Анализ жалоб».

Принимает загруженные файлы (site_file, agg_file, geo_file, os_file
+ опциональный os_tmn_file), читает их, нормализует, фильтрует по датам
и дедуплицирует по телефону.

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
TMN_OS_RESTAURANT_NUMBER_MAP = _const("TMN_OS_RESTAURANT_NUMBER_MAP", {})
CLOSED_RESTAURANT_NUMBERS = _const("CLOSED_RESTAURANT_NUMBERS", set())
NAME_TO_NUMBER = {name: num for num, name in RESTAURANT_NUMBER_MAP.items()}

# Единая схема столбцов жалобы (используется для ОС, ОС Тюмени и жалоб из отзывов).
# Решение/Статус возмещения/Сотрудник — только для строк из ОС-файлов;
# у жалоб из отзывов эти поля всегда пустые (там нет workflow компенсаций).
COMPLAINT_COLS = [
    "Дата", "Телефон", "Ресторан", "Номер ресторана", "Вид жалобы", "Текст", "Источник",
    "Решение", "Статус возмещения", "Сотрудник",
]


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
    s = str(value)
    # Строки вида "2026-08-01" или "2026-08-01T07:59:11+0300" уже однозначны
    # (год впереди) — dayfirst тут не нужен и на формате с временем/TZ
    # заставляет pandas путать месяц и день (01.08 <-> 08.01).
    dayfirst = not re.match(r"^\d{4}-\d{1,2}-\d{1,2}", s)
    try:
        return pd.to_datetime(s, dayfirst=dayfirst).date()
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


def _has_value(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, float) and pd.isna(v):
        return False
    return str(v).strip() != ""


def _clean_str(value: Any) -> Optional[str]:
    """Строка без NaN: `value or ""` не годится — NaN истинно, `str(NaN)` даёт текст "nan"."""
    return str(value).strip() if _has_value(value) else None


def _warn_unmapped(raw: pd.Series, mapped: pd.Series, warnings: Optional[List[str]], label: str) -> None:
    """Предупреждает, если строки с заполненным рестораном не удалось замаппить (и они выпадут из отчёта)."""
    if warnings is None:
        return
    has_raw = raw.map(_has_value)
    count = int((has_raw & mapped.isna()).sum())
    if count:
        warnings.append(
            f"«{label}»: не удалось определить ресторан для {count} строк(и) — они не попали в отчёт."
        )


def _parse_bool(value: Any) -> Optional[bool]:
    """Статус возмещения: TRUE/FALSE из Excel, либо текстовые варианты. None — если не указано."""
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


# ----------------------------------------------------------
# ЗАГРУЗКА ИСТОЧНИКОВ ОТЗЫВОВ
# ----------------------------------------------------------
def _warn_missing_columns(
    df: pd.DataFrame,
    expected: Dict[str, Optional[str]],
    label: str,
    warnings: Optional[List[str]],
) -> None:
    """Предупреждает, если ожидаемых столбцов нет в файле СОВСЕМ (не просто пустые/
    нераспознанные значения) — иначе источник молча даёт 0 без единой подсказки."""
    if warnings is None or df is None:
        return
    missing = [name for name, col in expected.items() if col and col not in df.columns]
    if not missing:
        return
    cols_preview = ", ".join(f'"{c}"' for c in list(df.columns)[:12])
    more = "…" if len(df.columns) > 12 else ""
    warnings.append(
        f"«{label}»: не найдены ожидаемые столбцы: {', '.join(missing)}. "
        f"Столбцы в файле: {cols_preview}{more}."
    )


def _load_reviews(df: Optional[pd.DataFrame], source: str,
                  start_date: Optional[date], end_date: Optional[date],
                  rest_col: str, rest_mapper, text_col: str,
                  rating_col: str, phone_col: Optional[str],
                  date_col: str = "Дата",
                  warnings: Optional[List[str]] = None, label: Optional[str] = None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Дата", "Источник", "Ресторан", "Номер ресторана", "Рейтинг", "Текст", "Телефон"])

    out = pd.DataFrame()
    out["Дата"] = df.get(date_col, pd.Series([None] * len(df))).map(_parse_review_date)
    out["Источник"] = source
    raw_rest = df.get(rest_col, pd.Series([None] * len(df)))
    out["Ресторан"] = raw_rest.map(rest_mapper)
    out["Номер ресторана"] = out["Ресторан"].map(lambda n: NAME_TO_NUMBER.get(n))
    out["Рейтинг"] = pd.to_numeric(df.get(rating_col, pd.Series([None] * len(df))), errors="coerce")
    out["Текст"] = df.get(text_col, pd.Series([""] * len(df))).fillna("")
    out["Телефон"] = df.get(phone_col, pd.Series([None] * len(df))).map(normalize_phone) if phone_col else ""

    _warn_unmapped(raw_rest, out["Ресторан"], warnings, label or source)
    _warn_missing_columns(
        df,
        {"ресторан/адрес": rest_col, "текст отзыва": text_col, "оценка": rating_col, "дата": date_col},
        label or source, warnings,
    )

    out = out[out["Ресторан"].notna()]
    out = out[out["Дата"].map(lambda d: _in_range(d, start_date, end_date))]
    return out


def _load_site(df, start_date, end_date, warnings: Optional[List[str]] = None):
    if df is None or df.empty:
        return pd.DataFrame(columns=["Дата", "Источник", "Ресторан", "Номер ресторана", "Рейтинг", "Текст", "Телефон"])
    out = pd.DataFrame()
    out["Дата"] = df.get("Date", pd.Series([None] * len(df))).map(_parse_review_date)
    out["Источник"] = "Сайт"
    raw_rest = df.get("Ресторан", pd.Series([None] * len(df)))
    out["Ресторан"] = raw_rest.map(_map_file1)
    out["Номер ресторана"] = out["Ресторан"].map(lambda n: NAME_TO_NUMBER.get(n))
    out["Рейтинг"] = pd.to_numeric(df.get("Рейтинг", pd.Series([None] * len(df))), errors="coerce")
    out["Текст"] = df.get("Комментарий", pd.Series([""] * len(df))).fillna("")
    out["Телефон"] = df.get("Телефон", pd.Series([None] * len(df))).map(normalize_phone)

    _warn_unmapped(raw_rest, out["Ресторан"], warnings, "Сайт/приложение")
    _warn_missing_columns(
        df,
        {"ресторан": "Ресторан", "комментарий": "Комментарий", "рейтинг": "Рейтинг", "дата": "Date"},
        "Сайт/приложение", warnings,
    )

    out = out[out["Ресторан"].notna()]
    out = out[out["Дата"].map(lambda d: _in_range(d, start_date, end_date))]
    return out


def _load_agg(df, start_date, end_date, warnings: Optional[List[str]] = None):
    if df is None or df.empty:
        return _load_reviews(df, "Агрегаторы", start_date, end_date,
                             "Адрес", _map_address, "Отзыв", "Оценка", None,
                             warnings=warnings, label="Агрегаторы")

    df = df.copy()

    # Некоторые выгрузки агрегаторов (Яндекс Еда/Delivery Club) не содержат
    # колонку "Дата" — время создания отзыва там называется иначе.
    date_col = "Дата" if "Дата" in df.columns else (
        "Время создания отзыва" if "Время создания отзыва" in df.columns else "Дата"
    )

    # В этих же выгрузках свободный текст "Отзыв" часто пуст — гость просто
    # отмечает готовые комментарии чекбоксами в "Предвыбранные комментарии".
    # Добавляем их к тексту, чтобы ключевые слова категорий жалоб их видели.
    if "Предвыбранные комментарии" in df.columns:
        preset = df["Предвыбранные комментарии"].fillna("").astype(str)
        free_text = df.get("Отзыв", pd.Series([""] * len(df))).fillna("").astype(str)
        df["Отзыв"] = (free_text + " " + preset).str.strip()

    return _load_reviews(df, "Агрегаторы", start_date, end_date,
                         "Адрес", _map_address, "Отзыв", "Оценка", None,
                         date_col=date_col,
                         warnings=warnings, label="Агрегаторы")


def _load_geo(df, start_date, end_date, warnings: Optional[List[str]] = None):
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
                            "Книга отзывов - Номер телефона автора",
                            date_col="Дата написания отзыва",
                            warnings=warnings, label="Геосервисы")
    return reviews, deleted_out


def _load_os(df, start_date, end_date, warnings: Optional[List[str]] = None, label: str = "ОС и компенсации"):
    cols = COMPLAINT_COLS
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)

    date_col = OS_SHEET_NAME and (df.columns[0] if "Дата" not in df.columns else "Дата")
    rows = []
    unmapped = 0
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
        # Закрытые рестораны намеренно отсутствуют в справочнике — это не
        # ошибка маппинга, предупреждать о них не нужно.
        if name is None and _has_value(num_raw) and num_int not in CLOSED_RESTAURANT_NUMBERS:
            unmapped += 1

        cat_raw = _clean_str(complaint_raw) or ""
        category = OS_COMPLAINT_NORMALIZE.get(cat_raw.lower(), cat_raw) if cat_raw else ""

        rows.append({
            "Дата": d,
            "Телефон": normalize_phone(phone_raw),
            "Ресторан": name,
            "Номер ресторана": num_int,
            "Вид жалобы": category,
            "Текст": _clean_str(r.get("Комментарий")) or "",
            "Источник": "ОС",
            "Решение": _clean_str(r.get("Решение")),
            "Статус возмещения": _parse_bool(r.get("Статус возмещения")),
            # В актуальной выгрузке столбец называется иначе, чем в файле
            # Тюмени — "ФИО сотрудника" оставлен как запасной вариант для
            # старых/иных форматов файла.
            "Сотрудник": _clean_str(r.get("Имя в системе 1С ответственного (полностью)"))
                or _clean_str(r.get("ФИО сотрудника")),
        })

    if unmapped and warnings is not None:
        warnings.append(
            f"«{label}»: не удалось определить ресторан для {unmapped} строк(и) — они не попали в отчёт."
        )

    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


def _load_os_tmn(df, start_date, end_date, warnings: Optional[List[str]] = None, label: str = "ОС Тюмень"):
    """Необязательный файл «ОС Тюмень».

    Формат отличается от основного файла ОС:
    - в начале листа идут пример заполнения и повторная шапка
      (реальные данные начинаются сразу после последнего такого
      повтора — ищем его и берём всё, что ниже);
    - ресторан задан текстом «Тюмень 2» / «Тюмень 3» (номер —
      собственная нумерация, см. TMN_OS_RESTAURANT_NUMBER_MAP);
    - вместо номера телефона — «Номер заказа» (по факту тоже
      телефон в формате 7XXXXXXXXXX, поэтому дедуплицируем
      той же normalize_phone, что и остальные источники).
    """
    cols = COMPLAINT_COLS
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)

    date_col = "Дата" if "Дата" in df.columns else df.columns[0]
    order_col = "Номер заказа" if "Номер заказа" in df.columns else (
        df.columns[1] if len(df.columns) > 1 else None
    )

    if order_col is not None:
        header_repeats = df.index[
            (df[date_col].astype(str).str.strip() == "Дата")
            & (df[order_col].astype(str).str.strip() == "Номер заказа")
        ]
        if len(header_repeats) > 0:
            df = df.loc[df.index > header_repeats[-1]]

    rows = []
    unmapped = 0
    for _, r in df.iterrows():
        complaint_raw = r.get("Жалоба")
        rest_raw = r.get("Ресторан")
        if not _has_value(complaint_raw) and not _has_value(rest_raw):
            continue

        d = _parse_os_date(r.get(date_col), start_date, end_date)
        if not _in_range(d, start_date, end_date):
            continue

        num_match = re.search(r"\d+", str(rest_raw)) if _has_value(rest_raw) else None
        num_int = int(num_match.group()) if num_match else None
        name = TMN_OS_RESTAURANT_NUMBER_MAP.get(num_int) if num_int is not None else None
        if name is None and _has_value(rest_raw):
            unmapped += 1

        cat_raw = _clean_str(complaint_raw) or ""
        category = OS_COMPLAINT_NORMALIZE.get(cat_raw.lower(), cat_raw) if cat_raw else ""

        order_raw = r.get(order_col) if order_col else None

        rows.append({
            "Дата": d,
            "Телефон": normalize_phone(order_raw),
            "Ресторан": name,
            "Номер ресторана": NAME_TO_NUMBER.get(name),
            "Вид жалобы": category,
            "Текст": _clean_str(r.get("Комментарий")) or "",
            "Источник": label,
            "Решение": _clean_str(r.get("Решение")),
            "Статус возмещения": _parse_bool(r.get("Статус возмещения")),
            "Сотрудник": _clean_str(r.get("ФИО сотрудника")),
        })

    if unmapped and warnings is not None:
        warnings.append(
            f"«{label}»: не удалось определить ресторан для {unmapped} строк(и) — они не попали в отчёт."
        )

    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


# ----------------------------------------------------------
# АВТООПРЕДЕЛЕНИЕ ФОРМАТА ФАЙЛА ОС (СПб vs Тюмень) — для общего загрузчика
# ----------------------------------------------------------
def classify_os_upload(file: Any) -> str:
    """Определяет формат загруженного файла «ОС»: "main" (СПб, лист "Обращения"),
    "tyumen" (есть столбец "Номер заказа") или "unknown", если не удалось понять.
    Файл должен поддерживать seek(0) (как st.file_uploader)."""
    try:
        file.seek(0)
        pd.read_excel(file, sheet_name=OS_SHEET_NAME)
        return "main"
    except Exception:
        pass

    try:
        file.seek(0)
        df = pd.read_excel(file)
        if "Номер заказа" in df.columns:
            return "tyumen"
    except Exception:
        pass
    finally:
        try:
            file.seek(0)
        except Exception:
            pass

    return "unknown"


def split_os_files(files):
    """Разносит список загруженных файлов «ОС» по форматам: СПб (лист "Обращения")
    и Тюмень (столбец "Номер заказа") — используется UI-страницами Complaints и ОС,
    чтобы не дублировать логику маршрутизации файлов по загрузчикам."""
    file_main, file_tmn = None, None
    for f in files or []:
        kind = classify_os_upload(f)
        if kind == "tyumen" and file_tmn is None:
            file_tmn = f
        elif file_main is None:
            file_main = f
        elif file_tmn is None:
            file_tmn = f
    return file_main, file_tmn


# ----------------------------------------------------------
# ДЕДУПЛИКАЦИЯ: ОДИН ЗАКАЗ + ОДНА КАТЕГОРИЯ ЖАЛОБЫ = ОДИН ТИКЕТ
# ----------------------------------------------------------
def _dedup_by_phone(complaints: pd.DataFrame):
    """Схлопывает повторные записи одного и того же тикета: если по одному
    заказу (телефон/номер) внесено несколько строк с ОДНОЙ И ТОЙ ЖЕ категорией
    жалобы — в сводную попадает только первая, остальные уходят в «Дубликаты».
    Разные категории по одному заказу дублями не считаются и остаются все."""
    cols = list(complaints.columns)
    if complaints.empty:
        return complaints, pd.DataFrame(columns=cols + ["Причина дубля"])

    seen = set()
    kept = []
    dups = []
    for _, r in complaints.iterrows():
        phone = r.get("Телефон") or ""
        category = r.get("Вид жалобы") or ""
        key = (phone, category)
        if phone:
            if key in seen:
                row = r.to_dict()
                row["Причина дубля"] = "Совпадение заказа и категории жалобы"
                dups.append(row)
                continue
            seen.add(key)
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
    os_tmn_file: Any = None,
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
    os_tmn_df = _to_dataframe(os_tmn_file)

    reviews_site = _load_site(site_df, start_date, end_date, warnings)
    reviews_agg = _load_agg(agg_df, start_date, end_date, warnings)
    reviews_geo, deleted_geo = _load_geo(geo_df, start_date, end_date, warnings)

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
            # У жалоб из отзывов нет workflow компенсаций — поля всегда пустые.
            "Решение": None,
            "Статус возмещения": None,
            "Сотрудник": None,
        })

    review_complaints = pd.DataFrame(review_complaint_rows)

    os_complaints = _load_os(os_df, start_date, end_date, warnings)
    os_tmn_complaints = _load_os_tmn(os_tmn_df, start_date, end_date, warnings)

    # ОС сначала — они имеют приоритет при дедупликации
    combined = pd.concat([os_complaints, os_tmn_complaints, review_complaints], ignore_index=True)
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