import html
from typing import Callable, Optional, Tuple

import streamlit as st

from components import render_theme_controls
from report.foodcost_snacks import build_snacks_report
from report.foodcost_pizza import build_pizza_report
from report.foodcost_drinks import build_drinks_report


CITIES = ["СПб", "Тюмень"]
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def render() -> None:
    render_theme_controls()

    title = html.escape("📊 Foodcost отчёты")
    subtitle = html.escape(
        "Заполнение шаблонов по закускам, пицце и напиткам для СПб и Тюмени"
    )

    st.markdown(
        f'<div class="header-block"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )

    snacks_tab, pizza_tab, drinks_tab = st.tabs(
        ["Закуски", "Пицца", "Напитки"]
    )

    with snacks_tab:
        _render_report(
            key="fc_snacks",
            heading="Закуски",
            description=(
                "Блок «Сейчас»: заполняется столбец сс. "
                "Блок «Продажи»: заполняется столбец кол-во."
            ),
            builder=build_snacks_report,
            cost_label="Себестоимость закусок",
            sales_label="Продажи закусок",
            disabled=False,
        )

    with pizza_tab:
        _render_report(
            key="fc_pizza",
            heading="Пицца",
            description=(
                "Лист СС: блок Сейчас — столбцы сс. "
                "Лист продажи: блок Сейчас — столбец кол-во."
            ),
            builder=build_pizza_report,
            cost_label="Себестоимость пиццы",
            sales_label="Продажи пиццы",
            disabled=False,
        )

    with drinks_tab:
        _render_report(
            key="fc_drinks",
            heading="Напитки",
            description=(
                "Блок «Сейчас»: заполняется столбец сс. "
                "Блок «Продажи»: заполняется столбец кол-во."
            ),
            builder=build_drinks_report,
            cost_label="Себестоимость напитков",
            sales_label="Продажи напитков",
            disabled=True,
            disabled_reason=(
                "Напитки пока не подключены. "
                "Для этого модуля нужны исходные файлы себестоимости и продаж напитков."
            ),
        )


def _render_report(
    *,
    key: str,
    heading: str,
    description: str,
    builder: Optional[Callable[..., Tuple[bytes, str]]],
    cost_label: str,
    sales_label: str,
    disabled: bool = False,
    disabled_reason: Optional[str] = None,
) -> None:
    st.subheader(heading)
    st.caption(description)

    if disabled and disabled_reason:
        st.info(disabled_reason)

    settings_col, files_col = st.columns([1, 2])

    with settings_col:
        city = st.selectbox(
            "Город",
            options=CITIES,
            key=f"{key}_city",
        )

        template_file = st.file_uploader(
            "Шаблон отчёта",
            type=["xlsx"],
            key=f"{key}_template",
            help=(
                "Загрузи шаблон, который нужно заполнить. "
                "Например, закуски шаблон, себестоимость шаблон или шаблон Тюмени."
            ),
        )

    with files_col:
        cost_file = st.file_uploader(
            cost_label,
            type=["xls", "xlsx"],
            key=f"{key}_cost",
        )

        sales_file = st.file_uploader(
            sales_label,
            type=["xls", "xlsx"],
            key=f"{key}_sales",
        )

    ready = bool(template_file and cost_file and sales_file)
    button_disabled = disabled or not ready or builder is None

    if st.button(
        "Сформировать отчёт",
        type="primary",
        key=f"{key}_build",
        disabled=button_disabled,
    ):
        if builder is None:
            st.warning("Для этого отчёта ещё не подключена бизнес-логика.")
            return

        try:
            report_bytes, file_name = builder(
                city=city,
                template_file=template_file,
                cost_file=cost_file,
                sales_file=sales_file,
            )

            st.download_button(
                label="Скачать отчёт",
                data=report_bytes,
                file_name=file_name,
                mime=XLSX_MIME,
                key=f"{key}_download",
            )

            st.success(
                "Отчёт сформирован. Формулы и форматирование шаблона сохранены."
            )

        except Exception as exc:  # noqa: BLE001
            st.error(f"Не удалось сформировать отчёт: {exc}")