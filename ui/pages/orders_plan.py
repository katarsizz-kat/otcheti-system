"""Чистый UI слой страницы «План заказов».
Не содержит бизнес-логику расчёта — только вызовы report/orders_plan.py.
"""
from datetime import date

import pandas as pd
import streamlit as st

import report.orders_plan as logic

from config.greetings import get_current_greeting
from config.holidays import get_today_holiday
from styles import apply_subtle_theme

try:
    from config.effects import celebrate_report_success
except Exception:
    celebrate_report_success = None

try:
    from components import render_theme_controls
except Exception:
    render_theme_controls = None


def _month_options(center: date, back: int = 6, forward: int = 18):
    """Список месяцев для выпадающего списка: `back` месяцев назад .. `forward` вперёд от center."""
    start = logic.shift_months(center, -back)
    return [logic.shift_months(start, i) for i in range(back + forward + 1)]


def _format_month(d: date) -> str:
    return f"{logic.MONTHS_RU[d.month - 1].capitalize()} {d.year}"


def render():
    """Основная точка входа UI."""
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

    st.markdown(
        """
<div class="header-block fade-in">
    <h1>📈 План заказов</h1>
    <p>Прогноз количества заказов по ресторанам на выбранный месяц</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("### 📂 Загрузка данных")
    uploaded_file = st.file_uploader(
        "Загрузите файл истории заказов по ресторанам (.xlsx)",
        type=["xlsx"],
        key="orders_plan_uploader",
    )
    if not uploaded_file:
        st.info("👆 Загрузите файл с помесячной историей заказов, чтобы построить план.")
        return

    try:
        history = logic.load_history(uploaded_file)
    except Exception as e:
        st.error(f"❌ Не удалось прочитать файл: {e}")
        return

    if history.empty:
        st.warning("В файле не найдено ни одной строки с данными по ресторанам.")
        return

    last_period = history["period"].max()
    default_target = logic.shift_months(last_period, 1)
    st.success(
        f"✅ Загружено ресторанов: **{history['restaurant'].nunique()}** | "
        f"история: **{history['period'].min():%m.%Y}** — **{last_period:%m.%Y}**"
    )

    st.markdown("---")
    st.markdown("### 🎯 Целевой период")

    options = _month_options(default_target)
    labels = [_format_month(m) for m in options]

    col1, col2 = st.columns(2)
    with col1:
        start_idx = st.selectbox(
            "Месяц (начало периода):",
            options=range(len(options)),
            format_func=lambda i: labels[i],
            index=options.index(default_target),
            key="orders_plan_start",
        )
    with col2:
        is_range = st.checkbox("Период из нескольких месяцев", key="orders_plan_is_range")
        end_idx = start_idx
        if is_range:
            end_idx = st.selectbox(
                "Месяц (конец периода):",
                options=range(start_idx, len(options)),
                format_func=lambda i: labels[i],
                index=0,
                key="orders_plan_end",
            )

    target_period = f"{options[start_idx]:%Y-%m}:{options[end_idx]:%Y-%m}"

    all_restaurants = logic.sort_restaurants(history["restaurant"].unique())
    selected_restaurants = st.multiselect(
        "Рестораны (по умолчанию — все):",
        options=all_restaurants,
        default=all_restaurants,
        key="orders_plan_restaurants",
    )

    deviation_pct = st.slider(
        "Порог отклонения прогноза от тренда для пометки «проверить», %",
        min_value=5, max_value=50, value=15, step=1,
        key="orders_plan_deviation",
    )

    if not st.button("🧮 Рассчитать план", type="primary", use_container_width=True):
        return

    if not selected_restaurants:
        st.warning("Выберите хотя бы один ресторан.")
        return

    with st.spinner("⏳ Считаю план..."):
        plan = logic.build_plan(
            history,
            target_period,
            restaurants=selected_restaurants,
            deviation_threshold=deviation_pct / 100,
        )

    st.markdown("---")
    st.markdown("### 📊 Результат")

    total = plan["total"]
    m1, m2, m3 = st.columns(3)
    m1.metric("План на период, шт.", f"{total['plan']:,.0f}".replace(",", " "))
    m2.metric("Ресторанов", total["restaurant_count"])
    m3.metric("Требуют проверки", total["needs_review_count"])

    df = logic.plan_to_dataframe(plan)
    display_df = df.copy()
    display_df["target_period"] = pd.to_datetime(display_df["target_period"]).dt.strftime("%m.%Y")
    display_df["base_period"] = pd.to_datetime(display_df["base_period"]).dt.strftime("%m.%Y")
    for col in ("base_orders", "forecast_seasonal", "forecast_trend", "plan"):
        display_df[col] = display_df[col].round(0)
    display_df["seasonal_coef"] = display_df["seasonal_coef"].round(3)
    display_df["deviation_pct"] = display_df["deviation_pct"].round(1)
    display_df = display_df.rename(columns=logic.PLAN_COLUMN_LABELS)

    def _highlight_review(row):
        color = "background-color: rgba(230, 126, 34, 0.18)" if row.get("Проверить?") else ""
        return [color] * len(row)

    st.dataframe(
        display_df.style.apply(_highlight_review, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    if total["needs_review_count"]:
        st.warning(
            f"⚠️ {total['needs_review_count']} ресторан(ов) с отклонением прогноза от тренда "
            f"больше {deviation_pct}% — отмечены в таблице, стоит проверить вручную."
        )

    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        try:
            workbook_bytes = logic.export_plan_workbook(
                history, target_period,
                restaurants=selected_restaurants,
                deviation_threshold=deviation_pct / 100,
            )
            st.download_button(
                label="📥 Скачать план с формулами (.xlsx)",
                data=workbook_bytes,
                file_name="План_заказов_формулы.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="Лист «Данные» + лист(ы) «План_<Месяц>» — коэффициент, "
                     "прогноз, тренд и план как формулы Excel, а не готовые числа.",
            )
            if celebrate_report_success is not None:
                celebrate_report_success()
        except Exception as e:
            st.error(f"❌ Не удалось сформировать Excel-файл с формулами: {e}")
    with dl_col2:
        try:
            excel_bytes = logic.export_plan_excel(plan)
            st.download_button(
                label="📋 Скачать как таблицу (.xlsx)",
                data=excel_bytes,
                file_name="План_заказов_таблица.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="Один лист с готовыми числами — без формул, для быстрой выгрузки.",
            )
        except Exception as e:
            st.error(f"❌ Не удалось сформировать таблицу: {e}")
