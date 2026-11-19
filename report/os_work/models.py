"""Модели данных модуля «Работа ОС». Только структуры, без Streamlit/openpyxl."""
from __future__ import annotations

import calendar
import io
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from report.complaints_control.models import sanitize_filename

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


@dataclass
class OsWorkSourceFiles:
    """CRM JSON — обязателен; чаты Битрикс и главные таблицы — опционально
    (без них листы «Работа с ресторанами» и «Не внесённые жалобы» пустеют)."""
    crm_json: Any = None
    chat_spb: Any = None
    chat_tmn: Any = None
    main_spb: Any = None
    main_tmn: Any = None

    def has_bitrix(self) -> bool:
        return bool(self.chat_spb or self.chat_tmn)


@dataclass(frozen=True)
class OsWorkSettings:
    use_period: bool = True
    date_start: Optional[date] = None
    date_end: Optional[date] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "use_period", bool(self.use_period))
        object.__setattr__(self, "date_start", _normalize_date(self.date_start))
        object.__setattr__(self, "date_end", _normalize_date(self.date_end))
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
        return "Все даты выгрузки"

    @property
    def period_kind(self) -> str:
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

    def _base_name(self) -> str:
        if not self.is_filtered:
            return "Проверка работы ОС_все_даты"
        base = (
            f"Проверка работы ОС_"
            f"{self.date_start.strftime('%Y-%m-%d')}—{self.date_end.strftime('%Y-%m-%d')}"
        )
        if self.period_kind:
            base += f"_{self.period_kind}"
        return base

    @property
    def file_name(self) -> str:
        return sanitize_filename(self._base_name() + "_руководителю") + ".xlsx"

    def personal_file_name(self, employee: str) -> str:
        return sanitize_filename(f"{self._base_name()}_{employee}") + ".xlsx"


@dataclass
class OsWorkRequest:
    files: OsWorkSourceFiles
    settings: OsWorkSettings
    # Ручная разметка: {"outcome": {ключ: результат}, "tone": {ключ: "tone"},
    # "wrong": {ключ: "wrong"}, "merge": {ключ пары: "merge"}}.
    overrides: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # Сверять внесение жалоб с Google-таблицами (модуль «Контроль жалоб»).
    check_not_entered: bool = True

    def validate(self) -> None:
        if self.files.crm_json is None:
            raise ValueError("Не загружена CRM-выгрузка (JSON реестра и диалогов).")


@dataclass
class OsWorkData:
    appeals: pd.DataFrame                 # реестр обращений
    waits: pd.DataFrame                   # все ожидания периода
    dashboard: pd.DataFrame               # показатели: отдел / Женя / Полина
    speed_groups: pd.DataFrame
    outcomes: pd.DataFrame                # разбивка результатов + прогресс разметки
    unanswered: pd.DataFrame
    long_answers: pd.DataFrame            # >20 рабочих минут
    next_day: pd.DataFrame                # первый ответ на следующий день
    old_period_closed: pd.DataFrame       # ожидания прошлых периодов, закрытые в этом
    old_period_open: pd.DataFrame         # незавершённые ожидания прошлых периодов
    hourly: pd.DataFrame
    daily: pd.DataFrame
    weekday: pd.DataFrame
    joint: pd.DataFrame
    pivot_detailed: pd.DataFrame
    pivot_aggregated: pd.DataFrame
    restaurant_work: pd.DataFrame
    not_entered: pd.DataFrame
    probable: pd.DataFrame
    attention: pd.DataFrame
    remarks: pd.DataFrame
    review_queue: pd.DataFrame            # только требующие решения
    review_queue_all: pd.DataFrame        # все обращения (для «показать все» и массовой отметки)
    merge_queue: pd.DataFrame
    weekly: pd.DataFrame = field(default_factory=pd.DataFrame)
    coverage_notes: List[str] = field(default_factory=list)
    personal: Dict[str, Dict[str, pd.DataFrame]] = field(default_factory=dict)
    totals: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OsWorkResult:
    success: bool
    period_label: str
    file_name: str
    excels: Dict[str, io.BytesIO] = field(default_factory=dict)
    personal_file_names: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    data: Optional[OsWorkData] = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(MSK))

    def add_warning(self, message: str) -> None:
        message = str(message or "").strip()
        if message and message not in self.warnings:
            self.warnings.append(message)

    @classmethod
    def ok(cls, period_label, file_name, excels=None, personal_file_names=None,
           warnings=None, data=None) -> "OsWorkResult":
        return cls(
            success=True, period_label=period_label, file_name=file_name,
            excels=dict(excels or {}), personal_file_names=dict(personal_file_names or {}),
            warnings=list(warnings or []), error=None, data=data,
        )

    @classmethod
    def fail(cls, error, period_label="", file_name="", warnings=None) -> "OsWorkResult":
        return cls(
            success=False, period_label=period_label, file_name=file_name,
            warnings=list(warnings or []), error=str(error), data=None,
        )
