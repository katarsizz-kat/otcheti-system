"""
Визуальная часть страницы «ОС» — Проверка работы Отдела Обратной Связи.

v3.0 (методика v4, ред. 18.11.2026): вход — JSON реестра и полных диалогов
CRM (crm-pj-readonly-unified-2), который пользователь выгружает сам;
опционально чаты ресторанов Битрикс24 (CSV) и сверка внесения жалоб с
Google-таблицами (переиспользуется «Контроль жалоб»).

Сохранены полезные блоки прежней страницы: статистика операторов,
совместные дни, нагрузка по часам МСК (до 02:00 = предыдущий день),
категории жалоб и сводные по ресторанам, анализ сбоев бота, Excel
с диаграммами. Вкладка «Невнесённые» по CRM заменена ссылкой на
«Контроль жалоб» (по правилам от 10.11 внесение проверяется только
по Битрикс-чатам и Google-таблицам).

Семантика (решён/не решён, тон, не к месту, брань Гостя, объединение
повторов) — очередь ручной разметки, БЕЗ ИИ. Бизнес-логика — в
report/os_work/builder.py.
"""
import io
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from config.greetings import get_current_greeting
from config.holidays import get_today_holiday
from styles import apply_subtle_theme, get_os_styles

from report.os_work import constants as c
from report.os_work.builder import build_os_work_report
from report.os_work.models import OsWorkRequest, OsWorkSettings, OsWorkSourceFiles
from report.complaints_control.gsheets import fetch_main_table

try:
    from config.effects import celebrate_report_success
except Exception:
    celebrate_report_success = None

try:
    from components import render_theme_controls
except Exception:
    render_theme_controls = None

MSK = timezone(timedelta(hours=3))


def greeting_by_time():
    hour = datetime.now(MSK).hour
    if 5 <= hour < 12:
        return "🌅 Доброе утро!"
    if 12 <= hour < 18:
        return "🌤 Добрый день!"
    if 18 <= hour < 23:
        return "🌆 Добрый вечер!"
    return "🌜 Доброй ночи!"


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_sheet_bytes(city: str) -> bytes:
    return fetch_main_table(city).getvalue()


def _export_period(uploaded) -> tuple:
    """Лёгкое чтение метаданных выгрузки для периода по умолчанию."""
    try:
        uploaded.seek(0)
        data = json.load(uploaded)
        uploaded.seek(0)
        period = data.get("period") or {}
        d1 = datetime.strptime(str(period.get("from"))[:10], "%Y-%m-%d").date()
        d2 = datetime.strptime(str(period.get("to_inclusive"))[:10], "%Y-%m-%d").date()
        return d1, d2, bool(data.get("complete")), str(data.get("format") or "")
    except Exception:
        return None, None, None, ""


