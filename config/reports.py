"""Описание карточек отчётов."""

REPORTS = [
    {
        "id": "kr_month",
        "title": "КР месяц",
        "description": "Сводный отчёт по отзывам за месяц из трёх источников",
        "icon": "📅",
        "page": "KR_month",
        "color": "#3498DB",
        "gradient": "linear-gradient(135deg, #3498DB 0%, #85C1E9 100%)",
    },
    {
        "id": "kr_week",
        "title": "КР неделя",
        "description": "Еженедельный отчёт по отзывам",
        "icon": "📈",
        "page": "KR_week",
        "color": "#2ECC71",
        "gradient": "linear-gradient(135deg, #2ECC71 0%, #82E0AA 100%)",
    },
    {
        "id": "produkt",
        "title": "Продукт",
        "description": "Сводный отчёт по продукту и категориям",
        "icon": "🍕",
        "page": "produkt",
        "color": "#E67E22",
        "gradient": "linear-gradient(135deg, #E67E22 0%, #F39C12 100%)",
    },
]


def get_reports() -> list:
    """Возвращает список отчётов."""
    return REPORTS


def get_report_by_id(report_id: str) -> dict | None:
    """Возвращает отчёт по id."""
    for report in REPORTS:
        if report["id"] == report_id:
            return report
    return None