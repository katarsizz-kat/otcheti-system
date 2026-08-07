# report/kr/models.py

"""
Модели данных для модуля КР.

Здесь только структуры данных и вспомогательные преобразования:
- настройки месяца;
- настройки недели;
- загруженные файлы;
- результат формирования отчёта.

В этом файле не должно быть:
- Streamlit;
- openpyxl;
- бизнес-расчётов;
- генерации Excel.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

# ==========================================================
# ИМПОРТ КОНСТАНТ
# ==========================================================
try:
    from . import constants as c
except Exception:
    from report.kr import constants as c

MODE_MONTH = c.MODE_MONTH
MODE_WEEK = c.MODE_WEEK

SOURCE_SITE = c.SOURCE_SITE
SOURCE_AGG = c.SOURCE_AGG
SOURCE_GEO = c.SOURCE_GEO
SOURCE_LABELS = c.SOURCE_LABELS

PERIOD_ALL_DATES_LABEL = c.PERIOD_ALL_DATES_LABEL
MONTHS_GENITIVE = c.MONTHS_GENITIVE
DEFAULT_PRICE_THRESHOLD = c.DEFAULT_PRICE_THRESHOLD

DEFAULT_YEAR_MIN = getattr(c, "DEFAULT_YEAR_MIN", 2020)
DEFAULT_YEAR_MAX = getattr(c, "DEFAULT_YEAR_MAX", 2100)

MONTH_FILE_NAME_TEMPLATE = getattr(
    c,
    "MONTH_FILE_NAME_TEMPLATE",
    "КР_{month}_{year}.xlsx"
)

WEEK_FILE_NAME_TEMPLATE = getattr(
    c,
    "WEEK_FILE_NAME_TEMPLATE",
    "КР_неделя_{period}.xlsx"
)

# Московское время: UTC+3
MSK = timezone(timedelta(hours=3))


# ==========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================================
def sanitize_filename(value: str) -> str:
    """
    Делает строку безопасной для имени файла.
    """
    value = str(value or "")
    value = re.sub(r"[^\w\s\-]+", "", value, flags=re.UNICODE)
    value = value.strip().replace(" ", "_")

    while "__" in value:
        value = value.replace("__", "_")

    return value or "отчет"


def format_week_period_label(start_date: date, end_date: date) -> str:
    """
    Формирует человекочитаемую подпись периода недели.

    Примеры:
    - 1-9 августа 2026
    - 30 июня – 5 июля 2026
    - 28 декабря 2025 – 3 января 2026
    """
    if start_date.month == end_date.month and start_date.year == end_date.year:
        return (
            f"{start_date.day}-{end_date.day} "
            f"{MONTHS_GENITIVE[end_date.month - 1]} "
            f"{end_date.year}"
        )

    if start_date.year == end_date.year:
        return (
            f"{start_date.day} {MONTHS_GENITIVE[start_date.month - 1]} – "
            f"{end_date.day} {MONTHS_GENITIVE[end_date.month - 1]} "
            f"{end_date.year}"
        )

    return (
        f"{start_date.day} {MONTHS_GENITIVE[start_date.month - 1]} {start_date.year} – "
        f"{end_date.day} {MONTHS_GENITIVE[end_date.month - 1]} {end_date.year}"
    )


def get_default_week_period() -> tuple[date, date]:
    """
    Период недели по умолчанию:
    с 1 числа месяца до конца последней завершённой недели.

    Пример:
    если сегодня 10 августа, период будет 1-9 августа.
    """
    today = datetime.now(MSK).date()

    # Последний воскресенье строго до сегодняшнего дня.
    # В Python: Monday=0, Sunday=6.
    days_since_sunday = (today.weekday() + 1) % 7

    if days_since_sunday == 0:
        days_since_sunday = 7

    end_date = today - timedelta(days=days_since_sunday)
    start_date = end_date.replace(day=1)

    return start_date, end_date


def get_default_week_settings() -> "KRWeekSettings":
    """
    Возвращает настройки недели с периодом по умолчанию.
    """
    start_date, end_date = get_default_week_period()

    return KRWeekSettings(
        use_period=True,
        start_date=start_date,
        end_date=end_date,
        custom_label=""
    )


def _normalize_date(value: Optional[Any]) -> Optional[date]:
    """
    Приводит datetime/date к date.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    raise ValueError("Дата должна быть типа date или datetime.")


