# report/kr/builder.py

"""
Финальная сборка отчёта КР.

Модуль связывает:
- data.py: загрузка и подготовка данных;
- stats.py: расчёт показателей;
- excel.py: генерация Excel-файла;
- models.py: запрос и результат отчёта.

Модуль не содержит:
- Streamlit;
- визуала;
- CSS;
- интерфейса.
"""

from __future__ import annotations

from typing import Optional

# ==========================================================
# КОНСТАНТЫ
# ==========================================================
try:
    from . import constants as c
except Exception:
    try:
        from . import kr_constants as c
    except Exception:
        try:
            from report.kr import constants as c
        except Exception:
            try:
                from report.kr import kr_constants as c
            except Exception:
                c = None

MODE_MONTH = getattr(c, "MODE_MONTH", "month")
MODE_WEEK = getattr(c, "MODE_WEEK", "week")


# ==========================================================
# МОДЕЛИ
# ==========================================================
try:
    from .models import (
        KRMonthSettings,
        KRReportRequest,
        KRReportResult,
        KRReportSettings,
        KRSourceFiles,
        KRWeekSettings,
    )
except Exception:
    from report.kr.models import (
        KRMonthSettings,
        KRReportRequest,
        KRReportResult,
        KRReportSettings,
        KRSourceFiles,
        KRWeekSettings,
    )


# ==========================================================
# ДАННЫЕ
# ==========================================================
try:
    from .data import load_kr_data
except Exception:
    from report.kr.data import load_kr_data


# ==========================================================
# РАСЧЁТЫ
# ==========================================================
try:
    from .stats import calculate_report_data
except Exception:
    from report.kr.stats import calculate_report_data


# ==========================================================
# EXCEL
# ==========================================================
try:
    from .excel import build_kr_excel
except Exception:
    try:
        from .excel import build_excel as build_kr_excel
    except Exception:
        try:
            from report.kr.excel import build_kr_excel
        except Exception:
            from report.kr.excel import build_excel as build_kr_excel


__all__ = [
    "build_kr_report",
    "build_month_report",
    "build_week_report",
]


# ==========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================================
def _safe_settings_value(settings: Optional[object], name: str, default: str = "") -> str:
    """
    Безопасно получает значение из settings.
    """
    try:
        value = getattr(settings, name, default)
        return default if value is None else value
    except Exception:
        return default


def _has_any_data(prepared: object) -> bool:
    """
    Проверяет, есть ли вообще данные по трём источникам.
    """
    dataframes = (
        getattr(prepared, "site", None),
        getattr(prepared, "agg", None),
        getattr(prepared, "geo", None),
    )

    for df in dataframes:
        if df is None:
            continue

        if not getattr(df, "empty", True):
            return True

    return False


# ==========================================================
# ОСНОВНАЯ СБОРКА ОТЧЁТА
# ==========================================================
def build_kr_report(request: KRReportRequest) -> KRReportResult:
    """
    Основная точка сборки отчёта КР.

    Принимает KRReportRequest и возвращает KRReportResult.

    Логика:
    1. Проверяет запрос.
    2. Загружает и подготавливает данные.
    3. Считает показатели.
    4. Собирает Excel.
    5. Возвращает готовый результат.
    """
    settings = getattr(request, "settings", None)
    mode = _safe_settings_value(settings, "mode", "")

    try:
        if request is None:
            raise ValueError("Не передан запрос на формирование отчёта.")

        # Проверяем файлы и настройки
        request.validate()

        # Загрузка и подготовка данных
        prepared = load_kr_data(request.files, settings)

        if prepared is None:
            raise RuntimeError("Не удалось подготовить данные отчёта.")

        # Расчёт показателей
        report_data = calculate_report_data(prepared, settings)

        if report_data is None:
            raise RuntimeError("Не удалось рассчитать данные отчёта.")

        # Генерация Excel
        excel_file = build_kr_excel(report_data, settings)

        if excel_file is None:
            raise RuntimeError("Не удалось сформировать Excel-файл.")

        # Итоговый результат
        result = KRReportResult.ok(
            mode=settings.mode,
            period_label=settings.period_label,
            file_name=settings.file_name,
            excel=excel_file,
            preview=getattr(report_data, "stats_all", None),
            warnings=getattr(prepared, "warnings", []),
            data=report_data,
        )

        # Дополнительное предупреждение, если данных нет
        if not _has_any_data(prepared):
            result.add_warning(
                "Загруженные файлы не содержат распознанных отзывов. "
                "Отчёт сформирован с нулевыми значениями."
            )

        return result

    except Exception as exc:
        return KRReportResult.fail(
            mode=mode,
            error=str(exc) or repr(exc),
            period_label=_safe_settings_value(settings, "period_label", ""),
            file_name=_safe_settings_value(settings, "file_name", ""),
        )


# ==========================================================
# УДОБНЫЕ ОБЁРТКИ ДЛЯ МЕСЯЦА И НЕДЕЛИ
# ==========================================================
def build_month_report(
    files: KRSourceFiles,
    month_settings: KRMonthSettings,
) -> KRReportResult:
    """
    Собирает месячный отчёт КР.
    """
    request = KRReportRequest(
        files=files,
        settings=KRReportSettings(
            mode=MODE_MONTH,
            month=month_settings,
        ),
    )

    return build_kr_report(request)


def build_week_report(
    files: KRSourceFiles,
    week_settings: KRWeekSettings,
) -> KRReportResult:
    """
    Собирает недельный отчёт КР.
    """
    request = KRReportRequest(
        files=files,
        settings=KRReportSettings(
            mode=MODE_WEEK,
            week=week_settings,
        ),
    )

    return build_kr_report(request)