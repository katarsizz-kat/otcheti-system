"""
Визуальный слой страницы «Контроль жалоб» (проверка внесения жалоб).

Действующие правила (ред. 18.11.2026): источники — чаты ресторанов
Битрикс24 и Google-таблицы СПб/Тюмени (читаются напрямую по ссылке,
без ручной выгрузки; запасной вариант — файлы). CRM не используется.
Спорные случаи (вероятные совпадения, неполные ключи) размечаются
вручную в очереди проверки, после чего Excel пересобирается.

Бизнес-логики здесь нет — всё делает report/complaints_control/builder.py.
"""
import io

import streamlit as st
from datetime import datetime

from styles import apply_theme
from config.greetings import get_current_greeting
from config.holidays import get_today_holiday
from report.complaints_control.builder import (
    build_complaints_control_report,
    REVIEW_DEFAULT,
    REVIEW_CHOICES,
)
from report.complaints_control.gsheets import fetch_main_table
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


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_sheet_bytes(city: str) -> bytes:
    """Кеш на 5 минут: повторные пересборки отчёта не дёргают Google."""
    return fetch_main_table(city).getvalue()


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
            <p>Проверяем, все ли жалобы гостей из чатов ресторанов занесены
            в главную таблицу компенсаций (СПб и Тюмень). Источники — чаты
            Битрикс24 и Google-таблицы; CRM в этой проверке не используется.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_main_tables():
    st.markdown("### 📂 Главные таблицы («ОС и компенсации»)")
    source_mode = st.radio(
        "Откуда брать главные таблицы",
        ["Google-таблицы по ссылке (рекомендуется)", "Загрузить файлы вручную"],
        key="cc_main_source",
        horizontal=True,
        help="Таблицы СПб и Тюмени доступны по ссылке на чтение — сайт скачает "
             "актуальную версию сам, выгружать вручную не нужно.",
    )
    if source_mode.startswith("Google"):
        st.caption(
            "СПб: лист «Обращения» + «Сводная» · Тюмень: «Обратная_связь_Тюмень», лист «Лист1». "
            "Сверка идёт по всей таблице, включая старые строки."
        )
        return None, None, True

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
    return main_spb, main_tmn, False


def render_chat_uploaders():
    st.markdown("### 💬 Чаты ресторанов Битрикс24 (CSV-экспорт)")
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### 💬 «Обратная связь Гости» (СПб)")
        chat_spb = st.file_uploader(
            "Чат СПб", type=["csv"], key="cc_chat_spb", label_visibility="collapsed",
        )
    with col4:
        st.markdown("#### 💬 «Гости ОС Тюмень»")
        chat_tmn = st.file_uploader(
            "Чат Тюмень", type=["csv"], key="cc_chat_tmn", label_visibility="collapsed",
        )
    return chat_spb, chat_tmn


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
        "Допуск по дате для вероятных совпадений (дней)",
        min_value=0, max_value=14, value=3, key="cc_tolerance",
        help="Телефон совпал, но дата записи в таблице отличается не больше чем "
             "на N дней — это вероятное совпадение (требует сверки, не считается "
             "невнесённым). Точное совпадение — заказ или телефон+ресторан+дата+категория.",
    )
    return all_dates, date_start, date_end, tolerance_days


