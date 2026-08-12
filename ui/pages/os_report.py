"""Визуальная часть страницы отчёта ОС.
БЕЗ openpyxl. Один файл = одна задача.

v2.0 (дизайн-система Sage & Sandstone):
- st.balloons() заменён на celebrate_report_success() — пастельные шарики;
- render_theme_controls() — блок "Оформление" в сайдбаре (футера нет);
- приветствие по московскому времени (UTC+3), по правилу проекта.
"""
from datetime import datetime, timedelta, timezone
import pandas as pd
import streamlit as st

import report.os_report as logic

from config.greetings import get_current_greeting
from config.holidays import get_today_holiday
from styles import apply_subtle_theme, get_os_styles

# ==========================================================
# ИМПОРТ UI-ДОПОЛНЕНИЙ (шарики успеха + блок "Оформление")
# ==========================================================
try:
    from config.effects import celebrate_report_success
except Exception:
    celebrate_report_success = None

try:
    from components import render_theme_controls
except Exception:
    render_theme_controls = None

# Московское время (правило проекта: UTC+3)
MSK = timezone(timedelta(hours=3))


def greeting_by_time():
    """Приветствие в зависимости от часа (МСК)."""
    hour = datetime.now(MSK).hour
    if 5 <= hour < 12:
        return "🌅 Доброе утро!"
    if 12 <= hour < 18:
        return "🌤 Добрый день!"
    if 18 <= hour < 23:
        return "🌆 Добрый вечер!"
    return "🌜 Доброй ночи!"


def render():
    """Основная точка входа UI."""
    # Блок "Оформление" в сайдбаре (тема + праздничные эффекты)
    if render_theme_controls is not None:
        try:
            render_theme_controls()
        except Exception:
            pass

    # Тема
    greeting_data = get_current_greeting() or {}
    holiday = get_today_holiday() or {}
    theme_name = greeting_data.get("theme") if isinstance(greeting_data, dict) else None
    holiday_effects = holiday.get("effects") if isinstance(holiday, dict) else None
    apply_subtle_theme(theme_name, holiday_effects)

    # CSS (HTML с нулевой колонки)
    st.markdown(get_os_styles(), unsafe_allow_html=True)

    # Заголовок
    st.markdown(
        f'<div class="header-block">'
        f'<h1>💬 Отчёт по работе Отдела Обратной Связи (ОС)</h1>'
        f'<p>{greeting_by_time()}</p>'
        f'<p style="margin-top:10px; margin-bottom:0; font-size:16px;">'
        f'Анализ обращений, жалоб и работы операторов</p></div>',
        unsafe_allow_html=True,
    )

    # Загрузка файла
    st.markdown("### 📂 Загрузка данных")
    uploaded_file = st.file_uploader(
        "Загрузите выгрузку тикетов (Excel/CSV)",
        type=['xlsx', 'csv'],
        key="os_uploader",
    )
    if not uploaded_file:
        st.info("👆 Загрузите файл с выгрузкой обращений выше.")
        return

    try:
        df = logic.load_data(uploaded_file)
    except Exception as e:
        st.error(f"Ошибка чтения файла: {e}")
        return

    # Фильтры
    df_filtered = _render_filters(df)
    if df_filtered is None or df_filtered.empty:
        st.warning("Нет данных после применения фильтров.")
        return

    valid_dates = df_filtered['Дата отзыва'].dropna()
    if not valid_dates.empty:
        st.success(
            f"✅ Тикетов: **{len(df_filtered)}** | "
            f"**{valid_dates.min().date()}** — **{valid_dates.max().date()}**"
        )
    else:
        st.success(f"✅ Тикетов: **{len(df_filtered)}**")

    # Вкладки
    tab1, tab2, tab3, tab4 = st.tabs([
        "👨‍💼 Статистика операторов",
        "📊 Жалобы и Рестораны",
        "🤖 Анализ Чат-бота",
        "📥 Экспорт в Excel",
    ])

    # Общие вычисления для вкладок (один раз)
    df_op_full = df_filtered[
        (df_filtered['Исполнитель'].notna()) &
        (df_filtered['Исполнитель'] != 'Системный пользователь')
    ].copy()
    if not df_op_full.empty:
        df_op_full['Дата_МСК'] = df_op_full['Дата отзыва'] + logic.MSK_OFFSET
        df_op_full['Час_МСК'] = df_op_full['Дата_МСК'].dt.hour
        df_op_full['Дата_рабочая'] = df_op_full.apply(
            lambda r: (r['Дата_МСК'] - timedelta(days=1)).date()
            if r['Час_МСК'] < 2 else r['Дата_МСК'].date(), axis=1,
        )
        df_op_stats = logic.compute_operator_stats(df_op_full)
        h_stats, total_days = logic.compute_hourly_stats(df_op_full)
        day_stats, wd_stats = logic.compute_day_stats(df_op_full)
        joint_df = logic.compute_joint_work(df_op_full)
    else:
        df_op_stats = pd.DataFrame()
        h_stats = pd.DataFrame()
        day_stats = pd.DataFrame()
        wd_stats = pd.DataFrame()
        joint_df = pd.DataFrame()
        total_days = 0

    df_f, p1_for_ui, p2_for_ui, city_map = logic.compute_complaint_pivots(df_filtered)
    bot_df = logic.analyze_bot_fails(df_filtered)

    with tab1:
        _render_tab_operators(df_op_full, df_op_stats, h_stats, joint_df, total_days)
    with tab2:
        _render_tab_complaints(df_f, p1_for_ui, p2_for_ui)
    with tab3:
        _render_tab_bot(bot_df)
    with tab4:
        _render_tab_export(
            df_op_stats, h_stats, day_stats, wd_stats,
            p1_for_ui, p2_for_ui, bot_df, city_map,
        )


