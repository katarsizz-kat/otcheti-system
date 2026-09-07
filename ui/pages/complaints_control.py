"""
Визуальный слой страницы «Контроль жалоб».
Отвечает только за интерфейс: шапка, 5 загрузчиков (главные таблицы СПб/
Тюмень, чаты СПб/Тюмень, issues_report), период, допуск по дате, кнопка
генерации, превью и скачивание результата.
Бизнес-логики здесь нет — всё делает report/complaints_control/builder.py.
"""
import streamlit as st
from datetime import datetime

from styles import apply_theme
from config.greetings import get_current_greeting
from config.holidays import get_today_holiday
from report.complaints_control.builder import build_complaints_control_report
from report.complaints_control.models import (
    ControlReportRequest,
    ControlSourceFiles,
    ControlSettings,
)

PAGE_CSS = """
<style>
.element-container:has(> .stFileUploader) {
    background: white;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    border: 2px solid transparent;
    transition: all 0.3s ease;
}
.element-container:has(> .stFileUploader):hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.12);
}
.stFileUploader > div > div {
    border: 2px dashed rgba(0,0,0,0.2) !important;
    border-radius: 8px !important;
    background: rgba(255,255,255,0.8) !important;
}
.header-block {
    padding: 24px;
    border-radius: 16px;
    margin-bottom: 24px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.15);
}
.header-block h1 { margin: 0; font-size: 36px; }
.header-block p { margin-top: 8px; margin-bottom: 0; font-size: 18px; }
</style>
"""


def greeting_by_time() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "🌅 Доброе утро!"
    if 12 <= hour < 18:
        return "🌤 Добрый день!"
    if 18 <= hour < 23:
        return "🌙 Добрый вечер!"
    return "🌜 Доброй ночи!"


def render_header() -> None:
    greeting_data = get_current_greeting()
    holiday = get_today_holiday()
    holiday_effects = holiday.get("effects") if holiday and isinstance(holiday, dict) else None
    apply_theme(greeting_data["theme"], holiday_effects)
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="header-block">
            <h1>🕵️ Контроль жалоб</h1>
            <p>{greeting_by_time()}</p>
            <p>Проверяем, все ли жалобы гостей из чатов и issues_report занесены
            в главную таблицу компенсаций (СПб и Тюмень)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_uploaders():
    st.markdown("### 📂 Главные таблицы («ОС и компенсации»)")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🏙 СПб — лист «Обращения»")
        main_spb = st.file_uploader(
            "Главная СПб", type=["xlsx", "xls"], key="cc_main_spb", label_visibility="collapsed",
        )
    with col2:
        st.markdown("#### 🌇 Тюмень — «Обратная_связь_Тюмень» *(опционально)*")
        main_tmn = st.file_uploader(
            "Главная Тюмень", type=["xlsx", "xls"], key="cc_main_tmn", label_visibility="collapsed",
        )

    st.markdown("### 💬 Источники для сверки")
    col3, col4, col5 = st.columns(3)
    with col3:
        st.markdown("#### 💬 Чат «Обратная связь Гости» (СПб) *(опц.)*")
        chat_spb = st.file_uploader(
            "Чат СПб", type=["csv"], key="cc_chat_spb", label_visibility="collapsed",
        )
    with col4:
        st.markdown("#### 💬 Чат «Гости ОС Тюмень» *(опц.)*")
        chat_tmn = st.file_uploader(
            "Чат Тюмень", type=["csv"], key="cc_chat_tmn", label_visibility="collapsed",
        )
    with col5:
        st.markdown("#### 🎫 issues_report (вся сеть) *(опц.)*")
        issues_report = st.file_uploader(
            "issues_report", type=["xlsx", "xls"], key="cc_issues", label_visibility="collapsed",
        )

    return main_spb, main_tmn, chat_spb, chat_tmn, issues_report


def render_period_settings():
    st.markdown("---")
    st.subheader("⚙️ Период и сопоставление")
    all_dates = st.checkbox("Все даты (без фильтра)", value=False, key="cc_all_dates")
    date_start = None
    date_end = None
    if not all_dates:
        today = datetime.now().date()
        default_start = today.replace(day=1)
        col_a, col_b = st.columns(2)
        with col_a:
            date_start = st.date_input("Дата начала", value=default_start, key="cc_date_start")
        with col_b:
            date_end = st.date_input("Дата конца", value=today, key="cc_date_end")
    tolerance_days = st.slider(
        "Допуск по дате при сопоставлении телефон+дата (дней)",
        min_value=0, max_value=14, value=3, key="cc_tolerance",
        help="Жалоба из источника считается «НАЙДЕНО», если в главной таблице "
             "есть запись с тем же телефоном в пределах ±N дней от даты обращения.",
    )
    return all_dates, date_start, date_end, tolerance_days