def render():
    if render_theme_controls is not None:
        try:
            render_theme_controls()
        except Exception:
            pass

    greeting_data = get_current_greeting() or {}
    holiday = get_today_holiday() or {}
    theme_name = greeting_data.get("theme") if isinstance(greeting_data, dict) else None
    holiday_effects = holiday.get("effects") if isinstance(holiday, dict) else None
    apply_subtle_theme(theme_name, holiday_effects)
    st.markdown(get_os_styles(), unsafe_allow_html=True)

    st.markdown(
        f'<div class="header-block">'
        f'<h1>💬 Проверка работы ОС</h1>'
        f'<p>{greeting_by_time()}</p>'
        f'<p style="margin-top:10px; margin-bottom:0; font-size:16px;">'
        f'Скорость ответа, решение вопросов, нагрузка и замечания — по методике v4. '
        f'Спорные случаи размечаются вручную, без ИИ.</p></div>',
        unsafe_allow_html=True,
    )

    # ---------------- ЗАГРУЗКА ----------------
    st.markdown("### 📂 Загрузка данных")
    crm_file = st.file_uploader(
        "CRM-выгрузка: JSON реестра и полных диалогов (crm-pj-readonly-unified-2)",
        type=["json"], key="ow_crm",
    )
    file_period = (None, None, None, "")
    if crm_file is not None:
        file_period = _export_period(crm_file)
        d1, d2, complete, fmt = file_period
        if d1 and d2:
            flag = "полная" if complete else "⚠️ неполная (complete=false)"
            st.caption(f"Период выгрузки: **{d1.strftime('%d.%m.%Y')} – {d2.strftime('%d.%m.%Y')}** · {flag}")
        else:
            st.warning("Не удалось прочитать метаданные выгрузки — проверьте, что это JSON сборщика CRM.")

    st.markdown("##### 💬 Чаты ресторанов Битрикс24 *(необязательно — для листов «Работа с ресторанами» и «Не внесённые жалобы»)*")
    col1, col2 = st.columns(2)
    with col1:
        chat_spb = st.file_uploader("«Обратная связь Гости» (СПб)", type=["csv"], key="ow_chat_spb")
    with col2:
        chat_tmn = st.file_uploader("«Гости ОС Тюмень»", type=["csv"], key="ow_chat_tmn")

    check_not_entered = False
    main_spb = main_tmn = None
    if chat_spb is not None or chat_tmn is not None:
        check_not_entered = st.checkbox(
            "Сверять внесение жалоб с Google-таблицами (СПб и Тюмень читаются по ссылке автоматически)",
            value=True, key="ow_check_ne",
        )
        with st.expander("Запасной вариант: загрузить главные таблицы файлами"):
            mc1, mc2 = st.columns(2)
            with mc1:
                main_spb = st.file_uploader("«ОС и компенсации» (СПб)", type=["xlsx", "xls"], key="ow_main_spb")
            with mc2:
                main_tmn = st.file_uploader("«Обратная_связь_Тюмень»", type=["xlsx", "xls"], key="ow_main_tmn")

    # ---------------- ПЕРИОД ----------------
    st.markdown("---")
    st.markdown("### 📅 Период проверки")
    today = datetime.now(MSK).date()
    def_start, def_end = file_period[0], file_period[1]
    if def_start is None:
        def_start = today - timedelta(days=7)
    if def_end is None:
        def_end = today
    pc1, pc2 = st.columns(2)
    suffix = crm_file.name if crm_file is not None else "none"
    with pc1:
        date_start = st.date_input("Дата начала", value=def_start, key=f"ow_start_{suffix}")
    with pc2:
        date_end = st.date_input("Дата конца", value=def_end, key=f"ow_end_{suffix}")
    st.caption(
        "Ожидание относится к периоду первого вопроса Гостя; ответы после конца периода "
        "по этим вопросам учитываются. Недельный период, пересекающий месяцы, относится "
        "к месяцу последнего дня."
    )

    generate = st.button("🚀 Сформировать отчёт", use_container_width=True, type="primary", key="ow_generate")
    if generate:
        if crm_file is None:
            st.error("⚠️ Загрузите CRM-выгрузку (JSON).")
            st.stop()
        if date_start > date_end:
            st.error("⚠️ Дата начала позже даты конца.")
            st.stop()
        with st.spinner("⏳ Обработка выгрузки..."):
            try:
                eff_main_spb, eff_main_tmn = main_spb, main_tmn
                if check_not_entered and eff_main_spb is None and eff_main_tmn is None:
                    try:
                        eff_main_spb = io.BytesIO(_fetch_sheet_bytes("СПб"))
                        eff_main_tmn = io.BytesIO(_fetch_sheet_bytes("Тюмень"))
                    except Exception as e:
                        st.warning(
                            f"Google-таблицы недоступны ({e}). Лист «Не внесённые жалобы» "
                            "будет пропущен — можно загрузить таблицы файлами выше."
                        )
                crm_file.seek(0)
                files = OsWorkSourceFiles(
                    crm_json=crm_file.read(),
                    chat_spb=chat_spb, chat_tmn=chat_tmn,
                    main_spb=eff_main_spb, main_tmn=eff_main_tmn,
                )
                settings = OsWorkSettings(True, date_start, date_end)
                request = OsWorkRequest(
                    files=files, settings=settings, check_not_entered=check_not_entered,
                )
                result = build_os_work_report(request)
                if not result.success:
                    st.error(f"❌ Ошибка: {result.error}")
                    st.stop()
                st.session_state["ow_request"] = request
                st.session_state["ow_result"] = result
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"❌ Не удалось сформировать отчёт: {e}")

    result = st.session_state.get("ow_result")
    if result is not None:
        _render_result(result)