def _render_filters(df):
    st.markdown("---")
    st.markdown("### 🔍 Фильтры")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🏙️ Город/регион")
        available_cities = (
            df['Город'].dropna().unique().tolist()
            if 'Город' in df.columns else []
        )
        default_cities = [c for c in ['Санкт-Петербург', 'Тюмень'] if c in available_cities]
        cities = st.multiselect(
            "Город/регион:",
            options=available_cities,
            default=default_cities or available_cities[:3],
            key="os_cities",
        )
        df_filtered = df[df['Город'].isin(cities)] if cities else df.copy()

    with col2:
        st.markdown("#### 📅 Период")
        date_type = st.radio(
            "Тип фильтра:",
            ["Интервал дат", "Отдельные даты"],
            key="os_date_type",
        )
        valid_dates = df_filtered['Дата отзыва'].dropna()
        if not valid_dates.empty:
            min_d, max_d = valid_dates.min().date(), valid_dates.max().date()
            if date_type == "Интервал дат":
                dr = st.date_input(
                    "Период:",
                    value=(min_d, max_d),
                    min_value=min_d, max_value=max_d,
                    key="os_date_range",
                )
                if isinstance(dr, (list, tuple)) and len(dr) == 2:
                    df_filtered = logic.apply_filters(
                        df_filtered, cities, date_type, date_range=dr,
                    )
            else:
                ud = sorted(valid_dates.dt.date.unique(), reverse=True)
                sel = st.multiselect(
                    "Даты:",
                    options=ud,
                    default=ud[:7] if len(ud) >= 7 else ud,
                    key="os_dates",
                )
                if sel:
                    df_filtered = logic.apply_filters(
                        df_filtered, cities, date_type, selected_dates=sel,
                    )
    return df_filtered