def render_result(result) -> None:
    for warning in result.warnings:
        st.warning(warning)
    st.success(f"✅ Отчёт сформирован: {result.period_label}")
    st.download_button(
        "📥 Скачать Excel",
        result.excel,
        file_name=result.file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    data = result.data
    if data is None:
        return

    if data.classification_preview is not None and not data.classification_preview.empty:
        st.subheader("🔍 Статистика классификации")
        st.caption(
            "Сколько сообщений/тикетов прогнано через классификатор и почему "
            "часть из них не признана жалобой — здесь удобнее всего заметить "
            "нежелательный побочный эффект от правил (см. ТЗ §9)."
        )
        st.dataframe(data.classification_preview, use_container_width=True)

    st.subheader("💬 Сопоставление — чаты")
    st.dataframe(data.comparison_chats, use_container_width=True)

    st.subheader("🎫 Сопоставление — issues_report")
    st.dataframe(data.comparison_issues, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**🔴 НЕ ЗАНЕСЕНО:** {len(data.not_entered_all)}")
        if not data.not_entered_all.empty:
            st.dataframe(data.not_entered_all, use_container_width=True)
    with col_b:
        st.markdown(f"**🟣 НЕ ПОДТВЕРЖДЕНО ИСТОЧНИКОМ:** {len(data.not_confirmed_main)}")
        if not data.not_confirmed_main.empty:
            st.dataframe(data.not_confirmed_main, use_container_width=True)

    if not data.no_phone_all.empty:
        st.markdown(f"**🟡 НЕТ ТЕЛЕФОНА — ручная проверка:** {len(data.no_phone_all)}")
        st.dataframe(data.no_phone_all, use_container_width=True)

    st.subheader("👤 % незанесённых по сотруднику (чаты)")
    st.dataframe(data.employee_not_entered_share, use_container_width=True)

    st.subheader("🏠 По ресторанам")
    st.dataframe(data.restaurant_summary, use_container_width=True)

    with st.expander("📈 5 метрик (лист «Метрики» в Excel)"):
        st.markdown("**1. Доля невыплаченной компенсации**")
        st.dataframe(data.metric_unpaid_compensation, use_container_width=True)
        st.markdown("**2. Доля подтверждённых нарушений стандарта (только СПб)**")
        st.dataframe(data.metric_deviation_confirmed, use_container_width=True)
        st.markdown("**3. Стоимость компенсаций**")
        st.dataframe(data.metric_compensation_cost, use_container_width=True)
        st.markdown("**4. Незакрытый бэклог issues_report**")
        st.dataframe(data.metric_backlog, use_container_width=True)
        st.markdown("**5. Распределение способов компенсации**")
        st.dataframe(data.metric_decision_distribution, use_container_width=True)


def render_page() -> None:
    st.set_page_config(page_title="🕵️ Контроль жалоб", page_icon="🕵️", layout="wide")
    render_header()

    main_spb, main_tmn, chat_spb, chat_tmn, issues_report = render_uploaders()
    all_dates, date_start, date_end, tolerance_days = render_period_settings()

    generate = st.button("🚀 Сформировать отчёт", use_container_width=True, type="primary")
    if not generate:
        return

    if not (main_spb or main_tmn):
        st.error("⚠️ Загрузите хотя бы одну главную таблицу (СПб или Тюмень).")
        st.stop()
    if not (chat_spb or chat_tmn or issues_report):
        st.error("⚠️ Загрузите хотя бы один источник для сверки (чаты или issues_report).")
        st.stop()
    if not all_dates and date_start and date_end and date_start > date_end:
        st.error("⚠️ Дата начала позже даты конца.")
        st.stop()

    with st.spinner("⏳ Обработка данных..."):
        try:
            files = ControlSourceFiles(
                main_spb=main_spb,
                main_tmn=main_tmn,
                chat_spb=chat_spb,
                chat_tmn=chat_tmn,
                issues_report=issues_report,
            )
            settings = ControlSettings(
                use_period=not all_dates,
                date_start=date_start,
                date_end=date_end,
                tolerance_days=tolerance_days,
            )
            request = ControlReportRequest(files=files, settings=settings)
            result = build_complaints_control_report(request)

            if not result.success:
                st.error(f"❌ Ошибка: {result.error}")
                st.stop()

            render_result(result)

        except Exception as e:
            st.error(f"❌ Произошла ошибка при обработке: {e}")
            st.exception(e)