def _render_result(result) -> None:
    for warning in result.warnings:
        st.warning(warning)
    st.success(f"✅ Отчёт сформирован: {result.period_label}")
    data = result.data
    if data is None:
        return

    t = data.totals
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📨 Обращений", t.get("обращений", 0))
    m2.metric("⏱ Среднее ответа, мин", t.get("среднее") if t.get("среднее") is not None else "—")
    m3.metric("🔇 Без ответа", t.get("без ответа", 0))
    m4.metric("🐢 Дольше 20 мин", t.get("дольше 20", 0))
    m5.metric("🧑‍⚖️ Размечено", f"{t.get('размечено', 0)} из {t.get('всего размечать', 0)}")

    dl1, dl2, dl3 = st.columns(3)
    with dl1:
        st.download_button(
            "📥 Excel руководителю", result.excels.get("руководителю"),
            file_name=result.file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True, key="ow_dl_main",
        )
    for col, emp in ((dl2, "Женя"), (dl3, "Полина")):
        with col:
            if emp in result.excels:
                st.download_button(
                    f"📥 Личная книга: {emp}", result.excels[emp],
                    file_name=result.personal_file_names.get(emp, f"{emp}.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True, key=f"ow_dl_{emp}",
                )

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Дашборд", "⏱ Скорость", "🧑‍⚖️ Разметка", "📈 Нагрузка",
        "🍕 Жалобы и рестораны", "🤖 Бот", "🔧 Полнота и внимание",
    ])
    with tab1:
        _tab_dashboard(data)
    with tab2:
        _tab_speed(data)
    with tab3:
        _tab_review(data, result)
    with tab4:
        _tab_load(data)
    with tab5:
        _tab_complaints(data)
    with tab6:
        _tab_bot(data)
    with tab7:
        _tab_coverage(data)


