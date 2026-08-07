# report/kr/data.py

"""
Загрузка и подготовка данных для модуля КР.

Ответственность файла:
- чтение Excel-файлов;
- маппинг ресторанов;
- нормализация колонок;
- фильтрация данных по датам для недельного отчёта;
- исключение удалённых отзывов из геосервисов для месячного отчёта;
- подготовка DataFrame для дальнейших расчётов.

Здесь не должно быть:
- Streamlit;
- Excel-генерации;
- расчёта итоговых таблиц;
- анализа отзывов по ключевым словам.
"""

from __future__ import annotations

from typing import Any, List, Optional

import pandas as pd

# ==========================================================
# ИМПОРТ КОНСТАНТ
# ==========================================================
try:
    from . import constants as c
except Exception:
    from report.kr import constants as c

# ==========================================================
# ИМПОРТ МОДЕЛЕЙ
# ==========================================================
try:
    from .models import KRPreparedData, KRReportSettings, KRSourceFiles
except Exception:
    from report.kr.models import KRPreparedData, KRReportSettings, KRSourceFiles


# ==========================================================
# ЛОКАЛЬНЫЕ ССЫЛКИ НА КОНСТАНТЫ
# ==========================================================
MODE_MONTH = getattr(c, "MODE_MONTH", "month")
MODE_WEEK = getattr(c, "MODE_WEEK", "week")

SOURCE_SITE = getattr(c, "SOURCE_SITE", "site")
SOURCE_AGG = getattr(c, "SOURCE_AGG", "agg")
SOURCE_GEO = getattr(c, "SOURCE_GEO", "geo")

DEFAULT_SOURCE_LABELS = {
    SOURCE_SITE: "Сайт",
    SOURCE_AGG: "Агрегаторы",
    SOURCE_GEO: "Геосервисы",
}

SOURCE_LABELS = getattr(c, "SOURCE_LABELS", DEFAULT_SOURCE_LABELS)

SITE_RESTAURANT_COLUMN = getattr(c, "SITE_RESTAURANT_COLUMN", "Ресторан")
SITE_RATING_COLUMN = getattr(c, "SITE_RATING_COLUMN", "Рейтинг")
SITE_COMMENT_COLUMN = getattr(c, "SITE_COMMENT_COLUMN", "Комментарий")
SITE_SUM_COLUMN = getattr(c, "SITE_SUM_COLUMN", "Сумма заказа со скидкой")
SITE_DATE_COLUMN = getattr(c, "SITE_DATE_COLUMN", "Date")

AGG_ADDRESS_COLUMN = getattr(c, "AGG_ADDRESS_COLUMN", "Адрес")
AGG_RATING_COLUMN = getattr(c, "AGG_RATING_COLUMN", "Оценка")
AGG_REVIEW_COLUMN = getattr(c, "AGG_REVIEW_COLUMN", "Отзыв")
AGG_DATE_COLUMN = getattr(c, "AGG_DATE_COLUMN", "Время создания отзыва")

GEO_BRANCH_NAME_COLUMN = getattr(c, "GEO_BRANCH_NAME_COLUMN", "Название филиала")
GEO_BRANCH_ADDRESS_COLUMN = getattr(c, "GEO_BRANCH_ADDRESS_COLUMN", "Адрес филиала")
GEO_FEED_NAME_COLUMN = getattr(c, "GEO_FEED_NAME_COLUMN", "Название из фида")
GEO_RATING_COLUMN = getattr(c, "GEO_RATING_COLUMN", "Оценка")
GEO_TEXT_COLUMN = getattr(c, "GEO_TEXT_COLUMN", "Текст отзыва")
GEO_STATUS_COLUMN = getattr(c, "GEO_STATUS_COLUMN", "Статус отзыва")
GEO_DATE_COLUMN = getattr(c, "GEO_DATE_COLUMN", "Дата написания отзыва")

DEFAULT_SOURCE_DATE_COLUMNS = {
    SOURCE_SITE: SITE_DATE_COLUMN,
    SOURCE_AGG: AGG_DATE_COLUMN,
    SOURCE_GEO: GEO_DATE_COLUMN,
}

SOURCE_DATE_COLUMNS = getattr(c, "SOURCE_DATE_COLUMNS", DEFAULT_SOURCE_DATE_COLUMNS)

COL_RESTAURANT = getattr(c, "COL_RESTAURANT", "Ресторан")
COL_RATING = getattr(c, "COL_RATING", "Рейтинг")
COL_TEXT = getattr(c, "COL_TEXT", "Текст")
COL_SUM = getattr(c, "COL_SUM", "Сумма")

RESTAURANT_MAP_FILE1 = getattr(c, "RESTAURANT_MAP_FILE1", {})
ADDRESS_MAP = getattr(c, "ADDRESS_MAP", {})
DELETED_STATUSES = getattr(c, "DELETED_STATUSES", {"удален", "удалён"})

