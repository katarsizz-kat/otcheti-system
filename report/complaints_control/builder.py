"""
Оркестратор отчёта «Проверка внесения жалоб» (действующие правила,
ред. 18.11.2026).

Источники: только чаты ресторанов Битрикс24 (CSV) и главные таблицы
СПб/Тюмени (файлы или прямая выгрузка Google Sheets). CRM не используется.

extract (data.py) -> classify (classify.py) -> match (matching.py)
-> разметка спорных случаев (request.overrides) -> stats -> excel.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Dict, List, Optional

import pandas as pd

from . import constants as c
from . import data
from . import matching
from . import stats as st
from .classify import classify_message
from .excel import build_complaints_control_excel
from .models import (
    ControlReportRequest,
    ControlReportResult,
    ControlReportData,
)

ATTENTION_COLS = ["Дата", "Источник", "Автор", "Ресторан", "Текст", "Кол-во сообщений"]

_OVERRIDE_STATUS = {
    "exact": c.STATUS_EXACT,
    "probable": c.STATUS_PROBABLE,
    "not_entered": c.STATUS_NOT_ENTERED,
}

REVIEW_DEFAULT = "Оставить как есть"
REVIEW_CHOICES = {
    "Подтверждено внесение": "exact",
    "Не внесено": "not_entered",
    "Вероятное совпадение": "probable",
}


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
    if messages is None or messages.empty or (start is None and end is None):
        return messages
    return messages[messages["Дата"].map(
        lambda d: _in_range(d.date() if pd.notna(d) else None, start, end)
    )]


def _summary(text: str, limit: int = 200) -> str:
    s = " / ".join(t.strip() for t in str(text or "").split("||") if t.strip())
    return s[:limit]


def _empty_comparison() -> pd.DataFrame:
    return pd.DataFrame(columns=matching.COMPARISON_COLS)


def _process_chat(
    file,
    source_label: str,
    main_index: Dict,
    other_index: Dict,
    city_has_table: bool,
    start: Optional[date],
    end: Optional[date],
    tolerance_days: int,
    warnings: List[str],
    label_counts: Dict[str, Dict[str, int]],
) -> (pd.DataFrame, pd.DataFrame):
    """Возвращает (строки сопоставления, строки «Требует внимания»)."""
    messages = data.load_chat_messages(file, source_label, warnings)
    messages = _filter_messages_by_period(messages, start, end)
    grouped, no_keys_msgs = data.group_messages(messages)

    counts: Counter = Counter()
    comparison_rows: List[dict] = []
    attention_rows: List[dict] = []

    def handle(text: str, cdate, authors: str, tickets: str, phone: str,
               order_id: str, orders: List[dict], count: int):
        result = classify_message(text)
        counts[result.reason_label] += 1
        city, rest, rest_label = matching.extract_restaurant(text, orders, source_label)

        if result.reason_label == "attention":
            attention_rows.append({
                "Дата": cdate, "Источник": source_label, "Автор": authors,
                "Ресторан": rest_label, "Текст": _summary(text, 500),
                "Кол-во сообщений": count,
            })
            return
        if not result.is_complaint:
            return

        if not city_has_table:
            status, record, basis = (
                c.STATUS_NO_KEYS, None, f"главная таблица города {city} не загружена",
            )
        else:
            status, record, basis = matching.match_complaint(
                phone, order_id, rest, cdate, result.category,
                main_index, tolerance_days,
            )
            if status == c.STATUS_NOT_ENTERED and other_index:
                other_status, other_record, other_basis = matching.match_complaint(
                    phone, order_id, rest, cdate, result.category,
                    other_index, tolerance_days,
                )
                if other_status in (c.STATUS_EXACT, c.STATUS_PROBABLE):
                    status, record, basis = other_status, other_record, other_basis

        key = matching.complaint_key(source_label, phone, order_id, cdate, text)
        comparison_rows.append({
            "Ключ": key,
            "Источник": source_label,
            "Дата": cdate,
            "Сотрудник": authors,
            "Тикеты": tickets,
            "Ресторан": rest_label,
            "Категория жалобы": result.category,
            "Суть обращения": _summary(text),
            "Телефон Гостя": matching.format_guest_phone(phone),
            "Заказ": order_id,
            "Статус": status,
            "Результат сверки": matching.result_label(status, basis),
            "№ записи в главной": record.get("__row_num") if record else None,
            "Дата в главной": record.get("Дата") if record else None,
            "Ресторан (по главной)": record.get("Ресторан") if record else None,
            "Категория (по главной)": record.get("Категория") if record else None,
            "Основание": basis,
        })

    for _, g in grouped.iterrows():
        orders = data.find_orders_in_text(g["Текст"])
        handle(
            g["Текст"], g["Дата"], g["Авторы"], g["Тикеты"],
            g["Телефон"], g["Заказ"], orders, g["Кол-во сообщений"],
        )

    for _, m in no_keys_msgs.iterrows():
        mdate = m["Дата"].date() if pd.notna(m["Дата"]) else None
        handle(
            m["Текст"], mdate, m["Автор"], "", "", "", [], 1,
        )

    label_counts[source_label] = dict(counts)
    if file is not None and not comparison_rows and not attention_rows and not messages.empty:
        warnings.append(
            f"«{source_label}»: за период не найдено ни одной жалобы среди сообщений — "
            "проверьте, что чат-экспорт актуален."
        )

    comparison = (
        pd.DataFrame(comparison_rows, columns=matching.COMPARISON_COLS)
        if comparison_rows else _empty_comparison()
    )
    attention = (
        pd.DataFrame(attention_rows, columns=ATTENTION_COLS)
        if attention_rows else pd.DataFrame(columns=ATTENTION_COLS)
    )
    return comparison, attention


def build_complaints_control_report(request: ControlReportRequest) -> ControlReportResult:
    settings = request.settings
    period_label = settings.period_label
    warnings: List[str] = []

    try:
        request.validate()
        start_date, end_date = settings.date_start, settings.date_end
        if not settings.is_filtered:
            start_date = end_date = None
        tolerance_days = settings.tolerance_days or c.DEFAULT_TOLERANCE_DAYS

        for label in request.files.missing_labels():
            warnings.append(f"Источник «{label}» не загружен — соответствующий раздел будет пустым.")

        # -------------------- ГЛАВНЫЕ ТАБЛИЦЫ (ВСЯ ТАБЛИЦА) --------------------
        main_spb = data.finalize_main_table(
            data.load_main_spb(request.files.main_spb, warnings), start_date, end_date,
        )
        main_tmn = data.finalize_main_table(
            data.load_main_tyumen(request.files.main_tmn, warnings), start_date, end_date,
        )
        if request.files.main_spb is not None and main_spb.empty:
            warnings.append("«ОС и компенсации» (СПб): таблица пуста — проверьте выгрузку.")
        if request.files.main_tmn is not None and main_tmn.empty:
            warnings.append("«Обратная_связь_Тюмень»: таблица пуста — проверьте выгрузку.")

        index_spb = matching.build_main_index(main_spb)
        index_tmn = matching.build_main_index(main_tmn)

        label_counts: Dict[str, Dict[str, int]] = {}

        # -------------------- ЧАТЫ РЕСТОРАНОВ --------------------
        comparison_tmn, attention_tmn = _process_chat(
            request.files.chat_tmn, "Гости ОС Тюмень",
            index_tmn, index_spb, request.files.main_tmn is not None,
            start_date, end_date, tolerance_days, warnings, label_counts,
        )
        comparison_spb, attention_spb = _process_chat(
            request.files.chat_spb, "Обратная связь Гости",
            index_spb, index_tmn, request.files.main_spb is not None,
            start_date, end_date, tolerance_days, warnings, label_counts,
        )

        comparison = pd.concat(
            [comparison_tmn, comparison_spb], ignore_index=True,
        )
        attention = pd.concat(
            [attention_tmn, attention_spb], ignore_index=True,
        )

        # -------------------- РУЧНАЯ РАЗМЕТКА СПОРНЫХ СЛУЧАЕВ --------------------
        if request.overrides and not comparison.empty:
            for key, decision in request.overrides.items():
                status = _OVERRIDE_STATUS.get(decision)
                if not status:
                    continue
                mask = comparison["Ключ"] == key
                if mask.any():
                    comparison.loc[mask, "Статус"] = status
                    comparison.loc[mask, "Результат сверки"] = matching.result_label(
                        status, "решение пользователя (ручная разметка)",
                    )
                    comparison.loc[mask, "Основание"] = "ручная разметка"

        # -------------------- ИТОГОВЫЕ ТАБЛИЦЫ --------------------
        not_entered = st.build_not_entered(comparison)
        probable = st.build_probable(comparison)
        no_keys = st.build_no_keys(comparison)
        employee_share = st.build_employee_not_entered_share(comparison)
        restaurant_summary = st.build_restaurant_summary(comparison)
        classification_preview = st.build_classification_preview(label_counts)

        review_source = comparison[
            comparison["Статус"].isin([c.STATUS_PROBABLE, c.STATUS_NO_KEYS])
        ].copy()
        if not review_source.empty:
            review_source["Решение"] = REVIEW_DEFAULT
        review_queue = review_source.reset_index(drop=True)

        excel_bytes = build_complaints_control_excel(
            not_entered, probable, comparison, attention,
            employee_share, restaurant_summary, period_label, no_keys,
        )

        report_data = ControlReportData(
            comparison=comparison,
            not_entered=not_entered,
            probable=probable,
            no_keys=no_keys,
            attention=attention,
            review_queue=review_queue,
            employee_not_entered_share=employee_share,
            restaurant_summary=restaurant_summary,
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