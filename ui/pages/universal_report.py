"""
Визуальная часть универсального отчёта.

Файл содержит только Streamlit-интерфейс.
Логика расчётов и генерация Excel находятся в:
    report/universal_report.py
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st


# ==========================================================
# ИМПОРТ ЛОГИКИ
# ==========================================================
try:
    from report.universal_report import (
        CITY_SPB,
        CITY_TYUMEN,
        aggregate_data,
        aggregate_pizza_by_size,
        create_excel,
        create_pizza_excel,
        extract_period,
        read_file,
    )
    LOGIC_IMPORT_ERROR = None
except Exception as exc:
    LOGIC_IMPORT_ERROR = str(exc)


# ==========================================================
# КОНСТАНТЫ РЕЖИМОВ
# ==========================================================
STANDARD_MODE = "📝 Стандартный отчёт"
PIZZA_MODE = "🍕 Пиццы по размерам"
REPORT_MODES = [STANDARD_MODE, PIZZA_MODE]

PIZZA_SIZES = ["15", "23", "30", "35", "40"]

DEFAULT_STANDARD_RULES = """Сырная 30
Четыре сыра 35
Пепперони 30
Картофель из печи 150 гр
Рогалики с колбасками"""

DEFAULT_PIZZA_RULES = """Сырная
Пепперони
Четыре Сыра
Мясная
Супер Папа
Гавайская
Цыпленок Барбекю
Маргарита
Мексиканская
Ветчина и Грибы"""


# ==========================================================
# HTML-БЛОКИ
# ВАЖНО: HTML должен начинаться с нулевой колонки,
# иначе Markdown превращает его в блок кода.
# ==========================================================
HEADER_HTML = """<div class="header-block">
<h1>📊 Универсальный отчёт</h1>
<p>Отчёт с разбивкой пицц по размерам и по конкретным позициям</p>
</div>"""

DESCRIPTION_HTML = """<div class="universal-card">
<h3>📋 Как работает отчёт</h3>
<h4>📝 Стандартный режим:</h4>
<ul>
<li>
<b>Гибкий поиск:</b> введите название позиции — программа найдёт все совпадения.
</li>
<li>
Если написано <code>Картофель из печи 150 гр</code> — считает только по этому весу.
Если написано <code>Картофель из печи</code> — считает оба веса.
</li>
<li>
<b>Результат:</b> количество и сумма по СПб и Тюмени для каждой позиции.
</li>
</ul>
<h4>🍕 Пиццы по размерам:</h4>
<ul>
<li>
Если нужен отчёт по пиццам с разбивкой по размерам —
переключитесь на режим <b>"🍕 Пиццы по размерам"</b>.
</li>
<li>
Программа автоматически сгруппирует размеры: 15, 23, 30, 35, 40 см.
</li>
<li>
Тонкое и традиционное тесто суммируются внутри каждого размера.
</li>
</ul>
</div>"""


# ==========================================================
# ТОЧКА ВХОДА ДЛЯ СТРАНИЦЫ
# ==========================================================
def render_universal_report() -> None:
    """
    Главный рендер страницы.
    Вызывается из pages/10_MINI.py.
    """
    _inject_styles()
    _render_header()
    _render_description()

    if LOGIC_IMPORT_ERROR is not None:
        st.error("❌ Не удалось импортировать логику из report/universal_report.py")
        st.code(LOGIC_IMPORT_ERROR)
        return

    report_mode = _render_mode_selector()
    rules_text = _render_rules_input(report_mode)
    uploaded_file = _render_file_uploader()

    if uploaded_file is None:
        st.info("👆 Загрузите файл для начала работы")
        return

    _render_report_section(uploaded_file, report_mode, rules_text)


# ==========================================================
# СТИЛИ
# ==========================================================
def _inject_styles() -> None:
    """
    Пытается использовать отдельную функцию стилей из styles.py.
    Если её ещё нет, применяет локальный fallback.
    """
    try:
        from styles import apply_universal_report_styles

        apply_universal_report_styles()
    except Exception:
        st.markdown(
            "<style>"
            ".universal-card { background: rgba(255,255,255,0.55); border: 1px solid rgba(255,255,255,0.7); border-radius: 14px; padding: 24px 28px; margin-bottom: 24px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); } "
            ".universal-card h3 { margin: 0 0 12px 0; } "
            ".universal-card h4 { margin: 16px 0 8px 0; } "
            ".universal-card p { margin: 0 0 12px 0; } "
            ".universal-card ul { margin: 0 0 8px 0; padding-left: 22px; } "
            ".universal-card li { margin-bottom: 6px; } "
            ".universal-card code { background: rgba(0,0,0,0.06); padding: 2px 6px; border-radius: 6px; } "
            "[data-testid='stTextArea'] textarea { border: 2px solid #4a90e2 !important; border-radius: 8px !important; padding: 12px !important; font-size: 14px !important; background-color: #ffffff !important; min-height: 300px !important; } "
            "[data-testid='stTextArea'] textarea:focus { border-color: #2c5aa0 !important; box-shadow: 0 0 8px rgba(74,144,226,0.3) !important; outline: none !important; } "
            "[data-testid='stTextArea'] textarea::placeholder { color: #6c757d !important; font-style: italic; opacity: 0.8; } "
            "[data-testid='stTextArea'] label { font-weight: 600; color: #333; margin-bottom: 8px; } "
            "</style>",
            unsafe_allow_html=True,
        )


# ==========================================================
# ШАПКА
# ==========================================================
def _render_header() -> None:
    st.markdown(HEADER_HTML, unsafe_allow_html=True)


# ==========================================================
# ОПИСАНИЕ
# ==========================================================
def _render_description() -> None:
    st.markdown(DESCRIPTION_HTML, unsafe_allow_html=True)


# ==========================================================
# ВЫБОР РЕЖИМА
# ==========================================================
def _render_mode_selector() -> str:
    return st.radio(
        "📋 Выберите режим отчёта:",
        REPORT_MODES,
        horizontal=True,
        help=(
            "Стандартный — обычный отчёт с количеством и суммой.\n"
            "Пиццы по размерам — отчёт с разбивкой по размерам 15, 23, 30, 35, 40 см."
        ),
    )


# ==========================================================
# ПОЛЕ ВВОДА СПИСКА ПОЗИЦИЙ
# ==========================================================
def _render_rules_input(report_mode: str) -> str:
    default_rules = DEFAULT_PIZZA_RULES if report_mode == PIZZA_MODE else DEFAULT_STANDARD_RULES
    height = 400 if report_mode == PIZZA_MODE else 300
    widget_key = (
        "universal_rules_input_pizza"
        if report_mode == PIZZA_MODE
        else "universal_rules_input_standard"
    )

    st.markdown("### ✏️ ВВЕДИТЕ СПИСОК ПОЗИЦИЙ")
    st.markdown(
        "<p><b>Каждая строка = одна позиция в отчёте.</b></p>",
        unsafe_allow_html=True,
    )

    rules_text = st.text_area(
        "Список позиций:",
        value="",
        height=height,
        key=widget_key,
        label_visibility="visible",
        placeholder=default_rules,
    )

    return rules_text


# ==========================================================
# ЗАГРУЗКА ФАЙЛА
# ==========================================================
def _render_file_uploader():
    st.markdown('<div class="universal-card">', unsafe_allow_html=True)
    st.markdown("### 📂 Загрузка файла")

    uploaded_file = st.file_uploader(
        "Загрузите файл рейтинг_продукт (Excel)",
        type=["xlsx"],
        key="universal_file_uploader",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    return uploaded_file


# ==========================================================
# ОСНОВНОЙ БЛОК ГЕНЕРАЦИИ
# ==========================================================
def _render_report_section(uploaded_file, report_mode: str, rules_text: str) -> None:
    st.markdown('<div class="universal-card">', unsafe_allow_html=True)

    period_str, period_ok = _get_period(uploaded_file)

    if period_ok:
        st.info(f"📅 Период: **{period_str}**")
    else:
        st.warning("⚠️ Не удалось определить период")
        st.info(f"📅 Период: **{period_str}**")

    if st.button(
        "📊 Сгенерировать отчёт",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Формирую отчёт..."):
            try:
                df = read_file(uploaded_file)
                rules = _parse_rules(rules_text)

                if not rules:
                    st.error("❌ Введите хотя бы одну позицию в поле выше!")
                elif report_mode == PIZZA_MODE:
                    data = aggregate_pizza_by_size(df, rules_text)
                    wb = create_pizza_excel(data, period_str, rules)

                    st.success("✅ Отчёт сформирован!")
                    _render_pizza_preview(data, rules)
                    _render_download_button(wb, period_str, report_mode)
                else:
                    data = aggregate_data(df, rules_text)
                    wb = create_excel(data, period_str, rules)

                    st.success("✅ Отчёт сформирован!")
                    _render_standard_preview(data, rules)
                    _render_download_button(wb, period_str, report_mode)

            except Exception as exc:
                st.error(f"❌ Ошибка: {exc}")

                import traceback

                st.code(traceback.format_exc())

    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ UI
# ==========================================================
def _get_period(uploaded_file) -> tuple[str, bool]:
    """
    Возвращает период и флаг успешности.
    Обязательно возвращает файл в начало, чтобы потом его можно было читать.
    """
    try:
        period_str = extract_period(uploaded_file)
        uploaded_file.seek(0)
        return period_str, True
    except Exception:
        uploaded_file.seek(0)
        return f"01.{datetime.now().strftime('%m')}.{datetime.now().year}", False


def _parse_rules(rules_text: str) -> list[str]:
    return [line.strip() for line in rules_text.splitlines() if line.strip()]


def _build_standard_preview(data: dict, rules: list[str], city: str) -> pd.DataFrame:
    preview_rows = []

    for rule in rules:
        preview_rows.append(
            {
                "Позиция": rule,
                "Количество": data[city][rule]["qty"],
                "Сумма, ₽": data[city][rule]["sum"],
            }
        )

    return pd.DataFrame(preview_rows)


def _build_pizza_preview(data: dict, rules: list[str], city: str) -> pd.DataFrame:
    preview_rows = []

    for rule in rules:
        row = {"Позиция": rule}

        for size in PIZZA_SIZES:
            row[f"{size} см"] = data[city][rule][size]["qty"]

        row["Всего"] = data[city][rule]["Всего"]["qty"]
        preview_rows.append(row)

    return pd.DataFrame(preview_rows)


def _render_standard_preview(data: dict, rules: list[str]) -> None:
    st.subheader("📋 Превью")

    tab_spb, tab_tyumen = st.tabs([f"🏙 {CITY_SPB}", f"🏙 {CITY_TYUMEN}"])

    with tab_spb:
        st.dataframe(
            _build_standard_preview(data, rules, CITY_SPB),
            use_container_width=True,
        )

    with tab_tyumen:
        st.dataframe(
            _build_standard_preview(data, rules, CITY_TYUMEN),
            use_container_width=True,
        )


def _render_pizza_preview(data: dict, rules: list[str]) -> None:
    st.subheader("📋 Превью")

    tab_spb, tab_tyumen = st.tabs([f"🏙 {CITY_SPB}", f"🏙 {CITY_TYUMEN}"])

    with tab_spb:
        st.dataframe(
            _build_pizza_preview(data, rules, CITY_SPB),
            use_container_width=True,
        )

    with tab_tyumen:
        st.dataframe(
            _build_pizza_preview(data, rules, CITY_TYUMEN),
            use_container_width=True,
        )


def _render_download_button(wb, period_str: str, report_mode: str) -> None:
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    file_prefix = "pizza_" if report_mode == PIZZA_MODE else ""
    file_name = f"Отчёт_{file_prefix}{period_str.replace('.', '-')}.xlsx"

    st.download_button(
        label="📥 Скачать Excel",
        data=output,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )