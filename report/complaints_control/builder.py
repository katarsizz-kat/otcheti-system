"""
Оркестратор отчёта «Контроль жалоб».
extract (data.py) -> classify (classify.py) -> match (matching.py)
-> stats (stats.py) -> excel (excel.py) -> ControlReportResult.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Dict, Optional

import pandas as pd

from . import constants as c
from . import data
from . import matching
from . import stats as st
from .classify import classify_message, classify_issue_row
from .excel import build_complaints_control_excel
from .models import (
    ControlReportRequest,
    ControlReportResult,
    ControlReportData,
)


def _in_range(d: Optional[date], start: Optional[date], end: Optional[date]) -> bool:
    if d is None:
        return True
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


def _filter_messages_by_period(
    messages: pd.DataFrame, start: Optional[date], end: Optional[date]
) -> pd.DataFrame:
    """Фильтрует сырые сообщения чата по периоду ДО группировки по (телефон,
    день)."""
    if messages is None or messages.empty or (start is None and end is None):
        return messages
    return messages[messages["Дата"].map(
        lambda d: _in_range(d.date() if pd.notna(d) else None, start, end)
    )]


def _classify_grouped_chat(grouped: pd.DataFrame) -> (pd.DataFrame, Counter):
    """Классифицирует каждую сгруппированную (телефон, день) запись чата.
    Возвращает (только жалобы, счётчик причин по всем записям)."""
    counts: Counter = Counter()
    if grouped is None or grouped.empty:
        return grouped, counts

    is_complaint = []
    for text in grouped["Текст"]:
        result = classify_message(text, allow_compensation=True)
        counts[result.reason_label] += 1
        is_complaint.append(result.is_complaint)

    grouped = grouped.copy()
    grouped["_is_complaint"] = is_complaint
    return grouped[grouped["_is_complaint"]].drop(columns=["_is_complaint"]), counts


def _classify_issues(issues_df: pd.DataFrame) -> (pd.DataFrame, Counter):
    counts: Counter = Counter()
    if issues_df is None or issues_df.empty:
        return issues_df, counts

    is_complaint = []
    for _, row in issues_df.iterrows():
        result = classify_issue_row(row.get("Первичное сообщение"), row.get("Причина обращения"))
        counts[result.reason_label] += 1
        is_complaint.append(result.is_complaint)

    issues_df = issues_df.copy()
    issues_df["_is_complaint"] = is_complaint
    return issues_df[issues_df["_is_complaint"]].drop(columns=["_is_complaint"]), counts


def build_complaints_control_report(request: ControlReportRequest) -> ControlReportResult:
    settings = request.settings
    period_label = settings.period_label
    warnings: list = []

    try:
        request.validate()
        start_date, end_date = settings.date_start, settings.date_end
        if not settings.is_filtered:
            start_date = end_date = None
        tolerance_days = settings.tolerance_days or c.DEFAULT_TOLERANCE_DAYS

        for label in request.files.missing_labels():
            warnings.append(f"Источник «{label}» не загружен — соответствующий раздел будет пустым.")

        # -------------------- ГЛАВНЫЕ ТАБЛИЦЫ --------------------
        main_spb_raw = data.load_main_spb(request.files.main_spb, warnings)
        main_spb = data.finalize_main_table(main_spb_raw, start_date, end_date)
        main_tmn_raw = data.load_main_tyumen(request.files.main_tmn, warnings)
        main_tmn = data.finalize_main_table(main_tmn_raw, start_date, end_date)
        main_combined = pd.concat([main_spb, main_tmn], ignore_index=True)

        if request.files.main_spb and main_spb.empty:
            warnings.append(
                "«ОС и компенсации» (СПб): за выбранный период нет строк — "
                "проверьте, что таблица обновлена, это не обязательно значит «жалоб не было»."
            )
        if request.files.main_tmn and main_tmn.empty:
            warnings.append(
                "«Обратная_связь_Тюмень»: за выбранный период нет строк — "
                "проверьте, что таблица обновлена, это не обязательно значит «жалоб не было»."
            )

        main_index_spb = matching.build_main_index(main_spb)
        main_index_tmn = matching.build_main_index(main_tmn)
        empty_index: Dict = {}

        label_counts: Dict[str, Dict[str, int]] = {}

        # -------------------- ЧАТ ТЮМЕНЬ --------------------
        chat_tmn_messages = data.load_chat_messages(request.files.chat_tmn, "Гости ОС Тюмень", warnings)
        chat_tmn_messages = _filter_messages_by_period(chat_tmn_messages, start_date, end_date)
        grouped_tmn, no_phone_tmn = data.group_messages_by_phone_day(chat_tmn_messages)
        complaints_tmn, counts_tmn = _classify_grouped_chat(grouped_tmn)
        label_counts["Гости ОС Тюмень (чат)"] = dict(counts_tmn)
        if request.files.chat_tmn and complaints_tmn.empty and not chat_tmn_messages.empty:
            warnings.append(
                "«Гости ОС Тюмень»: за период не найдено ни одной жалобы среди сообщений — "
                "проверьте, что чат-экспорт актуален."
            )
        comparison_chat_tmn = matching.match_source_to_main(
            complaints_tmn, no_phone_tmn, main_index_tmn, "Гости ОС Тюмень",
            tolerance_days, author_col="Авторы", count_col="Кол-во сообщений",
        )
        not_confirmed_chat_tmn = matching.find_unconfirmed_main_rows(
            main_tmn, set(complaints_tmn.get("Телефон", pd.Series(dtype=str)))
        )

        # -------------------- ЧАТ СПБ --------------------
        chat_spb_messages = data.load_chat_messages(request.files.chat_spb, "Обратная связь Гости", warnings)
        chat_spb_messages = _filter_messages_by_period(chat_spb_messages, start_date, end_date)
        grouped_spb, no_phone_spb = data.group_messages_by_phone_day(chat_spb_messages)
        complaints_spb, counts_spb = _classify_grouped_chat(grouped_spb)
        label_counts["Обратная связь Гости (чат, СПб)"] = dict(counts_spb)
        if request.files.chat_spb and complaints_spb.empty and not chat_spb_messages.empty:
            warnings.append(
                "«Обратная связь Гости»: за период не найдено ни одной жалобы среди сообщений — "
                "проверьте, что чат-экспорт актуален."
            )
        comparison_chat_spb = matching.match_source_to_main(
            complaints_spb, no_phone_spb, main_index_spb, "Обратная связь Гости",
            tolerance_days, author_col="Авторы", count_col="Кол-во сообщений",
        )
        not_confirmed_chat_spb = matching.find_unconfirmed_main_rows(
            main_spb, set(complaints_spb.get("Телефон", pd.Series(dtype=str)))
        )

        # -------------------- issues_report --------------------
        issues_raw = data.load_issues_report(request.files.issues_report, warnings)
        if not issues_raw.empty:
            issues_raw = issues_raw[issues_raw["Дата отзыва"].map(
                lambda d: _in_range(d.date() if pd.notna(d) else None, start_date, end_date)
            )]
        issues_complaints, counts_issues = _classify_issues(issues_raw)
        label_counts["issues_report"] = dict(counts_issues)
        if request.files.issues_report and issues_complaints.empty and not issues_raw.empty:
            warnings.append(
                "«issues_report»: за период не найдено ни одной жалобы среди обращений СПб/Тюмени."
            )

        issues_tmn = issues_complaints[issues_complaints.get("Город") == "Тюмень"] if not issues_complaints.empty else issues_complaints
        issues_spb = issues_complaints[issues_complaints.get("Город") == "Санкт-Петербург"] if not issues_complaints.empty else issues_complaints

        comparison_issues_tmn = matching.match_issues_to_main(issues_tmn, empty_index, main_index_tmn, tolerance_days)
        comparison_issues_spb = matching.match_issues_to_main(issues_spb, main_index_spb, empty_index, tolerance_days)

        not_confirmed_issues_tmn = matching.find_unconfirmed_main_rows(
            main_tmn, set(issues_tmn.get("Телефон", pd.Series(dtype=str)))
        )
        not_confirmed_issues_spb = matching.find_unconfirmed_main_rows(
            main_spb, set(issues_spb.get("Телефон", pd.Series(dtype=str)))
        )

        # -------------------- ЛИСТ 3: СВОД --------------------
        comparison_chats_combined = pd.concat(
            [df for df in (comparison_chat_tmn, comparison_chat_spb) if df is not None and not df.empty],
            ignore_index=True,
        ) if (not comparison_chat_tmn.empty or not comparison_chat_spb.empty) else pd.DataFrame(columns=matching.COMPARISON_COLS)
        comparison_issues_combined = pd.concat(
            [df for df in (comparison_issues_tmn, comparison_issues_spb) if df is not None and not df.empty],
            ignore_index=True,
        ) if (not comparison_issues_tmn.empty or not comparison_issues_spb.empty) else pd.DataFrame(columns=matching.COMPARISON_COLS)

        not_entered_all = st.build_not_entered_all(comparison_chats_combined, comparison_issues_combined)
        no_phone_all = st.build_no_phone_all(comparison_chats_combined, comparison_issues_combined)
        employee_share = st.build_employee_not_entered_share(comparison_chats_combined)
        restaurant_summary = st.build_restaurant_summary(comparison_chats_combined, comparison_issues_combined)

        # -------------------- ЛИСТ 4: МЕТРИКИ --------------------
        metric_unpaid = st.metric_unpaid_compensation(main_combined)
        metric_deviation = st.metric_deviation_confirmed(main_combined)
        metric_cost = st.metric_compensation_cost(main_combined)
        metric_backlog = st.metric_backlog(issues_raw)
        metric_decision = st.metric_decision_distribution(main_combined)

        classification_preview = st.build_classification_preview(label_counts)

        # -------------------- EXCEL --------------------
        excel_bytes = build_complaints_control_excel(
            comparison_chat_tmn, comparison_chat_spb,
            not_confirmed_chat_tmn, not_confirmed_chat_spb,
            comparison_issues_tmn, comparison_issues_spb,
            not_confirmed_issues_tmn, not_confirmed_issues_spb,
            not_entered_all, employee_share, restaurant_summary,
            metric_unpaid, metric_deviation, metric_cost, metric_backlog, metric_decision,
            period_label,
        )

        # Агрегированный превью-список «не подтверждено» (для UI, не для Excel):
        # confirmed по объединению ВСЕХ источников — иначе запись, найденная
        # чатом, но не встретившаяся в issues_report, ложно попала бы сюда.
        all_confirmed_tmn = set(complaints_tmn.get("Телефон", pd.Series(dtype=str))) | set(
            issues_tmn.get("Телефон", pd.Series(dtype=str))
        )
        all_confirmed_spb = set(complaints_spb.get("Телефон", pd.Series(dtype=str))) | set(
            issues_spb.get("Телефон", pd.Series(dtype=str))
        )
        not_confirmed_main_combined = pd.concat(
            [
                matching.find_unconfirmed_main_rows(main_tmn, all_confirmed_tmn),
                matching.find_unconfirmed_main_rows(main_spb, all_confirmed_spb),
            ],
            ignore_index=True,
        )

        report_data = ControlReportData(
            comparison_chats=comparison_chats_combined,
            comparison_issues=comparison_issues_combined,
            not_entered_all=not_entered_all,
            not_confirmed_main=not_confirmed_main_combined,
            no_phone_all=no_phone_all,
            employee_not_entered_share=employee_share,
            restaurant_summary=restaurant_summary,
            metric_unpaid_compensation=metric_unpaid,
            metric_deviation_confirmed=metric_deviation,
            metric_compensation_cost=metric_cost,
            metric_backlog=metric_backlog,
            metric_decision_distribution=metric_decision,
            classification_preview=classification_preview,
        )

        return ControlReportResult.ok(
            period_label=period_label,
            file_name=settings.file_name,
            excel=excel_bytes,
            warnings=warnings,
            data=report_data,
        )

    except Exception as exc:  # noqa: BLE001
        return ControlReportResult.fail(
            error=str(exc),
            period_label=period_label,
            file_name=settings.file_name,
            warnings=warnings,
        )