DATE_MISSING_WARNING_TEMPLATE = getattr(
    c,
    "DATE_MISSING_WARNING_TEMPLATE",
    "{source}: строк без даты — {count}; они включены в отчёт.",
)

DATE_COLUMN_MISSING_WARNING_TEMPLATE = getattr(
    c,
    "DATE_COLUMN_MISSING_WARNING_TEMPLATE",
    "{source}: колонка '{column}' не найдена, фильтр по датам пропущен.",
)


# ==========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================================
def _is_blank(value: Any) -> bool:
    """
    Проверяет, является ли значение пустым/NaN/None.
    """
    try:
        if value is None or pd.isna(value):
            return True
    except Exception:
        if value is None:
            return True

    return not str(value).strip()


def _normalize_text(value: Any) -> str:
    """
    Возвращает очищенный текст значения.
    """
    if _is_blank(value):
        return ""

    return str(value).strip()


def _require_columns(df: pd.DataFrame, columns: List[str], source_label: str) -> None:
    """
    Проверяет наличие обязательных колонок в DataFrame.
    """
    missing = [column for column in columns if column not in df.columns]

    if missing:
        raise ValueError(
            f"{source_label}: не найдены обязательные колонки: {', '.join(missing)}."
        )


def read_source_excel(file_obj: Any, source_label: str) -> pd.DataFrame:
    """
    Читает Excel-файл источника и возвращает DataFrame.
    """
    try:
        return pd.read_excel(file_obj)
    except Exception as exc:
        raise ValueError(
            f"{source_label}: не удалось прочитать Excel-файл. {exc}"
        ) from exc


# ==========================================================
# МАППИНГ РЕСТОРАНОВ
# ==========================================================
def map_restaurant_file1(value: Any) -> Optional[str]:
    """
    Маппинг ресторана из файла сайта.
    """
    if _is_blank(value):
        return None

    key = _normalize_text(value)

    if not key:
        return None

    return RESTAURANT_MAP_FILE1.get(key, None)


def map_restaurant_address(value: Any) -> Optional[str]:
    """
    Маппинг ресторана по адресу.
    Используется для агрегаторов и геосервисов.
    """
    if _is_blank(value):
        return None

    text = _normalize_text(value).lower()

    if not text:
        return None

    for key, restaurant in ADDRESS_MAP.items():
        if str(key).lower() in text:
            return restaurant

    return None


# ==========================================================
# РАЗБОР СУММЫ ЗАКАЗА
# ==========================================================
def parse_price(value: Any) -> Optional[float]:
    """
    Приводит сумму заказа к float.

    Примеры:
    - "5,800" -> 5800.0
    - "1 954" -> 1954.0
    - "749" -> 749.0
    """
    if _is_blank(value):
        return None

    text = str(value).strip().replace(" ", "")

    if not text:
        return None

    # Обработка случая, когда запятая используется как десятичный разделитель.
    if "," in text and "." not in text:
        parts = text.split(",")

        if len(parts) == 2 and len(parts[1]) <= 2:
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")

    # Если есть и точка, и запятая, считаем запятую разделителем тысяч.
    elif "," in text and "." in text:
        text = text.replace(",", "")

    try:
        return float(text)
    except Exception:
        return None


# ==========================================================
# ФИЛЬТРАЦИЯ ПО ДАТАМ
# ==========================================================
def filter_dataframe_by_period(
    df: pd.DataFrame,
    source_key: str,
    start_date: Optional[Any],
    end_date: Optional[Any],
    warnings: List[str],
) -> pd.DataFrame:
    """
    Фильтрует DataFrame по датам.

    Правила:
    - если период не задан, возвращаем исходный DataFrame;
    - если колонка с датой не найдена, возвращаем исходный DataFrame
      и добавляем предупреждение;
    - строки без даты НЕ исключаем, а учитываем и добавляем предупреждение.
    """
    if df is None or df.empty:
        return df

    if not start_date or not end_date:
        return df

    source_label = SOURCE_LABELS.get(source_key, source_key)
    date_column = SOURCE_DATE_COLUMNS.get(source_key)

    if not date_column:
        return df

    if date_column not in df.columns:
        warnings.append(
            DATE_COLUMN_MISSING_WARNING_TEMPLATE.format(
                source=source_label,
                column=date_column,
            )
        )
        return df

    dt = pd.to_datetime(df[date_column], errors="coerce", utc=True)

    if getattr(dt.dt, "tz", None) is not None:
        try:
            dt = dt.dt.tz_convert("Europe/Moscow")
        except Exception:
            pass

    if getattr(dt.dt, "tz", None) is not None:
        try:
            dt = dt.dt.tz_localize(None)
        except Exception:
            pass

    valid_date_mask = dt.notna()
    no_date_mask = ~valid_date_mask

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    in_period_mask = valid_date_mask & dt.between(start_ts, end_ts)

    filtered = df[in_period_mask | no_date_mask].copy()

    no_date_count = int(no_date_mask.sum())

    if no_date_count > 0:
        warnings.append(
            DATE_MISSING_WARNING_TEMPLATE.format(
                source=source_label,
                count=no_date_count,
            )
        )

    return filtered