# ==========================================================
# ЗАГРУЖЕННЫЕ ФАЙЛЫ
# ==========================================================
@dataclass
class KRSourceFiles:
    """
    Три исходных файла:
    - сайт;
    - агрегаторы;
    - геосервисы.

    Тип намеренно Any, чтобы модель не зависела от Streamlit.
    """

    site: Any = None
    agg: Any = None
    geo: Any = None

    def is_complete(self) -> bool:
        return bool(self.site and self.agg and self.geo)

    def missing_labels(self) -> List[str]:
        missing: List[str] = []

        if not self.site:
            missing.append(SOURCE_LABELS.get(SOURCE_SITE, "Сайт"))

        if not self.agg:
            missing.append(SOURCE_LABELS.get(SOURCE_AGG, "Агрегаторы"))

        if not self.geo:
            missing.append(SOURCE_LABELS.get(SOURCE_GEO, "Геосервисы"))

        return missing

    def as_dict(self) -> Dict[str, Any]:
        return {
            SOURCE_SITE: self.site,
            SOURCE_AGG: self.agg,
            SOURCE_GEO: self.geo,
        }


# ==========================================================
# НАСТРОЙКИ МЕСЯЦА
# ==========================================================
@dataclass(frozen=True)
class KRMonthSettings:
    """
    Настройки месячного отчёта.
    """

    selected_month: str
    selected_year: int
    price_threshold: int = DEFAULT_PRICE_THRESHOLD

    def __post_init__(self) -> None:
        selected_month = str(self.selected_month or "").strip()

        object.__setattr__(self, "selected_month", selected_month)
        object.__setattr__(self, "selected_year", int(self.selected_year))
        object.__setattr__(self, "price_threshold", int(self.price_threshold))

        if not self.selected_month:
            raise ValueError("Месяц отчёта не может быть пустым.")

        if hasattr(c, "MONTHS") and self.selected_month not in c.MONTHS:
            raise ValueError(f"Некорректный месяц отчёта: {self.selected_month}")

        if not (DEFAULT_YEAR_MIN <= self.selected_year <= DEFAULT_YEAR_MAX):
            raise ValueError(
                f"Год отчёта должен быть между {DEFAULT_YEAR_MIN} и {DEFAULT_YEAR_MAX}."
            )

        if self.price_threshold < 0:
            object.__setattr__(self, "price_threshold", 0)

    @property
    def period_label(self) -> str:
        """
        Подпись периода для Excel и интерфейса.
        Пример: Июнь (2026г)
        """
        return f"{self.selected_month} ({self.selected_year}г)"

    @property
    def file_name(self) -> str:
        """
        Имя файла для скачивания.
        Пример: КР_Июнь_2026.xlsx
        """
        return MONTH_FILE_NAME_TEMPLATE.format(
            month=self.selected_month,
            year=self.selected_year
        )


# ==========================================================
# НАСТРОЙКИ НЕДЕЛИ
# ==========================================================
@dataclass(frozen=True)
class KRWeekSettings:
    """
    Настройки недельного отчёта.

    Логика подписи периода:
    1. Если пользователь ввёл подпись — используем её.
    2. Если подпись не введена, но даты выбраны — формируем автоматически.
    3. Если даты не выбраны — пишем "Все даты".
    """

    use_period: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    custom_label: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "use_period", bool(self.use_period))
        object.__setattr__(self, "start_date", _normalize_date(self.start_date))
        object.__setattr__(self, "end_date", _normalize_date(self.end_date))
        object.__setattr__(self, "custom_label", str(self.custom_label or "").strip())

        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Дата конца не может быть раньше даты начала.")

    @property
    def has_selected_dates(self) -> bool:
        return bool(self.start_date and self.end_date)

    @property
    def is_all_dates(self) -> bool:
        """
        Отчёт по всем датам формируется, если:
        - фильтр периода выключен;
        - или даты не выбраны полностью.
        """
        return (not self.use_period) or (not self.has_selected_dates)

    @property
    def period_label(self) -> str:
        if self.custom_label:
            return self.custom_label

        if self.is_all_dates or not self.start_date or not self.end_date:
            return PERIOD_ALL_DATES_LABEL

        return format_week_period_label(self.start_date, self.end_date)

    @property
    def file_name(self) -> str:
        """
        Имя файла для скачивания.
        Примеры:
        - КР_неделя_1-9_августа_2026.xlsx
        - КР_неделя_Все_даты.xlsx
        """
        return WEEK_FILE_NAME_TEMPLATE.format(
            period=sanitize_filename(self.period_label)
        )