def _tab_dashboard(data) -> None:
    st.markdown("##### 📋 Основные показатели")
    st.caption(
        "Личные количества включают совместные обращения у обоих участников; "
        "скорость относится к фактическому автору ответа. Ориентир среднего — 10 минут. "
        "Строки с нулевым показателем не выводятся."
    )
    st.dataframe(data.dashboard, use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Группы времени ответа")
        st.dataframe(data.speed_groups, use_container_width=True, hide_index=True)
    with c2:
        st.markdown("##### Решение вопроса")
        st.dataframe(data.outcomes, use_container_width=True, hide_index=True)


def _tab_speed(data) -> None:
    st.markdown(f"##### 🐢 Ответ дольше 20 рабочих минут")
    if data.long_answers.empty:
        st.success("✅ Долгих ожиданий нет.")
    else:
        st.dataframe(data.long_answers, use_container_width=True, hide_index=True)
    st.markdown("##### 🌙 Ответили только на следующий день (первый ответ)")
    if data.next_day.empty:
        st.info("Нет первых ответов на следующий день.")
    else:
        st.dataframe(data.next_day, use_container_width=True, hide_index=True)
    st.markdown("##### 🔇 Обращения без ответа")
    if data.unanswered.empty:
        st.success("✅ Все вопросы периода получили ответ.")
    else:
        st.dataframe(data.unanswered, use_container_width=True, hide_index=True)
    with st.expander("Все ожидания (включая прошлые периоды)"):
        st.dataframe(data.waits, use_container_width=True, hide_index=True)


def _tab_review(data, result) -> None:
    st.markdown("##### 🧑‍⚖️ Очередь ручной разметки")
    st.caption(
        "Решён/не решён, тон, ответ не к месту и брань Гостя правила определить не могут — "
        "решение за вами, без ИИ. «Подсказка» — детерминированный признак, не решение. "
        "Неразмеченные обращения не входят в знаменатель решённости. После разметки "
        "нажмите «Пересобрать Excel»."
    )
    if data.review_queue.empty:
        st.info("Нет обращений для разметки.")
    else:
        editable = {"Результат", "Тон", "Не к месту", "Брань Гостя"}
        disabled = [col for col in data.review_queue.columns if col not in editable]
        edited = st.data_editor(
            data.review_queue,
            column_config={
                "Результат": st.column_config.SelectboxColumn(
                    "Результат", options=[c.REVIEW_DEFAULT, *c.REVIEW_OUTCOME_CHOICES.keys()], required=True),
                "Тон": st.column_config.SelectboxColumn(
                    "Тон", options=list(c.REVIEW_TONE_CHOICES.keys()), required=True),
                "Не к месту": st.column_config.SelectboxColumn(
                    "Не к месту", options=list(c.REVIEW_WRONG_CHOICES.keys()), required=True),
                "Брань Гостя": st.column_config.SelectboxColumn(
                    "Брань Гостя", options=list(c.REVIEW_ABUSE_CHOICES.keys()), required=True),
                "Суть обращения": st.column_config.TextColumn(width="large"),
                "Последний ответ ОС": st.column_config.TextColumn(width="large"),
            },
            disabled=disabled, hide_index=True, use_container_width=True,
            key="ow_review_editor",
        )

    merge_edited = None
    if not data.merge_queue.empty:
        st.markdown("##### 🔗 Возможные повторы (один телефон, разные вопросы)")
        st.caption("Объединять только если это один и тот же вопрос Гостя. Разные жалобы по одному заказу проверяйте по сути.")
        merge_edited = st.data_editor(
            data.merge_queue,
            column_config={
                "Решение": st.column_config.SelectboxColumn(
                    "Решение", options=[c.MERGE_DEFAULT, *c.MERGE_CHOICES.keys()], required=True),
            },
            disabled=[col for col in data.merge_queue.columns if col != "Решение"],
            hide_index=True, use_container_width=True, key="ow_merge_editor",
        )

    if st.button("🔄 Пересобрать Excel с разметкой", use_container_width=True, key="ow_rebuild"):
        overrides = {"outcome": {}, "tone": {}, "wrong": {}, "abuse": {}, "merge": {}}
        if not data.review_queue.empty:
            for _, row in edited.iterrows():
                key = row["Ключ"]
                outcome = c.REVIEW_OUTCOME_CHOICES.get(row.get("Результат"))
                if outcome:
                    overrides["outcome"][key] = outcome
                if c.REVIEW_TONE_CHOICES.get(row.get("Тон")):
                    overrides["tone"][key] = "tone"
                if c.REVIEW_WRONG_CHOICES.get(row.get("Не к месту")):
                    overrides["wrong"][key] = "wrong"
                if c.REVIEW_ABUSE_CHOICES.get(row.get("Брань Гостя")):
                    overrides["abuse"][key] = "abuse"
        if merge_edited is not None:
            for _, row in merge_edited.iterrows():
                if c.MERGE_CHOICES.get(row.get("Решение")):
                    overrides["merge"][row["Ключ"]] = "merge"
        request = st.session_state.get("ow_request")
        if request is not None:
            new_request = OsWorkRequest(
                files=request.files, settings=request.settings,
                overrides=overrides, check_not_entered=request.check_not_entered,
            )
            with st.spinner("⏳ Пересборка с вашей разметкой..."):
                new_result = build_os_work_report(new_request)
            if new_result.success:
                st.session_state["ow_request"] = new_request
                st.session_state["ow_result"] = new_result
                if celebrate_report_success is not None:
                    celebrate_report_success()
                st.rerun()
            else:
                st.error(f"❌ Ошибка: {new_result.error}")


def _tab_load(data) -> None:
    st.markdown("##### 📆 По дням (одна строка на дату)")
    st.dataframe(data.daily, use_container_width=True, hide_index=True)
    if not data.weekly.empty:
        st.markdown("##### 🗓 По неделям — отдел, Женя, Полина")
        st.dataframe(data.weekly, use_container_width=True, hide_index=True)
    st.markdown("##### 🕐 Нагрузка по часам (МСК, до 02:00 = предыдущий день)")
    st.caption("Считаются сообщения гостей.")
    st.dataframe(data.hourly, use_container_width=True, hide_index=True)
    if not data.hourly.empty:
        st.bar_chart(data.hourly.set_index("Интервал")[["Сообщений/час", "Сообщений/час/день"]])
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### По дням недели")
        st.dataframe(data.weekday, use_container_width=True, hide_index=True)
    with c2:
        st.markdown("##### 👥 Совместная работа")
        if data.joint.empty:
            st.info("Дней с ответами обоих сотрудников нет.")
        else:
            st.dataframe(data.joint, use_container_width=True, hide_index=True)


def _tab_complaints(data) -> None:
    st.markdown("##### 📋 Детальные категории жалоб по ресторанам")
    if data.pivot_detailed.empty:
        st.info("Нет данных.")
    else:
        st.dataframe(data.pivot_detailed, use_container_width=True, hide_index=True)
    st.markdown("##### 📋 Укрупнённые категории")
    if not data.pivot_aggregated.empty:
        st.dataframe(data.pivot_aggregated, use_container_width=True, hide_index=True)
    st.markdown("---")
    st.markdown("##### 🤝 Работа с ресторанами (Битрикс)")
    if data.restaurant_work.empty:
        st.info("Загрузите чаты Битрикс, чтобы видеть передачу жалоб и ответы ресторанов.")
    else:
        st.dataframe(data.restaurant_work, use_container_width=True, hide_index=True)
        st.caption("«Ответ не найден» в доступных CSV не доказывает молчание ресторана; изменения текущего заказа ответа не требуют.")
    if not data.reverse_requests.empty:
        st.markdown("##### ↩️ Запросы ресторанов к ОС")
        st.dataframe(data.reverse_requests, use_container_width=True, hide_index=True)
    st.markdown("---")
    st.markdown("##### 🕵️ Не внесённые жалобы")
    if data.not_entered.empty and data.probable.empty:
        st.info(
            "Лист пуст: нужны чаты Битрикс и главные таблицы. Полная проверка внесения "
            "живёт на отдельной странице:"
        )
    else:
        st.dataframe(data.not_entered, use_container_width=True, hide_index=True)
        if not data.probable.empty:
            st.markdown("###### Вероятные совпадения — требуют сверки")
            st.dataframe(data.probable, use_container_width=True, hide_index=True)
    st.markdown("[🕵️ Открыть «Контроль жалоб» — полная проверка внесения](/ControlComplaints)")


def _tab_bot(data) -> None:
    st.markdown("##### 🤖 Ошибки чат-бота и запросы оператора")
    if data.bot_fails.empty:
        st.success("✅ Сбоев бота не обнаружено.")
        return
    c1, c2 = st.columns([1, 3])
    with c1:
        st.metric("Сбоев бота", len(data.bot_fails))
        st.dataframe(data.bot_fails["Тип ошибки бота"].value_counts(), use_container_width=True)
    with c2:
        st.dataframe(data.bot_fails, use_container_width=True, hide_index=True)


def _tab_coverage(data) -> None:
    st.markdown("##### 🔧 Требует внимания")
    if data.attention.empty:
        st.info("Тем, требующих внимания, не найдено.")
    else:
        st.dataframe(data.attention, use_container_width=True, hide_index=True)
    st.markdown("##### ⏳ Ожидания прошлых периодов")
    if not data.old_period_closed.empty:
        st.markdown("###### Закрытые в этом периоде (принадлежат прошлому)")
        st.dataframe(data.old_period_closed, use_container_width=True, hide_index=True)
    if not data.old_period_open.empty:
        st.markdown("###### Незавершённые (продолжения, не новые обращения)")
        st.dataframe(data.old_period_open, use_container_width=True, hide_index=True)
    st.markdown("##### 📜 Полнота источников")
    for note in data.coverage_notes:
        st.markdown(f"- {note}")
