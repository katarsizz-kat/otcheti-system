"""
Оркестратор отчёта «Анализ жалоб».
Собирает конвейер:
data (загрузка/нормализация/дедупликация)
-> stats (жалобы, дубли, сводные, по источникам)
-> excel (BytesIO)
и возвращает единый ComplaintsReportResult.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import pandas as pd

from .models import (
    ComplaintsReportRequest,
    ComplaintsReportResult,
    ComplaintsReportData,
)
from .data import prepare_complaints_data
from .stats import build_complaints_stats
from .excel import build_complaints_excel

MSK = timezone(timedelta(hours=3))


# ==========================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ==========================================================
def _empty_df() -> pd.DataFrame:
    return pd.DataFrame()


def _get(obj: object, names, default=None):
    if obj is None:
        return default
    if isinstance(names, str):
        names = [names]
    if isinstance(obj, dict):
        for n in names:
            if n in obj:
                return obj[n]
        return default
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return default


# ==========================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ==========================================================
def build_complaints_report(
    request: ComplaintsReportRequest,
) -> ComplaintsReportResult:
    settings = request.settings
    period_label = settings.period_label

    try:
        request.validate()

        # 1) Загрузка, нормализация, фильтр по датам
        prepared = prepare_complaints_data(
            site_file=request.files.site,
            agg_file=request.files.agg,
            geo_file=request.files.geo,
            os_file=request.files.os,
            os_tmn_file=request.files.os_tmn,
            date_start=settings.date_start,
            date_end=settings.date_end,
        )

        # 2) Жалобы, дубли, сводные
        stats = build_complaints_stats(prepared)

        complaints = _get(stats, ["complaints", "complaints_detail"], _empty_df())
        duplicates = _get(stats, ["duplicates"], _empty_df())
        complaint_summary = _get(stats, ["complaint_summary", "complaints_summary"], _empty_df())
        positive_summary = _get(stats, ["positive_summary", "positives_summary"], _empty_df())
        unresolved_complaints = _get(stats, ["unresolved_complaints"], _empty_df())
        no_compensation_complaints = _get(stats, ["no_compensation_complaints"], _empty_df())

        deleted_geo = getattr(prepared, "deleted_geo", _empty_df())

        # 3) Excel (BytesIO) — передаём period_label через kwargs
        excel_bytes = build_complaints_excel(
            prepared=prepared,
            stats=stats,
            period_label=period_label,
        )

        # 4) Данные для превью в UI
        report_data = ComplaintsReportData(
            complaints=complaints,
            duplicates=duplicates,
            complaint_summary=complaint_summary,
            positive_summary=positive_summary,
            deleted_geo=deleted_geo,
            unresolved_complaints=unresolved_complaints,
            no_compensation_complaints=no_compensation_complaints,
        )

        return ComplaintsReportResult.ok(
            period_label=period_label,
            file_name=settings.file_name,
            excel=excel_bytes,
            warnings=prepared.warnings,
            data=report_data,
        )

    except Exception as exc:  # noqa: BLE001
        return ComplaintsReportResult.fail(
            error=str(exc),
            period_label=period_label,
            file_name=settings.file_name,
        )


# ==========================================================
# УДОБНАЯ ОБЁРТКА
# ==========================================================
def build_complaints_report_from_files(
    site_file,
    agg_file,
    geo_file,
    os_file,
    os_tmn_file=None,
    date_start=None,
    date_end=None,
) -> ComplaintsReportResult:
    from .models import ComplaintsSourceFiles, ComplaintsSettings

    files = ComplaintsSourceFiles(
        site=site_file,
        agg=agg_file,
        geo=geo_file,
        os=os_file,
        os_tmn=os_tmn_file,
    )
    settings = ComplaintsSettings(
        date_start=date_start,
        date_end=date_end,
    )
    request = ComplaintsReportRequest(files=files, settings=settings)
    return build_complaints_report(request)