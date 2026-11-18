"""
Слой данных модуля «Контроль жалоб» (проверка внесения жалоб).

Источники по действующим правилам (ред. 18.11.2026) — только чаты ресторанов
Битрикс24 и Google-таблицы СПб/Тюмени; CRM в этой проверке не используется:
- главная таблица СПб («ОС и компенсации», лист «Обращения» + «Сводная»);
- главная таблица Тюмень («Обратная_связь_Тюмень», лист «Лист1»);
- чат «Гости ОС Тюмень» (CSV);
- чат «Обратная связь Гости» (CSV, СПб).

Ключевая колонка таблиц («Номер телефона» СПб / «Номер заказа» Тюмень)
содержит вперемешку телефоны и номера заказов — разбираются оба ключа.

Без Streamlit и openpyxl-стилей — только pandas.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from . import constants as c
from .phone import normalize_phone, find_phones_in_text, find_orders_in_text, parse_key_cell


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
    "Дата", "Телефон", "Заказ", "Город", "Источник", "Ресторан", "Номер ресторана",
    "Вид жалобы", "Категория", "Вид позиции", "Текст", "Решение", "Стоимость компенсации",
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
        keys = parse_key_cell(phone_raw)

        rows.append({
            "Дата": r.get(date_col),
            "Телефон": keys["phone"],
            "Заказ": keys["order_id"],
            "Город": "Санкт-Петербург",
            "Источник": _clean_str(r.get("источник")),
            "Ресторан": rest_name,
            "Номер ресторана": num_int if num_int is not None else keys["rest"],
            "Вид жалобы": _clean_str(complaint_raw),
            "Категория": c.normalize_table_category(complaint_raw),
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

        keys = parse_key_cell(orders.get(i))
        rest_num = pd.to_numeric(rest_raw, errors="coerce")
        rest_num = int(rest_num) if not pd.isna(rest_num) else keys["rest"]

        rows.append({
            "Дата": dates.get(i),
            "Телефон": keys["phone"],
            "Заказ": keys["order_id"],
            "Город": "Тюмень",
            "Источник": "",
            "Ресторан": rest_name,
            "Номер ресторана": rest_num,
            "Вид жалобы": _clean_str(complaint_raw),
            "Категория": c.normalize_table_category(complaint_raw),
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
    """Парсит даты (с учётом коротких dd.mm), но НЕ фильтрует по периоду:
    по действующим правилам сверяется вся доступная основная таблица,
    включая старые строки и строки без даты. Период ограничивает только
    источник жалоб (чаты), а не таблицу для сопоставления."""
    if df.empty:
        return df
    out = df.copy()
    out["Дата"] = out["Дата"].map(lambda v: _parse_main_date(v, start_date, end_date))
    return out


# ============================================================
# ЧАТЫ (CSV, ТЗ §2.3, §2.4)
# ============================================================
def _is_meta_message(text: str) -> bool:
    """Мета-сообщения — не жалобы гостя: автоматические аналитические
    отчёты, вставленные в канал, и уведомления Битрикс о создании задачи
    по сообщению (они цитируют исходную жалобу и задваивали бы её)."""
    return (
        "[b]" in text or "|---|" in text
        or "создал задачу на основании" in text
        or "[USER=" in text or "[CONTEXT=" in text
    )


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

    out = out[~out["Автор"].str.strip().isin(["Система", "id0"])]
    out = out[~out["Текст"].map(_is_meta_message)]
    return out


# ============================================================
# ГРУППИРОВКА: (ЗАКАЗ ИЛИ ТЕЛЕФОН, ДЕНЬ) + ПОВТОРЫ ОДНОГО ВОПРОСА
# ============================================================
GROUPED_COLS = [
    "Телефон", "Заказ", "Тикеты", "Дата", "Авторы", "Текст",
    "Кол-во сообщений", "Источник",
]


def group_messages(messages: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame):
    """Возвращает (grouped, no_keys).

    Группировка по действующим правилам («повторы одного вопроса в
    переписке объединять»):
    - сообщения с номером заказа группируются по (заказ, день), даже если
      телефон не указан — заказ сам по себе сильный ключ;
    - остальные — по (телефон, день);
    - группы одного дня с общим телефоном объединяются;
    - группы с одним заказом в разные дни объединяются (повтор вопроса);
    - сообщения без телефона и без заказа — `no_keys` (ручная проверка).
    """
    empty_grouped = pd.DataFrame(columns=GROUPED_COLS)
    no_keys_cols = ["Дата", "Автор", "Текст", "Источник"]
    if messages is None or messages.empty:
        return empty_grouped, pd.DataFrame(columns=no_keys_cols)

    work = messages.copy()
    work["_phones"] = work["Текст"].map(find_phones_in_text)
    work["_orders"] = work["Текст"].map(find_orders_in_text)
    work["_phone"] = work["_phones"].map(lambda lst: lst[0] if lst else "")
    work["_order"] = work["_orders"].map(lambda lst: lst[0]["order_id"] if lst else "")
    work["_day"] = work["Дата"].map(lambda d: d.date() if pd.notna(d) else None)

    no_keys = work[(work["_phone"] == "") & (work["_order"] == "")][no_keys_cols].copy()
    keyed = work[(work["_phone"] != "") | (work["_order"] != "")].copy()
    keyed = keyed[keyed["_day"].notna()]
    if keyed.empty:
        return empty_grouped, no_keys

    # Рестораны часто пишут номер заказа, телефон и суть отдельными
    # репликами подряд. Сообщение только с заказом, стоящее рядом (≤5 мин)
    # с сообщением с телефоном того же дня, относим к этому телефону —
    # иначе одна жалоба распалась бы на несколько групп.
    phone_rows = keyed[keyed["_phone"] != ""]
    order_only = keyed[(keyed["_order"] != "") & (keyed["_phone"] == "")]
    for idx, row in order_only.iterrows():
        same_day = phone_rows[phone_rows["_day"] == row["_day"]]
        if same_day.empty:
            continue
        deltas = (same_day["Дата"] - row["Дата"]).abs()
        near = same_day[deltas <= pd.Timedelta(minutes=5)]
        near_phones = near["_phone"].unique()
        if len(near_phones) == 1:
            keyed.at[idx, "_phone"] = near_phones[0]
            keyed.at[idx, "_phones"] = list(row["_phones"]) + [near_phones[0]]

    # Первичные группы: заказ важнее телефона.
    keyed["_gkey"] = keyed.apply(
        lambda r: ("o", r["_order"]) if r["_order"] else ("p", r["_phone"]), axis=1,
    )
    groups: Dict[Any, Dict[str, Any]] = {}
    for (gkey, day), grp in keyed.groupby(["_gkey", "_day"], sort=False):
        phones = {p for lst in grp["_phones"] for p in lst}
        orders = {o["order_id"]: o for lst in grp["_orders"] for o in lst}
        groups[(gkey, day)] = {
            "day": day,
            "phones": phones,
            "orders": orders,
            "authors": set(a for a in grp["Автор"] if a),
            "texts": [t for t in grp["Текст"] if t],
            "count": len(grp),
            "source": grp["Источник"].iloc[0],
        }

    # Объединение групп одного дня по общему телефону (union-find).
    parent: Dict[Any, Any] = {k: k for k in groups}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            lo, hi = sorted([ra, rb], key=str)
            parent[hi] = lo

    by_phone_day: Dict[Any, List[Any]] = {}
    for gkey, g in groups.items():
        for p in g["phones"]:
            by_phone_day.setdefault((p, g["day"]), []).append(gkey)
    for same_day_keys in by_phone_day.values():
        for other in same_day_keys[1:]:
            union(same_day_keys[0], other)

    merged: Dict[Any, Dict[str, Any]] = {}
    for gkey, g in groups.items():
        root = find(gkey)
        if root not in merged:
            merged[root] = {
                "day": g["day"], "phones": set(g["phones"]),
                "orders": dict(g["orders"]), "authors": set(g["authors"]),
                "texts": list(g["texts"]), "count": g["count"],
                "source": g["source"],
            }
        else:
            m = merged[root]
            m["phones"] |= g["phones"]
            m["orders"].update(g["orders"])
            m["authors"] |= g["authors"]
            m["texts"] += g["texts"]
            m["count"] += g["count"]
            m["day"] = min(m["day"], g["day"])

    # Повторы одного заказа в разные дни — одна жалоба.
    by_order: Dict[str, List[Any]] = {}
    for gkey, g in merged.items():
        for oid in g["orders"]:
            by_order.setdefault(oid, []).append(gkey)
    for gkeys in by_order.values():
        if len(gkeys) < 2:
            continue
        roots = sorted({find(k) for k in gkeys}, key=str)
        main_key = roots[0]
        for other in roots[1:]:
            g, o = merged[main_key], merged[other]
            g["phones"] |= o["phones"]
            g["orders"].update(o["orders"])
            g["authors"] |= o["authors"]
            g["texts"] += o["texts"]
            g["count"] += o["count"]
            g["day"] = min(g["day"], o["day"])
            del merged[other]

    rows = []
    for g in merged.values():
        order_ids = sorted(g["orders"])
        rows.append({
            "Телефон": sorted(g["phones"])[0] if g["phones"] else "",
            "Заказ": order_ids[0] if order_ids else "",
            "Тикеты": ", ".join(g["orders"][oid]["raw"] for oid in order_ids),
            "Дата": g["day"],
            "Авторы": ", ".join(sorted(g["authors"])),
            "Текст": " || ".join(g["texts"]),
            "Кол-во сообщений": g["count"],
            "Источник": g["source"],
        })
    grouped = pd.DataFrame(rows, columns=GROUPED_COLS)
    grouped = grouped.sort_values("Дата").reset_index(drop=True)
    return grouped, no_keys