def render_result(result) -> None:
    for warning in result.warnings:
        st.warning(warning)
    st.success(f"✅ Отчёт сформирован: {result.period_label}")

    data = result.data
    if data is not None:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🔴 Не внесено", len(data.not_entered))
        m2.metric("🟠 Вероятные совпадения", len(data.probable))
        m3.metric("🟡 Неполные ключи", len(data.no_keys))
        m4.metric("🔧 Требует внимания", len(data.attention))

    st.download_button(
        "📥 Скачать Excel",
        result.excel,
        file_name=result.file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    if data is None:
        return

    if not data.review_queue.empty:
        st.subheader("🧑‍⚖️ Очередь проверки — спорные случаи")
        st.caption(
            "Вероятные совпадения и жалобы с неполными ключами не попадают в счётчик "
            "невнесённых автоматически. Просмотрите текст и запись таблицы, отметьте "
            "решение и пересоберите Excel — без ИИ, решение за вами."
        )
        disabled_cols = [col for col in data.review_queue.columns if col != "Решение"]
        edited = st.data_editor(
            data.review_queue,
            column_config={
                "Решение": st.column_config.SelectboxColumn(
                    "Решение",
                    options=[REVIEW_DEFAULT, *REVIEW_CHOICES.keys()],
                    required=True,
                ),
                "Суть обращения": st.column_config.TextColumn(width="large"),
            },
            disabled=disabled_cols,
            hide_index=True,
            use_container_width=True,
            key="cc_review_editor",
        )
        if st.button("🔄 Пересобрать Excel с разметкой", use_container_width=True):
            overrides = {}
            for _, row in edited.iterrows():
                decision = REVIEW_CHOICES.get(row.get("Решение"))
                if decision:
                    overrides[row["Ключ"]] = decision
            request = st.session_state.get("cc_request")
            if request is not None:
                new_request = ControlReportRequest(
                    files=request.files, settings=request.settings, overrides=overrides,
                )
                with st.spinner("⏳ Пересборка с вашей разметкой..."):
                    new_result = build_complaints_control_report(new_request)
                if new_result.success:
                    st.session_state["cc_request"] = new_request
                    st.session_state["cc_result"] = new_result
                    st.rerun()
                else:
                    st.error(f"❌ Ошибка: {new_result.error}")

    if data.classification_preview is not None and not data.classification_preview.empty:
        with st.expander("🔍 Статистика классификации"):
            st.caption(
                "Сколько групп сообщений прогнано через классификатор и почему "
                "часть не признана жалобой — здесь заметны побочные эффекты правил."
            )
            st.dataframe(data.classification_preview, use_container_width=True)

    with st.expander("🔴 Не внесённые жалобы"):
        st.dataframe(data.not_entered, use_container_width=True)
    with st.expander("🟠 Вероятные совпадения"):
        st.dataframe(data.probable, use_container_width=True)
    with st.expander("💬 Полное сопоставление (лист «Сверка»)"):
        st.dataframe(data.comparison, use_container_width=True)
    if not data.attention.empty:
        with st.expander("🔧 Требует внимания"):
            st.dataframe(data.attention, use_container_width=True)
    with st.expander("👤 По сотрудникам и 🏠 ресторанам"):
        st.dataframe(data.employee_not_entered_share, use_container_width=True)
        st.dataframe(data.restaurant_summary, use_container_width=True)


def render_page() -> None:
    st.set_page_config(page_title="🕵️ Контроль жалоб", page_icon="🕵️", layout="wide")
    render_header()

    main_spb, main_tmn, auto_sheets = render_main_tables()
    chat_spb, chat_tmn = render_chat_uploaders()
    all_dates, date_start, date_end, tolerance_days = render_period_settings()

    generate = st.button("🚀 Сформировать отчёт", use_container_width=True, type="primary")
    if generate:
        if not (chat_spb or chat_tmn):
            st.error("⚠️ Загрузите хотя бы один чат ресторанов (СПб или Тюмень).")
            st.stop()
        if not all_dates and date_start and date_end and date_start > date_end:
            st.error("⚠️ Дата начала позже даты конца.")
            st.stop()

        with st.spinner("⏳ Обработка данных..."):
            try:
                if auto_sheets:
                    main_spb = io.BytesIO(_fetch_sheet_bytes("СПб"))
                    main_tmn = io.BytesIO(_fetch_sheet_bytes("Тюмень"))
                elif not (main_spb or main_tmn):
                    st.error("⚠️ Загрузите хотя бы одну главную таблицу (СПб или Тюмень).")
                    st.stop()

                files = ControlSourceFiles(
                    main_spb=main_spb,
                    main_tmn=main_tmn,
                    chat_spb=chat_spb,
                    chat_tmn=chat_tmn,
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

                st.session_state["cc_request"] = request
                st.session_state["cc_result"] = result
                st.rerun()

            except Exception as e:  # noqa: BLE001
                st.error(
                    f"❌ Не удалось сформировать отчёт: {e}. "
                    "Если Google-таблицы недоступны — переключитесь на ручную загрузку файлов."
                )

    result = st.session_state.get("cc_result")
    if result is not None:
        render_result(result)