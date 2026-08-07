# ui/pages/kr.py

"""
UI-слой объединённой страницы КР.

Ответственность файла:
- интерфейс выбора режима: месяц / неделя;
- загрузка трёх файлов;
- настройки месяца и недели;
- запуск формирования отчёта через report-слой;
- отображение результата: предупреждения, ошибка, скачивание Excel, превью.

Здесь не должно быть:
- бизнес-расчётов;
- чтения Excel-данных;
- генерации Excel-файла;
- маппинга ресторанов;
- анализа отзывов.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import streamlit as st

# ==========================================================
# ИМПОРТ КОНСТАНТ
# ==========================================================
try:
    from report.kr import constants as c
except Exception:
    c = None

MODE_MONTH = getattr(c, "MODE_MONTH", "month")
MODE_WEEK = getattr(c, "MODE_WEEK", "week")

MODE_LABELS = getattr(
    c,
    "MODE_LABELS",
    {
        MODE_MONTH: "📅 Месяц",
        MODE_WEEK: "📆 Неделя",
    },
)

MONTH_MODE_LABEL = MODE_LABELS.get(MODE_MONTH, "📅 Месяц")
WEEK_MODE_LABEL = MODE_LABELS.get(MODE_WEEK, "📆 Неделя")

PAGE_TITLE = getattr(c, "PAGE_TITLE", "📊 КР отзывы")
PAGE_SUBTITLE = getattr(
    c,
    "PAGE_SUBTITLE",
    "Отчёт по отзывам из трёх источников: сайт, агрегаторы, геосервисы",
)

MONTHS = getattr(
    c,
    "MONTHS",
    [
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ],
)

DEFAULT_PRICE_THRESHOLD = getattr(c, "DEFAULT_PRICE_THRESHOLD", 749)

DEFAULT_YEAR_MIN = getattr(c, "DEFAULT_YEAR_MIN", 2020)
DEFAULT_YEAR_MAX = getattr(c, "DEFAULT_YEAR_MAX", 2035)

SOURCE_SITE = getattr(c, "SOURCE_SITE", "site")
SOURCE_AGG = getattr(c, "SOURCE_AGG", "agg")
SOURCE_GEO = getattr(c, "SOURCE_GEO", "geo")

SOURCE_LABELS = getattr(
    c,
    "SOURCE_LABELS",
    {
        SOURCE_SITE: "Сайт / приложение",
        SOURCE_AGG: "Агрегаторы",
        SOURCE_GEO: "Геосервисы",
    },
)

ACCEPTED_FILE_TYPES = getattr(c, "ACCEPTED_FILE_TYPES", ["xlsx", "xls"])

# ==========================================================
# ИМПОРТ МОДЕЛЕЙ
# ==========================================================
try:
    from report.kr.models import (
        KRMonthSettings,
        KRReportRequest,
        KRReportSettings,
        KRSourceFiles,
        KRWeekSettings,
    )

    MODELS_AVAILABLE = True
except Exception:
    KRMonthSettings = None
    KRReportRequest = None
    KRReportSettings = None
    KRSourceFiles = None
    KRWeekSettings = None
    MODELS_AVAILABLE = False

# ==========================================================
# ИМПОРТ БИЛДЕРА
# ==========================================================
try:
    from report.kr.builder import build_kr_report

    BUILDER_AVAILABLE = True
except Exception:
    build_kr_report = None
    BUILDER_AVAILABLE = False

# ==========================================================
# ИМПОРТ ТЕМЫ
# ==========================================================
try:
    from styles import apply_theme
    from config.greetings import get_current_greeting
    from config.holidays import get_today_holiday

    THEME_ENABLED = True
except Exception:
    apply_theme = None
    get_current_greeting = None
    get_today_holiday = None
    THEME_ENABLED = False

# ==========================================================
# МОСКОВСКОЕ ВРЕМЯ
# ==========================================================
MSK = timezone(timedelta(hours=3))


# ==========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================================
def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
    """
    Безопасно получает атрибут из объекта или ключ из словаря.
    """
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def _greeting_by_time() -> str:
    """
    Возвращает приветствие по московскому времени.
    """
    hour = datetime.now(MSK).hour

    if 5 <= hour < 12:
        return "🌅 Доброе утро!"

    if 12 <= hour < 18:
        return "🌤 Добрый день!"

    if 18 <= hour < 23:
        return "🌙 Добрый вечер!"

    return "🌜 Доброй ночи!"


def _default_month_year() -> tuple[str, int]:
    """
    Возвращает месяц и год по умолчанию: предыдущий месяц.
    """
    now = datetime.now(MSK)

    if now.month == 1:
        return MONTHS[-1], now.year - 1

    return MONTHS[now.month - 2], now.year


def _default_week_period() -> tuple[Any, Any]:
    """
    Возвращает период недели по умолчанию:
    с 1 числа месяца последней завершённой недели до её конца.
    """
    today = datetime.now(MSK).date()

    # Последний воскресенье строго до сегодняшнего дня.
    days_since_sunday = (today.weekday() + 1) % 7

    if days_since_sunday == 0:
        days_since_sunday = 7

    end_date = today - timedelta(days=days_since_sunday)
    start_date = end_date.replace(day=1)

    return start_date, end_date


def _apply_theme() -> None:
    """
    Применяет общую тему приложения.
    """
    if not THEME_ENABLED:
        return

    try:
        theme_name = None
        holiday_effects = None

        if get_current_greeting is not None:
            greeting_data = get_current_greeting()

            if isinstance(greeting_data, dict):
                theme_name = greeting_data.get("theme")

        if get_today_holiday is not None:
            holiday = get_today_holiday()

            if isinstance(holiday, dict):
                holiday_effects = holiday.get("effects")

        if apply_theme is not None:
            apply_theme(theme_name, holiday_effects)
    except Exception:
        pass


def _apply_local_css() -> None:
    """
    Минимальные локальные стили для заголовка страницы.
    """
    st.markdown(
        """
        <style>
        .header-block {
            padding: 24px;
            border-radius: 16px;
            margin-bottom: 24px;
            background: rgba(255, 255, 255, 0.75);
            border: 1px solid rgba(0, 0, 0, 0.06);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
        }

        .header-block h1 {
            margin: 0;
            font-size: 34px;
            font-weight: 800;
        }

        .header-block p {
            margin-top: 8px;
            margin-bottom: 0;
            font-size: 17px;
            opacity: 0.85;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _seek_file(file_obj: Any) -> None:
    """
    Перематывает загруженный файл в начало перед повторным чтением.
    """
    if file_obj is None:
        return

    try:
        file_obj.seek(0)
    except Exception:
        pass


# ==========================================================
# ОТОБРАЖЕНИЕ РЕЗУЛЬТАТА
# ==========================================================
def _render_result(result: Any) -> None:
    """
    Отображает результат формирования отчёта.
    """
    success = bool(_get_attr(result, "success", False))
    error = _get_attr(result, "error")
    warnings = _get_attr(result, "warnings", []) or []
    period_label = str(_get_attr(result, "period_label", "") or "")
    file_name = str(_get_attr(result, "file_name", "") or "КР_отчет.xlsx")
    excel = _get_attr(result, "excel")
    preview = _get_attr(result, "preview")
    data = _get_attr(result, "data")
    generated_at = _get_attr(result, "generated_at")

    # Предупреждения показываем и при успехе, и при ошибке
    if isinstance(warnings, str):
        st.warning(warnings)
    elif warnings:
        for warning_message in warnings:
            st.warning(str(warning_message))

    if not success:
        if error:
            st.error(f"❌ Ошибка формирования отчёта: {error}")
        else:
            st.error("❌ Не удалось сформировать отчёт.")
        return

    # Успех
    if period_label:
        st.success(f"✅ Отчёт успешно сформирован: {period_label}")
    else:
        st.success("✅ Отчёт успешно сформирован!")

    if generated_at:
        try:
            st.caption(f"Сформировано: {generated_at:%d.%m.%Y %H:%M}")
        except Exception:
            st.caption(f"Сформировано: {generated_at}")

    # Скачивание Excel
    if excel is not None:
        if hasattr(excel, "seek"):
            try:
                excel.seek(0)
            except Exception:
                pass

        st.download_button(
            label="📥 Скачать Excel",
            data=excel,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="kr_download_button",
        )
    else:
        st.warning("Файл Excel не был передан в результате.")

    # Просмотр данных
    complaints = _get_attr(data, "complaints")
    positives = _get_attr(data, "positives")

    available_tabs: list[str] = []

    if preview is not None:
        available_tabs.append("📈 Общий итог")

    if complaints is not None:
        available_tabs.append("😠 Жалобы")

    if positives is not None:
        available_tabs.append("😊 Позитив")

    if not available_tabs:
        return

    st.subheader("📊 Просмотр данных")

    tabs = st.tabs(available_tabs)
    tab_index = 0

    if preview is not None:
        with tabs[tab_index]:
            st.dataframe(preview, use_container_width=True)
        tab_index += 1

    if complaints is not None:
        with tabs[tab_index]:
            st.dataframe(complaints, use_container_width=True)
        tab_index += 1

    if positives is not None:
        with tabs[tab_index]:
            st.dataframe(positives, use_container_width=True)
        tab_index += 1


# ==========================================================
# ОСНОВНАЯ ФУНКЦИЯ СТРАНИЦЫ
# ==========================================================
def render_page() -> None:
    """
    Точка входа для страницы КР.
    Вызывается из pages/1_KR.py.
    """
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon="📊",
        layout="wide",
    )

    _apply_theme()
    _apply_local_css()

    # ------------------------------------------------------
    # ЗАГОЛОВОК
    # ------------------------------------------------------
    st.markdown(
        f"""
        <div class="header-block">
            <h1>{PAGE_TITLE}</h1>
            <p>{_greeting_by_time()}</p>
            <p>{PAGE_SUBTITLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------
    # РЕЖИМ ОТЧЁТА
    # ------------------------------------------------------
    mode_label = st.radio(
        "Режим отчёта",
        [MONTH_MODE_LABEL, WEEK_MODE_LABEL],
        horizontal=True,
    )

    is_month = mode_label == MONTH_MODE_LABEL
    mode = MODE_MONTH if is_month else MODE_WEEK

    # Если пользователь переключил режим, старый результат очищаем
    if st.session_state.get("kr_report_mode") != mode:
        st.session_state.pop("kr_report_result", None)
        st.session_state.pop("kr_report_mode", None)

    # ------------------------------------------------------
    # ЗАГРУЗКА ФАЙЛОВ
    # ------------------------------------------------------
    st.markdown("### 📂 Загрузка файлов")

    col_site, col_agg, col_geo = st.columns(3)

    with col_site:
        st.markdown(f"#### 📱 {SOURCE_LABELS.get(SOURCE_SITE, 'Сайт / приложение')}")
        file_site = st.file_uploader(
            "Загрузите Excel",
            type=ACCEPTED_FILE_TYPES,
            key="kr_uploader_site",
            label_visibility="collapsed",
        )

    with col_agg:
        st.markdown(f"#### 📦 {SOURCE_LABELS.get(SOURCE_AGG, 'Агрегаторы')}")
        file_agg = st.file_uploader(
            "Загрузите Excel",
            type=ACCEPTED_FILE_TYPES,
            key="kr_uploader_agg",
            label_visibility="collapsed",
        )

    with col_geo:
        st.markdown(f"#### 🗺 {SOURCE_LABELS.get(SOURCE_GEO, 'Геосервисы')}")
        file_geo = st.file_uploader(
            "Загрузите Excel",
            type=ACCEPTED_FILE_TYPES,
            key="kr_uploader_geo",
            label_visibility="collapsed",
        )

    st.markdown("---")

    # ------------------------------------------------------
    # НАСТРОЙКИ
    # ------------------------------------------------------
    st.subheader("⚙️ Настройки")

    if is_month:
        st.caption(
            "Месячный режим: удалённые отзывы из геосервисов не учитываются. "
            "Порог суммы применяется только к сайту."
        )

        default_month, default_year = _default_month_year()

        col_month, col_year, col_threshold = st.columns(3)

        with col_month:
            selected_month = st.selectbox(
                "Месяц отчёта",
                MONTHS,
                index=MONTHS.index(default_month),
            )

        with col_year:
            selected_year = st.number_input(
                "Год",
                value=default_year,
                min_value=DEFAULT_YEAR_MIN,
                max_value=DEFAULT_YEAR_MAX,
                step=1,
            )

        with col_threshold:
            price_threshold = st.number_input(
                "Минимальная сумма заказа",
                value=DEFAULT_PRICE_THRESHOLD,
                min_value=0,
                step=10,
            )

        period_enabled = False
        start_date = None
        end_date = None
        custom_label = ""

    else:
        st.caption(
            "Недельный режим: удалённые отзывы из геосервисов учитываются. "
            "Порог суммы не применяется."
        )

        period_enabled = st.checkbox(
            "Ограничить период датами",
            value=False,
            help=(
                "Если не отмечено — отчёт формируется по всем датам из файлов. "
                "Если отмечено — используются выбранные даты."
            ),
        )

        start_date = None
        end_date = None

        if period_enabled:
            default_start, default_end = _default_week_period()

            col_start, col_end = st.columns(2)

            with col_start:
                start_date = st.date_input(
                    "Дата начала",
                    value=default_start,
                )

            with col_end:
                end_date = st.date_input(
                    "Дата конца",
                    value=default_end,
                )

        custom_label = st.text_input(
            "Подпись периода (опционально)",
            placeholder="Например: 1-9 августа",
            help=(
                "Если оставить пустым, подпись будет сформирована автоматически. "
                "Если даты не выбраны, будет использована подпись «Все даты»."
            ),
        )

        selected_month = None
        selected_year = None
        price_threshold = None

    st.markdown("---")

    # ------------------------------------------------------
    # КНОПКА ФОРМИРОВАНИЯ
    # ------------------------------------------------------
    generate_report = st.button(
        "🚀 Сформировать отчёт",
        use_container_width=True,
        type="primary",
    )

    if generate_report:
        if not MODELS_AVAILABLE:
            st.error("⚠️ Не удалось импортировать модели из `report/kr/models.py`.")
            st.stop()

        if not BUILDER_AVAILABLE or build_kr_report is None:
            st.error("⚠️ Не удалось импортировать `build_kr_report` из `report/kr/builder.py`.")
            st.stop()

        if not (file_site and file_agg and file_geo):
            st.error("⚠️ Пожалуйста, загрузите все три Excel-файла.")
            st.stop()

        if is_month:
            settings = KRReportSettings(
                mode=MODE_MONTH,
                month=KRMonthSettings(
                    selected_month=selected_month,
                    selected_year=int(selected_year),
                    price_threshold=int(price_threshold),
                ),
            )
        else:
            if period_enabled:
                if not start_date or not end_date:
                    st.error(
                        "⚠️ Укажите дату начала и дату конца периода "
                        "или снимите галочку «Ограничить период датами»."
                    )
                    st.stop()

                if end_date < start_date:
                    st.error("⚠️ Дата конца не может быть раньше даты начала.")
                    st.stop()

            settings = KRReportSettings(
                mode=MODE_WEEK,
                week=KRWeekSettings(
                    use_period=period_enabled,
                    start_date=start_date if period_enabled else None,
                    end_date=end_date if period_enabled else None,
                    custom_label=custom_label,
                ),
            )

        # Перед повторной загрузкой перематываем файлы в начало
        _seek_file(file_site)
        _seek_file(file_agg)
        _seek_file(file_geo)

        files = KRSourceFiles(
            site=file_site,
            agg=file_agg,
            geo=file_geo,
        )

        request = KRReportRequest(
            files=files,
            settings=settings,
        )

        try:
            with st.spinner("⏳ Формирование отчёта..."):
                result = build_kr_report(request)

            if result is None:
                st.error("❌ Отчёт не был сформирован: пустой результат.")
                st.stop()

            st.session_state["kr_report_result"] = result
            st.session_state["kr_report_mode"] = mode

        except Exception as exc:
            st.error(f"❌ Произошла ошибка при формировании отчёта: {exc}")
            st.exception(exc)
            st.stop()

    # ------------------------------------------------------
    # ОТОБРАЖЕНИЕ РЕЗУЛЬТАТА
    # ------------------------------------------------------
    result = st.session_state.get("kr_report_result")

    if result is None:
        st.info(
            "Загрузите файлы, настройте параметры и нажмите "
            "«🚀 Сформировать отчёт»."
        )
        return

    _render_result(result)


# ==========================================================
# ПРЯМОЙ ЗАПУСК ДЛЯ ЛОКАЛЬНОЙ ПРОВЕРКИ
# ==========================================================
if __name__ == "__main__":
    render_page()