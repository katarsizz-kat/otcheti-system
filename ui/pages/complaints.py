"""
Визуальный слой страницы «Анализ жалоб».
Отвечает только за интерфейс:
шапка и тема;
загрузка 4 файлов (сайт, агрегаторы, геосервисы, ОС);
выбор периода;
кнопка генерации;
превью и скачивание результата.
Бизнес-логики здесь нет — всё делает report/complaints/builder.py.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from styles import apply_theme
from config.greetings import get_current_greeting
from config.holidays import get_today_holiday
from report.complaints.builder import build_complaints_report
from report.complaints.models import (
    ComplaintsReportRequest,
    ComplaintsSourceFiles,
    ComplaintsSettings,
)

# ==========================================================
# CSS
# ==========================================================
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
.element-container:nth-child(1):has(> .stFileUploader) { border-color: #3498DB; }
.element-container:nth-child(2):has(> .stFileUploader) { border-color: #F1C40F; }
.element-container:nth-child(3):has(> .stFileUploader) { border-color: #27AE60; }
.element-container:nth-child(4):has(> .stFileUploader) { border-color: #9B59B6; }
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

# ==========================================================
# ШАПКА
# ==========================================================
def render_header() -> None:
    greeting_data = get_current_greeting()
    holiday = get_today_holiday()
    holiday_effects = (
        holiday.get("effects") if holiday and isinstance(holiday, dict) else None
    )
    apply_theme(greeting_data["theme"], holiday_effects)
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="header-block">
            <h1>📢 Анализ жалоб</h1>
            <p>{greeting_by_time()}</p>
            <p>Жалобы и позитив по отзывам и обращениям ОС — без дублей по номеру телефона</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==========================================================
# ЗАГРУЗКА ФАЙЛОВ
# ==========================================================
def render_uploaders():
    st.markdown("### 📂 Загрузка файлов")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("#### 📱 Сайт / приложение")
        file_site = st.file_uploader(
            "Сайт", type=["xlsx", "xls"], key="cmp_site", label_visibility="collapsed"
        )
    with col2:
        st.markdown("#### 🛒 Агрегаторы")
        file_agg = st.file_uploader(
            "Агрегаторы", type=["xlsx", "xls"], key="cmp_agg", label_visibility="collapsed"
        )
    with col3:
        st.markdown("#### 🗺 Геосервисы")
        file_geo = st.file_uploader(
            "Геосервисы", type=["xlsx", "xls"], key="cmp_geo", label_visibility="collapsed"
        )
    with col4:
        st.markdown("#### 📋 ОС и компенсации")
        file_os = st.file_uploader(
            "ОС", type=["xlsx", "xls"], key="cmp_os", label_visibility="collapsed"
        )
    return file_site, file_agg, file_geo, file_os

# ==========================================================
# НАСТРОЙКИ ПЕРИОДА
# ==========================================================
def render_period_settings():
    st.markdown("---")
    st.subheader("⚙️ Период")
    all_dates = st.checkbox("Все даты (без фильтра)", value=False)
    date_start = None
    date_end = None
    if not all_dates:
        today = datetime.now().date()
        default_start = today.replace(day=1)
        col_a, col_b = st.columns(2)
        with col_a:
            date_start = st.date_input("Дата начала", value=default_start)
        with col_b:
            date_end = st.date_input("Дата конца", value=today)
    return all_dates, date_start, date_end

# ==========================================================
# ПРЕВЬЮ РЕЗУЛЬТАТА
# ==========================================================
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

    st.subheader("📊 Сводная по жалобам")
    st.dataframe(data.complaint_summary, use_container_width=True)

    st.subheader("😊 Сводная по позитиву")
    st.dataframe(data.positive_summary, use_container_width=True)

    col_d, col_g = st.columns(2)
    with col_d:
        st.markdown(f"**Дубли по телефону:** {len(data.duplicates)}")
        if not data.duplicates.empty:
            st.dataframe(data.duplicates, use_container_width=True)
    with col_g:
        st.markdown(f"**Удалённые (гео):** {len(data.deleted_geo)}")
        if not data.deleted_geo.empty:
            st.dataframe(data.deleted_geo, use_container_width=True)

# ==========================================================
# ГЛАВНАЯ ФУНКЦИЯ СТРАНИЦЫ
# ==========================================================
def render_page() -> None:
    st.set_page_config(page_title="📢 Анализ жалоб", page_icon="📢", layout="wide")
    render_header()

    file_site, file_agg, file_geo, file_os = render_uploaders()
    all_dates, date_start, date_end = render_period_settings()

    generate = st.button("🚀 Сформировать отчёт", use_container_width=True, type="primary")
    if not generate:
        return

    if not (file_site and file_agg and file_geo and file_os):
        st.error("⚠️ Пожалуйста, загрузите все четыре Excel-файла.")
        st.stop()

    if not all_dates and date_start and date_end and date_start > date_end:
        st.error("⚠️ Дата начала позже даты конца.")
        st.stop()

    with st.spinner("⏳ Обработка данных..."):
        try:
            files = ComplaintsSourceFiles(
                site=file_site,
                agg=file_agg,
                geo=file_geo,
                os=file_os,
            )
            settings = ComplaintsSettings(
                use_period=not all_dates,
                date_start=date_start,
                date_end=date_end,
            )
            request = ComplaintsReportRequest(files=files, settings=settings)
            result = build_complaints_report(request)

            if not result.success:
                st.error(f"❌ Ошибка: {result.error}")
                st.stop()

            render_result(result)

        except Exception as e:
            st.error(f"❌ Произошла ошибка при обработке: {e}")
            st.exception(e)