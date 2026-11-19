"""
Оркестратор отчёта «Проверка работы ОС» (методика v4, ред. 18.11.2026).

parse CRM JSON -> объединение тикетов в обращения -> скорость (окно
11:10–22:58, серия ≤5 мин, первые/повторные) -> Битрикс (работа с
ресторанами) -> «Контроль жалоб» (лист «Не внесённые жалобы», опционально)
-> ручная разметка (request.overrides) -> показатели -> Excel (общий +
личные книги). Семантические решения принимает пользователь, не ИИ.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional

import pandas as pd

from report.complaints_control.builder import build_complaints_control_report
from report.complaints_control.data import _read_excel_raw, parse_restaurant_map
from report.complaints_control.models import (
    ControlReportRequest,
    ControlSettings,
    ControlSourceFiles,
)
from report.complaints_control import constants as cc

from . import bitrix
from . import constants as c
from . import crm
from . import merge as mg
from . import restaurants
from . import stats as st
from .excel import build_os_work_excel, build_personal_excel
from .models import OsWorkRequest, OsWorkResult, OsWorkData

REVIEW_QUEUE_COLS = [
    "Ключ", "Тикеты", "Дата", "Ресторан", "Суть обращения", "Подсказка",
    "Последний ответ ОС", "Ответов", "Без ответа", "Результат", "Тон", "Не к месту", "Брань Гостя",
]


def _in_range(d: Optional[date], start: Optional[date], end: Optional[date]) -> bool:
    if d is None:
        return True
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


def _svodnaya_map(main_spb) -> Dict[int, str]:
    if main_spb is None:
        return {}
    for sheet in cc.OS_SUMMARY_SHEET_CANDIDATES:
        try:
            raw = _read_excel_raw(main_spb, sheet_name=sheet)
        except Exception:
            raw = None
        mapping = parse_restaurant_map(raw)
        if mapping:
            return mapping
    return {}


def _apply_semantic_overrides(appeals: List[mg.Appeal], overrides: Dict[str, Dict[str, str]]) -> None:
    by_key = {a.key: a for a in appeals}
    for key, outcome in (overrides.get("outcome") or {}).items():
        if key in by_key and outcome in (
            c.OUTCOME_SOLVED, c.OUTCOME_UNSOLVED, c.OUTCOME_WAIT_GUEST, c.OUTCOME_NO_DATA,
        ):
            by_key[key].outcome = outcome
    for field_name, override_key in (("tone", "tone"), ("wrong", "wrong"), ("abuse", "abuse")):
        for key, value in (overrides.get(override_key) or {}).items():
            if key in by_key and value:
                setattr(by_key[key], field_name, True)


def _not_entered_by_employee(not_entered: pd.DataFrame) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    if not_entered is None or not_entered.empty or "Сотрудник" not in not_entered.columns:
        return counts
    for value in not_entered["Сотрудник"]:
        authors = [a.strip() for a in str(value or "").split(",")]
        for author in authors:
            emp = c.OS_BITRIX_AUTHORS.get(author)
            if emp:
                counts[emp] = counts.get(emp, 0) + 1
    return counts


def build_os_work_report(request: OsWorkRequest) -> OsWorkResult:
    settings = request.settings
    period_label = settings.period_label
    warnings: List[str] = []
    coverage_notes: List[str] = []

    try:
        request.validate()
        export = crm.parse_crm_export(request.files.crm_json)

        start = settings.date_start if settings.is_filtered else None
        end = settings.date_end if settings.is_filtered else None
        if start is None and export.period_from:
            start = export.period_from
        if end is None and export.period_to:
            end = export.period_to

        if not export.complete:
            warnings.append(
                "Сборщик CRM сообщает complete=false — охват может быть неполным. "
                "Проверьте выгрузку перед публикацией отчёта."
            )
        for err in export.errors:
            warnings.append(f"Ошибка сборщика CRM: {err}")
        for w in export.warnings:
            coverage_notes.append(w)
        if export.excluded:
            nums = ", ".join(str(e.get("number")) for e in export.excluded)
            coverage_notes.append(
                f"Реестр исключил карточки вне области ОС: {nums} (другие города/сотрудники)."
            )
        if not export.coverage.get("atomic_snapshot", False):
            coverage_notes.append(
                "Выгрузка — срез обновлений, не атомарный снимок всех обращений организации."
            )

        # -------------------- ОБРАЩЕНИЯ --------------------
        appeals, merge_candidates = mg.build_appeals(export.cards)
        _apply_semantic_overrides(appeals, request.overrides)
        appeals = mg.apply_merge_overrides(appeals, merge_candidates, request.overrides.get("merge") or {})

        no_guest = 0
        for a in appeals:
            for w in a.waits:
                w.in_period = _in_range(w.question_ts.date(), start, end)
            has_guest = any(m.kind == "guest" for m in a.messages)
            if not has_guest:
                a.active = False
                no_guest += 1
                continue
            # Обращение относится к периоду по начальным вопросам ожиданий.
            # Старая карточка с одними лишь напоминаниями/благодарностями в
            # периоде — продолжение, а не новое обращение.
            a.active = (
                any(w.in_period for w in a.waits)
                or (not a.waits and any(
                    _in_range(m.ts.date(), start, end)
                    for m in a.messages if m.kind == "guest"
                ))
            )
        active = [a for a in appeals if a.active]
        if no_guest:
            coverage_notes.append(
                f"Карточек без сообщений гостя (тестовые/служебные): {no_guest} — исключены из подсчёта."
            )

        # Брань Гостя ловится детерминированно (мат однозначен) — вручную
        # размечать её не нужно; ручная отметка только дополняет.
        for a in active:
            if a.abuse:
                continue
            guest_text = " ".join(m.text.lower() for m in a.messages if m.kind == "guest")
            if any(marker in guest_text for marker in c.ABUSE_MARKERS):
                a.abuse = True

        # -------------------- РЕСТОРАНЫ --------------------
        reference = restaurants.load_reference()
        svodnaya = _svodnaya_map(request.files.main_spb)
        restaurant_names: Dict[str, str] = {}
        unknown_ids = set()
        for a in active:
            name, known = restaurants.resolve_name(a.restaurant_id, a.city, reference, svodnaya)
            restaurant_names[a.key] = name
            if not known and a.restaurant_id is not None:
                unknown_ids.add(a.restaurant_id)
        if unknown_ids:
            coverage_notes.append(
                "Не расшифрованы restaurant_id: "
                + ", ".join(str(i) for i in sorted(unknown_ids))
                + " — в отчёте показаны как «город (ID N)». Сообщите названия, чтобы пополнить справочник."
            )
        # -------------------- БИТРИКС: РАБОТА С РЕСТОРАНАМИ --------------------
        bitrix_df = bitrix.load_bitrix(request.files.chat_spb, request.files.chat_tmn, warnings)
        work_df, transfers, _reverse_df, dr_offhours = bitrix.restaurant_work(
            active, bitrix_df, restaurant_names,
        )
        if dr_offhours:
            coverage_notes.append(
                f"Просьб ресторанов выдать промокод на ДР вне часов ОС 11:00–23:00: {dr_offhours}."
            )
        if not request.files.has_bitrix():
            coverage_notes.append(
                "Чаты Битрикс не загружены — передача жалоб в ресторан и ответы ресторанов не проверялись."
            )

        # -------------------- НЕ ВНЕСЁННЫЕ ЖАЛОБЫ (КОНТРОЛЬ ЖАЛОБ) --------------------
        not_entered = pd.DataFrame()
        probable = pd.DataFrame()
        cc_attention = pd.DataFrame()
        not_entered_by_emp: Dict[str, int] = {}
        if request.check_not_entered and request.files.has_bitrix() and (
            request.files.main_spb is not None or request.files.main_tmn is not None
        ):
            cc_request = ControlReportRequest(
                files=ControlSourceFiles(
                    main_spb=request.files.main_spb,
                    main_tmn=request.files.main_tmn,
                    chat_spb=request.files.chat_spb,
                    chat_tmn=request.files.chat_tmn,
                ),
                settings=ControlSettings(
                    use_period=settings.is_filtered,
                    date_start=start,
                    date_end=end,
                ),
            )
            cc_result = build_complaints_control_report(cc_request)
            if cc_result.success and cc_result.data is not None:
                not_entered = cc_result.data.not_entered
                probable = cc_result.data.probable
                cc_attention = cc_result.data.attention
                not_entered_by_emp = _not_entered_by_employee(not_entered)
                for w in cc_result.warnings:
                    warnings.append(f"Контроль жалоб: {w}")
            else:
                warnings.append(f"Контроль жалоб не выполнен: {cc_result.error}")
        elif request.check_not_entered and request.files.has_bitrix():
            coverage_notes.append(
                "Главные таблицы не загружены — лист «Не внесённые жалобы» пропущен."
            )

        # -------------------- ПОКАЗАТЕЛИ --------------------
        dashboard = st.build_dashboard(active, transfers, not_entered_by_emp, len(not_entered))
        groups = st.build_speed_groups_table(active)
        outcomes = st.build_outcomes_table(active)
        unanswered = st.build_unanswered(active, restaurant_names)
        long_answers = st.build_long_answers(active, restaurant_names)
        next_day = st.build_next_day(active, restaurant_names)
        old_closed = st.build_old_period_closed(appeals, start, end)
        old_open = st.build_old_period_open(appeals, start)
        hourly, daily, weekday, joint, total_days = st.build_load(active, start, end)
        weekly = st.build_weekly(active) if start and end and (end - start).days + 1 > 7 else pd.DataFrame()
        pivot1, pivot2 = st.build_pivots(active, restaurant_names)
        attention = st.build_attention(active, cc_attention)
        remarks = st.build_remarks(active, restaurant_names)
        appeals_table = st.build_appeals_table(active, restaurant_names)
        waits_table = st.build_waits_table(appeals)

        personal: Dict[str, Dict[str, pd.DataFrame]] = {}
        for emp in c.EMPLOYEES:
            personal[emp] = st.build_personal(
                active, emp, restaurant_names, transfers, not_entered_by_emp,
            )

        # -------------------- ПОЛНОТА ИСТОЧНИКОВ --------------------
        feedback_present = any(
            m.author == "Санкт-Петербург (Feedback)"
            for card in export.cards for m in card.messages if m.kind == "staff"
        )
        if not feedback_present:
            coverage_notes.append(
                "В выгрузке нет сообщений Полины (Feedback) — её показатели пустые. "
                "Это не доказательство отсутствия работы: проверьте охват выгрузки."
            )
        if start and end:
            guest_days = {
                m.ts.date() for a in active for m in a.messages if m.kind == "guest"
            }
            missing_days = []
            day = start
            while day <= end:
                if day not in guest_days:
                    missing_days.append(day.strftime("%d.%m"))
                day += timedelta(days=1)
            if missing_days:
                coverage_notes.append(
                    "Нет сообщений гостей за даты: " + ", ".join(missing_days)
                    + " — это не доказывает нулевой спрос."
                )
        attach_count = sum(
            1 for card in export.cards for m in card.messages if m.attachments
        )
        if attach_count:
            coverage_notes.append(
                f"Вложения в {attach_count} сообщениях — только ссылки, файлы не скачаны; "
                "решение по фото проверяется вручную."
            )
        coverage_notes.append(
            "График смен не предоставлен — скорость отнесена к фактическим авторам ответов, "
            "плановые смены не восстанавливались."
        )
        coverage_notes.append(
            "Решён/не решён, тон, ответ не к месту — ручная разметка в очереди; "
            "неразмеченные обращения не входят в знаменатель решённости."
        )

        # -------------------- ОЧЕРЕДЬ РАЗМЕТКИ --------------------
        # По умолчанию в очереди только обращения, требующие решения человека
        # (подсказка, без ответа, долгое ожидание, тон/не к месту). Остальные
        # можно отметить решёнными одной кнопкой — не проверяя каждое вручную.
        def _needs_review(a) -> bool:
            return bool(
                mg.outcome_hint(a)
                or any(w.in_period and not w.answered for w in a.waits)
                or any(w.in_period and w.answered and w.minutes > c.DETAIL_THRESHOLD_MIN for w in a.waits)
                or a.tone or a.wrong
            )

        queue_rows = []
        for a in active:
            last_staff = a.last_staff_message()
            outcome_label = c.REVIEW_DEFAULT
            for label, value in c.REVIEW_OUTCOME_CHOICES.items():
                if a.outcome == value:
                    outcome_label = label
                    break
            answered_n = sum(1 for w in a.waits if w.in_period and w.answered)
            queue_rows.append({
                "Ключ": a.key,
                "Тикеты": ", ".join(map(str, a.tickets)),
                "Дата": a.first_question,
                "Ресторан": restaurant_names.get(a.key, a.city),
                "Суть обращения": a.summary[:200],
                "Подсказка": mg.outcome_hint(a),
                "Последний ответ ОС": (last_staff.text[:150] if last_staff else ""),
                "Ответов": answered_n,
                "Без ответа": "Да" if any(w.in_period and not w.answered for w in a.waits) else "",
                "Результат": outcome_label,
                "Тон": "Нарушение тона" if a.tone else "Нет",
                "Не к месту": "Ответ не к месту / неверная информация" if a.wrong else "Нет",
                "Брань Гостя": "Гость ругался (брань, оскорбления, угрозы)" if a.abuse else "Нет",
                "_needs": _needs_review(a),
            })
        review_queue_all = pd.DataFrame(queue_rows, columns=REVIEW_QUEUE_COLS + ["_needs"])
        if review_queue_all.empty:
            review_queue = pd.DataFrame(columns=REVIEW_QUEUE_COLS)
            review_queue_all = pd.DataFrame(columns=REVIEW_QUEUE_COLS)
        else:
            review_queue = review_queue_all[review_queue_all["_needs"]].drop(columns=["_needs"]).reset_index(drop=True)
            review_queue_all = review_queue_all.drop(columns=["_needs"])
        merge_queue = pd.DataFrame(merge_candidates) if merge_candidates else pd.DataFrame(
            columns=["Ключ", "Телефон", "Тикеты А", "Тикеты Б", "Дата А", "Дата Б",
                     "Суть А", "Суть Б", "Решение"]
        )

        # -------------------- EXCEL --------------------
        data = OsWorkData(
            appeals=appeals_table, waits=waits_table, dashboard=dashboard,
            speed_groups=groups, outcomes=outcomes, unanswered=unanswered,
            long_answers=long_answers, next_day=next_day, old_period_closed=old_closed,
            old_period_open=old_open,
            hourly=hourly, daily=daily, weekday=weekday, joint=joint,
            pivot_detailed=pivot1, pivot_aggregated=pivot2,
            restaurant_work=work_df,
            not_entered=not_entered, probable=probable, attention=attention,
            remarks=remarks, review_queue=review_queue,
            review_queue_all=review_queue_all, merge_queue=merge_queue,
            weekly=weekly, coverage_notes=coverage_notes, personal=personal,
            totals={
                "обращений": len(active),
                "ответов": len(st.employee_waits(active, None)),
                "среднее": st._avg([w.minutes for w in st.employee_waits(active, None)]),
                "без ответа": len(unanswered),
                "дольше 20": len(long_answers),
                "размечено": sum(1 for a in active if a.outcome != c.OUTCOME_UNMARKED),
                "всего размечать": len(active),
            },
        )

        excels = {"руководителю": build_os_work_excel(data, period_label, coverage_notes)}
        personal_file_names = {}
        for emp in c.EMPLOYEES:
            if personal[emp]["appeals"].empty and personal[emp]["metrics"].empty:
                continue
            excels[emp] = build_personal_excel(emp, personal[emp], period_label)
            personal_file_names[emp] = settings.personal_file_name(emp)

        return OsWorkResult.ok(
            period_label=period_label,
            file_name=settings.file_name,
            excels=excels,
            personal_file_names=personal_file_names,
            warnings=warnings,
            data=data,
        )

    except Exception as exc:  # noqa: BLE001
        return OsWorkResult.fail(
            error=str(exc), period_label=period_label,
            file_name=settings.file_name, warnings=warnings,
        )