# ==========================================================
# ПОДГОТОВКА САЙТА
# ==========================================================
def prepare_site_df(df: pd.DataFrame, include_sum: bool = False) -> pd.DataFrame:
    """
    Подготавливает данные из файла сайта.

    Возвращает колонки:
    - Ресторан;
    - Рейтинг;
    - Текст;
    - Сумма, если include_sum=True.
    """
    source_label = SOURCE_LABELS.get(SOURCE_SITE, "Сайт")

    required_columns = [
        SITE_RESTAURANT_COLUMN,
        SITE_RATING_COLUMN,
        SITE_COMMENT_COLUMN,
    ]

    if include_sum:
        required_columns.append(SITE_SUM_COLUMN)

    _require_columns(df, required_columns, source_label)

    out = pd.DataFrame()

    out[COL_RESTAURANT] = df[SITE_RESTAURANT_COLUMN].map(map_restaurant_file1)
    out[COL_RATING] = pd.to_numeric(df[SITE_RATING_COLUMN], errors="coerce")
    out[COL_TEXT] = df[SITE_COMMENT_COLUMN].fillna("").astype(str)

    if include_sum:
        out[COL_SUM] = df[SITE_SUM_COLUMN].map(parse_price)
    else:
        out[COL_SUM] = None

    out = out.dropna(subset=[COL_RESTAURANT, COL_RATING])

    return out.reset_index(drop=True)


