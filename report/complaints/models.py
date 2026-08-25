# report/complaints/models.py
"""
Модели данных модуля «Анализ жалоб».
Только структуры данных. Без Streamlit и openpyxl.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, List, Optional

import pandas as pd

# Московское время: UTC+3
MSK = timezone(timedelta(hours=3))


# ==========================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ==========================================================
def _normalize_date(value: Any) -> Optional[date]:
    """Приводит datetime/date/str к date."""
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
    """Делает строку безопасной для имени файла."""
    value = str(value or "")
    value = re.sub(r"[^\w\s\-]+", "", value, flags=re.UNICODE)
    value = value.strip().replace(" ", "_")
    while "__" in value:
        value = value.replace("__", "_")
    return value or "otchet"


# ==========================================================
# ЗАГРУЖЕННЫЕ ФАЙЛЫ
# ==========================================================
@dataclass
class ComplaintsSourceFiles:
    """Четыре обязательных файла (сайт, агрегаторы, геосервисы, ОС)
    + необязательный ОС Тюмень (в UI загружаются одним загрузчиком —
    см. ui.pages.complaints.classify_os_upload)."""
    site: Any = None
    agg: Any = None
    geo: Any = None
    os: Any = None
    os_tmn: Any = None  # опционально — не влияет на is_complete()

    def is_complete(self) -> bool:
        return bool(self.site and self.agg and self.geo and self.os)

    def missing_labels(self) -> List[str]:
        missing: List[str] = []
        if not self.site:
            missing.append("Сайт/приложение")
        if not self.agg:
            missing.append("Агрегаторы")
        if not self.geo:
            missing.append("Геосервисы")
        if not self.os:
            missing.append("ОС и компенсации")
        return missing


# ==========================================================
# НАСТРОЙКИ ПЕРИОДА
# ==========================================================
@dataclass(frozen=True)
class ComplaintsSettings:
    """Настраиваемый период отчёта."""
    use_period: bool = False
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
            return (
                f"{self.date_start.strftime('%d.%m.%Y')}"
                "–"
                f"{self.date_end.strftime('%d.%m.%Y')}"
            )
        return "Все даты"

    @property
    def file_name(self) -> str:
        return f"Анализ_жалоб_{sanitize_filename(self.period_label)}.xlsx"


# ==========================================================
# ЗАПРОС НА ФОРМИРОВАНИЕ ОТЧЁТА
# ==========================================================
@dataclass
class ComplaintsReportRequest:
    """Файлы + настройки для запуска отчёта."""
    files: ComplaintsSourceFiles
    settings: ComplaintsSettings

    def validate(self) -> None:
        if not self.files.is_complete():
            missing = ", ".join(self.files.missing_labels())
            raise ValueError(f"Не загружены файлы: {missing}.")


# ==========================================================
# РАСЧЁТНЫЕ ДАННЫЕ ОТЧЁТА
# ==========================================================
@dataclass
class ComplaintsReportData:
    """Готовые таблицы для выгрузки."""
    complaints: pd.DataFrame
    duplicates: pd.DataFrame
    complaint_summary: pd.DataFrame
    positive_summary: pd.DataFrame
    deleted_geo: pd.DataFrame
    unresolved_complaints: pd.DataFrame = field(default_factory=pd.DataFrame)
    no_compensation_complaints: pd.DataFrame = field(default_factory=pd.DataFrame)

    # ---- Алиасы для интерфейса (plural-имена) ----
    @property
    def complaints_summary(self) -> pd.DataFrame:
        return self.complaint_summary

    @property
    def positives_summary(self) -> pd.DataFrame:
        return self.positive_summary


# ==========================================================
# РЕЗУЛЬТАТ ФОРМИРОВАНИЯ ОТЧЁТА
# ==========================================================
@dataclass
class ComplaintsReportResult:
    """Единый результат формирования отчёта."""
    success: bool
    period_label: str
    file_name: str
    excel: Optional[io.BytesIO] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    data: Optional[ComplaintsReportData] = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(MSK))

    def add_warning(self, message: str) -> None:
        message = str(message or "").strip()
        if message and message not in self.warnings:
            self.warnings.append(message)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    @classmethod
    def ok(
        cls,
        period_label: str,
        file_name: str,
        excel: Optional[io.BytesIO] = None,
        warnings: Optional[List[str]] = None,
        data: Optional[ComplaintsReportData] = None,
    ) -> "ComplaintsReportResult":
        return cls(
            success=True,
            period_label=period_label,
            file_name=file_name,
            excel=excel,
            warnings=list(warnings or []),
            error=None,
            data=data,
        )

    @classmethod
    def fail(
        cls,
        error: str,
        period_label: str = "",
        file_name: str = "",
        warnings: Optional[List[str]] = None,
    ) -> "ComplaintsReportResult":
        return cls(
            success=False,
            period_label=period_label,
            file_name=file_name,
            excel=None,
            warnings=list(warnings or []),
            error=str(error),
            data=None,
        )