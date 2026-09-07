"""Модели данных модуля «Контроль жалоб». Только структуры, без Streamlit/openpyxl."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional

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
    value = re.sub(r"[^\w\s\-]+", "", value, flags=re.UNICODE)
    value = value.strip().replace(" ", "_")
    while "__" in value:
        value = value.replace("__", "_")
    return value or "otchet"


@dataclass
class ControlSourceFiles:
    """5 источников. Главные таблицы и источники сверки — каждый опционален
    по отдельности, но должен быть загружен хотя бы один с каждой стороны,
    иначе сравнивать не с чем (см. ControlReportRequest.validate)."""
    main_spb: Any = None
    main_tmn: Any = None
    chat_spb: Any = None
    chat_tmn: Any = None
    issues_report: Any = None

    def has_any_main(self) -> bool:
        return bool(self.main_spb or self.main_tmn)

    def has_any_source(self) -> bool:
        return bool(self.chat_spb or self.chat_tmn or self.issues_report)

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
        if not self.issues_report:
            missing.append("issues_report")
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
    def file_name(self) -> str:
        return f"Контроль_жалоб_{sanitize_filename(self.period_label)}.xlsx"


@dataclass
class ControlReportRequest:
    files: ControlSourceFiles
    settings: ControlSettings

    def validate(self) -> None:
        if not self.files.has_any_main():
            raise ValueError("Не загружена ни одна главная таблица (СПб или Тюмень).")
        if not self.files.has_any_source():
            raise ValueError(
                "Не загружен ни один источник для сверки (чаты или issues_report)."
            )


@dataclass
class ControlReportData:
    """Готовые таблицы для превью в UI."""
    comparison_chats: pd.DataFrame
    comparison_issues: pd.DataFrame
    not_entered_all: pd.DataFrame
    not_confirmed_main: pd.DataFrame
    no_phone_all: pd.DataFrame
    employee_not_entered_share: pd.DataFrame
    restaurant_summary: pd.DataFrame
    metric_unpaid_compensation: pd.DataFrame
    metric_deviation_confirmed: pd.DataFrame
    metric_compensation_cost: pd.DataFrame
    metric_backlog: pd.DataFrame
    metric_decision_distribution: pd.DataFrame
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