# ==========================================================
# ПОДГОТОВКА АГРЕГАТОРОВ
# ==========================================================
def prepare_aggregators_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Подготавливает данные из файла агрегаторов.

    Возвращает колонки:
    - Ресторан;
    - Рейтинг;
    - Текст.
    """
    source_label = SOURCE_LABELS.get(SOURCE_AGG, "Агрегаторы")

    required_columns = [
        AGG_ADDRESS_COLUMN,
        AGG_RATING_COLUMN,
        AGG_REVIEW_COLUMN,
    ]

    _require_columns(df, required_columns, source_label)

    out = pd.DataFrame()

    out[COL_RESTAURANT] = df[AGG_ADDRESS_COLUMN].map(map_restaurant_address)
    out[COL_RATING] = pd.to_numeric(df[AGG_RATING_COLUMN], errors="coerce")
    out[COL_TEXT] = df[AGG_REVIEW_COLUMN].fillna("").astype(str)

    out = out.dropna(subset=[COL_RESTAURANT, COL_RATING])

    return out.reset_index(drop=True)


# ==========================================================
# ПОДГОТОВКА ГЕОСЕРВИСОВ
# ==========================================================
def prepare_geo_df(df: pd.DataFrame, include_deleted: bool = False) -> pd.DataFrame:
    """
    Подготавливает данные из файла геосервисов.

    Правила:
    - месяц: include_deleted=False, удалённые отзывы исключаем;
    - неделя: include_deleted=True, удалённые отзывы учитываем.

    Возвращает колонки:
    - Ресторан;
    - Рейтинг;
    - Текст.
    """
    source_label = SOURCE_LABELS.get(SOURCE_GEO, "Геосервисы")

    required_columns = [
        GEO_RATING_COLUMN,
        GEO_TEXT_COLUMN,
    ]

    _require_columns(df, required_columns, source_label)

    filtered = df.copy()

    if not include_deleted and GEO_STATUS_COLUMN in filtered.columns:
        status = (
            filtered[GEO_STATUS_COLUMN]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        filtered = filtered[~status.isin(DELETED_STATUSES)].copy()

    restaurants = pd.Series(None, index=filtered.index, dtype="object")

    # 1. Сначала пытаемся взять ресторан из поля "Название из фида".
    if GEO_FEED_NAME_COLUMN in filtered.columns:
        restaurants = filtered[GEO_FEED_NAME_COLUMN].map(map_restaurant_file1)

    # 2. Если не получилось — ищем по адресу филиала.
    if GEO_BRANCH_ADDRESS_COLUMN in filtered.columns:
        missing_mask = restaurants.isna()

        if missing_mask.any():
            restaurants[missing_mask] = (
                filtered.loc[missing_mask, GEO_BRANCH_ADDRESS_COLUMN]
                .map(map_restaurant_address)
            )

    # 3. Если всё ещё не получилось — ищем по названию филиала.
    if GEO_BRANCH_NAME_COLUMN in filtered.columns:
        missing_mask = restaurants.isna()

        if missing_mask.any():
            restaurants[missing_mask] = (
                filtered.loc[missing_mask, GEO_BRANCH_NAME_COLUMN]
                .map(map_restaurant_address)
            )

    out = pd.DataFrame(index=filtered.index)

    out[COL_RESTAURANT] = restaurants
    out[COL_RATING] = pd.to_numeric(filtered[GEO_RATING_COLUMN], errors="coerce")
    out[COL_TEXT] = filtered[GEO_TEXT_COLUMN].fillna("").astype(str)

    out = out.dropna(subset=[COL_RESTAURANT, COL_RATING])

    return out.reset_index(drop=True)


# ==========================================================
# ОБЪЕДИНЕНИЕ ТЕКСТОВ ДЛЯ АНАЛИЗА ОТЗЫВОВ
# ==========================================================
def get_combined_texts(prepared: KRPreparedData) -> pd.DataFrame:
    """
    Возвращает объединённые тексты отзывов по трём источникам.

    Колонки:
    - Ресторан;
    - Текст.
    """
    frames: List[pd.DataFrame] = []

    for df in (prepared.site, prepared.agg, prepared.geo):
        if df is None or df.empty:
            continue

        if COL_RESTAURANT not in df.columns or COL_TEXT not in df.columns:
            continue

        frames.append(df[[COL_RESTAURANT, COL_TEXT]].copy())

    if not frames:
        return pd.DataFrame(columns=[COL_RESTAURANT, COL_TEXT])

    return pd.concat(frames, ignore_index=True)


# ==========================================================
# ОСНОВНАЯ ЗАГРУЗКА ДАННЫХ
# ==========================================================
def load_kr_data(
    files: KRSourceFiles,
    settings: KRReportSettings,
) -> KRPreparedData:
    """
    Загружает и подготавливает данные для КР.

    Логика:
    - месяц:
        * данные не фильтруются по датам;
        * для сайта подготавливается сумма заказа;
        * удалённые отзывы из геосервисов исключаем.

    - неделя:
        * если выбран период, фильтруем данные по датам;
        * строки без даты учитываем и показываем предупреждение;
        * удалённые отзывы из геосервисов учитываем.
    """
    warnings: List[str] = []

    if not files.is_complete():
        missing = ", ".join(files.missing_labels())
        raise ValueError(f"Не загружены файлы: {missing}.")

    if settings.mode not in (MODE_MONTH, MODE_WEEK):
        raise ValueError(f"Некорректный режим отчёта: {settings.mode}.")

    if settings.is_month and settings.month is None:
        raise ValueError("Для месячного отчёта не переданы настройки месяца.")

    if settings.is_week and settings.week is None:
        raise ValueError("Для недельного отчёта не переданы настройки недели.")

    site_label = SOURCE_LABELS.get(SOURCE_SITE, "Сайт")
    agg_label = SOURCE_LABELS.get(SOURCE_AGG, "Агрегаторы")
    geo_label = SOURCE_LABELS.get(SOURCE_GEO, "Геосервисы")

    site_raw = read_source_excel(files.site, site_label)
    agg_raw = read_source_excel(files.agg, agg_label)
    geo_raw = read_source_excel(files.geo, geo_label)

    # ======================================================
    # ФИЛЬТР ПО ДАТАМ ТОЛЬКО ДЛЯ НЕДЕЛИ
    # ======================================================
    if settings.is_week and settings.week is not None and not settings.week.is_all_dates:
        start_date = settings.week.start_date
        end_date = settings.week.end_date

        if start_date and end_date and end_date < start_date:
            raise ValueError("Дата конца не может быть раньше даты начала.")

        site_raw = filter_dataframe_by_period(
            df=site_raw,
            source_key=SOURCE_SITE,
            start_date=start_date,
            end_date=end_date,
            warnings=warnings,
        )

        agg_raw = filter_dataframe_by_period(
            df=agg_raw,
            source_key=SOURCE_AGG,
            start_date=start_date,
            end_date=end_date,
            warnings=warnings,
        )

        geo_raw = filter_dataframe_by_period(
            df=geo_raw,
            source_key=SOURCE_GEO,
            start_date=start_date,
            end_date=end_date,
            warnings=warnings,
        )

    # ======================================================
    # ПОДГОТОВКА ДАННЫХ
    # ======================================================
    include_sum = bool(settings.is_month)
    include_deleted = bool(settings.is_week)

    site_df = prepare_site_df(site_raw, include_sum=include_sum)
    agg_df = prepare_aggregators_df(agg_raw)
    geo_df = prepare_geo_df(geo_raw, include_deleted=include_deleted)

    prepared = KRPreparedData(
        site=site_df,
        agg=agg_df,
        geo=geo_df,
        warnings=warnings,
    )

    return prepared