# ==========================================================
# ОБЩИЕ НАСТРОЙКИ ОТЧЁТА
# ==========================================================
@dataclass(frozen=True)
class KRReportSettings:
    """
    Универсальная обёртка над режимом отчёта:
    месяц или неделя.
    """

    mode: str
    month: Optional[KRMonthSettings] = None
    week: Optional[KRWeekSettings] = None

    def __post_init__(self) -> None:
        if self.mode not in (MODE_MONTH, MODE_WEEK):
            raise ValueError(f"Некорректный режим отчёта: {self.mode}")

        if self.is_month and self.month is None:
            raise ValueError("Для месячного отчёта не переданы настройки месяца.")

        if self.is_week and self.week is None:
            raise ValueError("Для недельного отчёта не переданы настройки недели.")

    @property
    def is_month(self) -> bool:
        return self.mode == MODE_MONTH

    @property
    def is_week(self) -> bool:
        return self.mode == MODE_WEEK

    @property
    def period_label(self) -> str:
        if self.is_month and self.month:
            return self.month.period_label

        if self.is_week and self.week:
            return self.week.period_label

        return ""

    @property
    def file_name(self) -> str:
        if self.is_month and self.month:
            return self.month.file_name

        if self.is_week and self.week:
            return self.week.file_name

        return ""

    @property
    def price_threshold(self) -> Optional[int]:
        """
        Порог суммы заказа.

        Используется только для месячного отчёта.
        Для недели возвращает None.
        """
        if self.is_month and self.month is not None:
            return self.month.price_threshold

        return None

    @property
    def week_filter_period(self) -> Optional[tuple[date, date]]:
        """
        Период фильтрации для недели.
        Для месяца возвращает None.
        """
        if self.is_week and self.week is not None and not self.week.is_all_dates:
            return self.week.start_date, self.week.end_date

        return None


# ==========================================================
# ЗАПРОС НА ФОРМИРОВАНИЕ ОТЧЁТА
# ==========================================================
@dataclass
class KRReportRequest:
    """
    Всё, что нужно для запуска формирования отчёта:
    файлы + настройки.
    """

    files: KRSourceFiles
    settings: KRReportSettings

    def validate(self) -> None:
        if not self.files.is_complete():
            missing = ", ".join(self.files.missing_labels())
            raise ValueError(f"Не загружены файлы: {missing}.")

        # Настройки уже валидируются внутри dataclass'ов,
        # но оставляем явную проверку для будущих расширений.
        if self.settings.mode not in (MODE_MONTH, MODE_WEEK):
            raise ValueError(f"Некорректный режим отчёта: {self.settings.mode}")


# ==========================================================
# ПОДГОТОВЛЕННЫЕ ДАННЫЕ
# ==========================================================
@dataclass
class KRPreparedData:
    """
    Данные после загрузки и первичной обработки.

    Сюда попадают DataFrame'ы с нормализованными колонками:
    - Ресторан;
    - Рейтинг;
    - Текст.

    Для сайта также может оставаться колонка "Сумма",
    если нужна обработка порога.
    """

    site: pd.DataFrame
    agg: pd.DataFrame
    geo: pd.DataFrame
    warnings: List[str] = field(default_factory=list)

    def add_warning(self, message: str) -> None:
        message = str(message or "").strip()

        if message and message not in self.warnings:
            self.warnings.append(message)

    def add_warnings(self, messages: List[str]) -> None:
        for message in messages:
            self.add_warning(message)


# ==========================================================
# РАСЧЁТНЫЕ ДАННЫЕ ОТЧЁТА
# ==========================================================
@dataclass
class KRReportData:
    """
    Готовые расчётные таблицы, которые можно использовать:
    - для Excel;
    - для превью;
    - для будущих визуальных блоков.
    """

    stats_site: pd.DataFrame
    stats_agg: pd.DataFrame
    stats_geo: pd.DataFrame
    stats_all: pd.DataFrame
    complaints: pd.DataFrame
    positives: pd.DataFrame


# ==========================================================
# РЕЗУЛЬТАТ ФОРМИРОВАНИЯ ОТЧЁТА
# ==========================================================
@dataclass
class KRReportResult:
    """
    Единый результат формирования отчёта.

    UI должен получать именно такой объект и не знать
    внутреннюю кухню расчётов.
    """

    success: bool
    mode: str
    period_label: str
    file_name: str

    excel: Optional[io.BytesIO] = None
    preview: Optional[pd.DataFrame] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    data: Optional[KRReportData] = None

    generated_at: datetime = field(default_factory=lambda: datetime.now(MSK))

    def add_warning(self, message: str) -> None:
        message = str(message or "").strip()

        if message and message not in self.warnings:
            self.warnings.append(message)

    def add_warnings(self, messages: List[str]) -> None:
        for message in messages:
            self.add_warning(message)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    @classmethod
    def ok(
        cls,
        mode: str,
        period_label: str,
        file_name: str,
        excel: Optional[io.BytesIO] = None,
        preview: Optional[pd.DataFrame] = None,
        warnings: Optional[List[str]] = None,
        data: Optional[KRReportData] = None,
    ) -> "KRReportResult":
        return cls(
            success=True,
            mode=mode,
            period_label=period_label,
            file_name=file_name,
            excel=excel,
            preview=preview,
            warnings=list(warnings or []),
            error=None,
            data=data,
        )

    @classmethod
    def fail(
        cls,
        mode: str,
        error: str,
        period_label: str = "",
        file_name: str = "",
        warnings: Optional[List[str]] = None,
    ) -> "KRReportResult":
        return cls(
            success=False,
            mode=mode,
            period_label=period_label,
            file_name=file_name,
            excel=None,
            preview=None,
            warnings=list(warnings or []),
            error=str(error),
            data=None,
        )