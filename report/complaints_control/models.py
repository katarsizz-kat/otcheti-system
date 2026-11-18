"""Модели данных модуля «Контроль жалоб». Только структуры, без Streamlit/openpyxl."""
from __future__ import annotations

import calendar
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

MSK = timezone(timedelta(hours=3))


def _normalize_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except Exception:
            continue
    return None


def sanitize_filename(value: str) -> str:
    value = str(value or "")
    value = re.sub(r"[^\w\s\-—]+", "", value, flags=re.UNICODE)
    value = value.strip().replace(" ", "_")
    while "__" in value:
        value = value.replace("__", "_")
    return value or "otchet"


@dataclass
class ControlSourceFiles:
    """Источники проверки внесения жалоб (действующие правила): главные
    таблицы СПб/Тюмени (файлы или выгрузка Google Sheets) и чаты ресторанов
    Битрикс24. CRM в этой проверке не используется. Каждая сторона должна
    быть представлена хотя бы одним источником."""
    main_spb: Any = None
    main_tmn: Any = None
    chat_spb: Any = None
    chat_tmn: Any = None

    def has_any_main(self) -> bool:
        return bool(self.main_spb or self.main_tmn)

    def has_any_source(self) -> bool:
        return bool(self.chat_spb or self.chat_tmn)

    def missing_labels(self) -> List[str]:
        missing = []
        if not self.main_spb:
            missing.append("Главная таблица СПб")
        if not self.main_tmn:
            missing.append("Главная таблица Тюмень")
        if not self.chat_spb:
            missing.append("Чат «Обратная связь Гости» (СПб)")
        if not self.chat_tmn:
            missing.append("Чат «Гости ОС Тюмень»")
        return missing


@dataclass(frozen=True)
class ControlSettings:
    use_period: bool = False
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    tolerance_days: int = 3

    def __post_init__(self) -> None:
        object.__setattr__(self, "use_period", bool(self.use_period))
        object.__setattr__(self, "date_start", _normalize_date(self.date_start))
        object.__setattr__(self, "date_end", _normalize_date(self.date_end))
        object.__setattr__(self, "tolerance_days", int(self.tolerance_days or 0))
        if self.date_start and self.date_end and self.date_end < self.date_start:
            raise ValueError("Дата конца не может быть раньше даты начала.")

    @property
    def has_dates(self) -> bool:
        return bool(self.date_start and self.date_end)

    @property
    def is_filtered(self) -> bool:
        return bool(self.use_period and self.has_dates)

    @property
    def period_label(self) -> str:
        if self.is_filtered:
            return f"{self.date_start.strftime('%d.%m.%Y')}–{self.date_end.strftime('%d.%m.%Y')}"
        return "Все даты"

    @property
    def period_kind(self) -> str:
        """Вид проверки для имени файла: недельная (пн–вс), месячная
        (полный календарный месяц) или произвольный период."""
        if not self.is_filtered:
            return ""
        span = (self.date_end - self.date_start).days + 1
        if span == 7 and self.date_start.weekday() == 0:
            return "недельная"
        last_day = calendar.monthrange(self.date_end.year, self.date_end.month)[1]
        if self.date_start.day == 1 and self.date_end.day == last_day \
                and self.date_start.month == self.date_end.month \
                and self.date_start.year == self.date_end.year:
            return "месячная"
        return ""

    @property
    def file_name(self) -> str:
        """Имя по правилам хранения: вид проверки + период, например
        «Проверка внесения жалоб_2026-10-26—2026-10-31_недельная.xlsx»."""
        if not self.is_filtered:
            return "Проверка_внесения_жалоб_все_даты.xlsx"
        base = (
            f"Проверка внесения жалоб_"
            f"{self.date_start.strftime('%Y-%m-%d')}—{self.date_end.strftime('%Y-%m-%d')}"
        )
        if self.period_kind:
            base += f"_{self.period_kind}"
        return sanitize_filename(base) + ".xlsx"


@dataclass
class ControlReportRequest:
    files: ControlSourceFiles
    settings: ControlSettings
    # Разметка спорных случаев из очереди ручной проверки:
    # {ключ жалобы: 'exact' | 'probable' | 'not_entered'}.
    overrides: Dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.files.has_any_main():
            raise ValueError("Не загружена ни одна главная таблица (СПб или Тюмень).")
        if not self.files.has_any_source():
            raise ValueError(
                "Не загружен ни один чат ресторанов для сверки (СПб или Тюмень)."
            )


@dataclass
class ControlReportData:
    """Готовые таблицы для превью и очереди ручной разметки в UI."""
    comparison: pd.DataFrame
    not_entered: pd.DataFrame
    probable: pd.DataFrame
    no_keys: pd.DataFrame
    attention: pd.DataFrame
    review_queue: pd.DataFrame
    employee_not_entered_share: pd.DataFrame
    restaurant_summary: pd.DataFrame
    classification_preview: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass
class ControlReportResult:
    success: bool
    period_label: str
    file_name: str
    excel: Optional[io.BytesIO] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    data: Optional[ControlReportData] = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(MSK))

    def add_warning(self, message: str) -> None:
        message = str(message or "").strip()
        if message and message not in self.warnings:
            self.warnings.append(message)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    @classmethod
    def ok(cls, period_label, file_name, excel=None, warnings=None, data=None) -> "ControlReportResult":
        return cls(
            success=True, period_label=period_label, file_name=file_name,
            excel=excel, warnings=list(warnings or []), error=None, data=data,
        )

    @classmethod
    def fail(cls, error, period_label="", file_name="", warnings=None) -> "ControlReportResult":
        return cls(
            success=False, period_label=period_label, file_name=file_name,
            excel=None, warnings=list(warnings or []), error=str(error), data=None,
        )