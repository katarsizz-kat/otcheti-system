from typing import Any, Tuple

from report.foodcost_common import make_placeholder_report, safe_file_name


def build_drinks_report(
    *,
    city: str,
    template_file: Any,
    cost_file: Any,
    sales_file: Any,
) -> Tuple[bytes, str]:
    """
    Будущая логика:
    - блок «Сейчас»: заполняем столбец сс;
    - блок «Продажи»: заполняем столбец кол-во;
    - себестоимость напитков не округляем;
    - маппинг названий напитков отдельный;
    - исходные данные по напиткам пока не подключены.
    """
    data = make_placeholder_report(f"Напитки | {city}")
    file_name = safe_file_name(city, "drinks")

    return data, file_name