def _render_tab_operators(df_op, df_op_stats, h_stats, joint_df, total_days):
    st.subheader("Загрузка операторов и распределение по часам")
    st.caption("⏱ Только живые операторы. МСК (+3 ч). До 02:00 = предыдущий день.")
    if df_op.empty:
        st.warning("Нет данных по живым операторам.")
        return

    st.markdown("##### 📋 Статистика по операторам")
    st.dataframe(df_op_stats, use_container_width=True, hide_index=True)

    st.markdown("##### 👥 Совместная работа операторов")
    st.caption(
        f"Дни, когда обращения обрабатывали несколько операторов. "
        f"Исключены: {', '.join(logic.EXCLUDED_OPERATORS)}"
    )
    if not joint_df.empty:
        st.dataframe(joint_df, use_container_width=True, hide_index=True)
    else:
        st.info(
            f"Каждый день работал один оператор (без учёта {', '.join(logic.EXCLUDED_OPERATORS)})."
        )

    st.markdown("##### 🕐 Распределение по часам (МСК)")
    st.caption(f"📆 Период: **{total_days} дней**")
    st.dataframe(h_stats, use_container_width=True, hide_index=True)
    if not h_stats.empty:
        st.bar_chart(h_stats.set_index('Интервал')[['Обращений/час', 'Обращений/час/день']])


def _render_tab_complaints(df_f, p1_for_ui, p2_for_ui):
    st.subheader("Аналитика жалоб по категориям и ресторанам")
    st.markdown("##### 📋 Таблица 1: Детальные категории жалоб")
    col1, col2 = st.columns([1, 2])
    with col1:
        if 'Категория' in df_f.columns:
            st.bar_chart(df_f['Категория'].value_counts())
    with col2:
        st.dataframe(p1_for_ui, use_container_width=True)

    st.markdown("---")
    st.markdown("##### 📋 Таблица 2: Укрупнённые категории жалоб")
    col3, col4 = st.columns([1, 2])
    with col3:
        if 'Категория_укрупн' in df_f.columns:
            agg_counts = df_f['Категория_укрупн'].value_counts()
            agg_sorted = pd.Series({
                k: agg_counts.get(k, 0)
                for k in logic.AGG_ORDER
                if agg_counts.get(k, 0) > 0
            })
            st.bar_chart(agg_sorted)
    with col4:
        st.dataframe(p2_for_ui, use_container_width=True)


def _render_tab_bot(bot_df):
    st.subheader("Ошибки чат-бота и запросы оператора")
    if not bot_df.empty:
        c1, c2 = st.columns([1, 3])
        with c1:
            st.metric("Сбоев бота", len(bot_df))
            st.dataframe(
                bot_df['Тип ошибки бота'].value_counts(),
                use_container_width=True,
            )
        with c2:
            st.dataframe(bot_df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Сбоев бота не обнаружено.")


def _render_tab_export(df_op_stats, h_stats, day_stats, wd_stats,
                       p1, p2, bot_df, city_map):
    st.subheader("📊 Генерация Excel-отчёта")
    st.info(
        "6 листов: Операторы · Часы · Дни · Жалобы (деталь) · "
        "Жалобы (укрупн) · Бот. С формулами =SUM и диаграммами!"
    )
    if st.button("📄 Сформировать и скачать Excel", type="primary", key="os_export_btn"):
        with st.spinner("Формируем отчёт..."):
            try:
                buf = logic.generate_excel_report(
                    df_op_stats=df_op_stats if not df_op_stats.empty else None,
                    h_stats=h_stats if not h_stats.empty else None,
                    day_stats=day_stats if not day_stats.empty else None,
                    wd_stats=wd_stats if not wd_stats.empty else None,
                    p1=p1 if not p1.empty else None,
                    p2=p2 if not p2.empty else None,
                    bot_df=bot_df if not bot_df.empty else None,
                    city_map=city_map,
                )
                st.download_button(
                    label="💾 Скачать отчёт (.xlsx)",
                    data=buf,
                    file_name="OS_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="os_download_btn",
                )
                # 🎈 Пастельные шарики при следующем рендере
                if celebrate_report_success is not None:
                    celebrate_report_success()
            except Exception as e:
                st.error(f"Ошибка при формировании Excel: {e}")