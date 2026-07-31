"""Стили для конкретных страниц приложения."""

# Стили для страницы КР месяц (более светлые и приглушённые)
KR_MONTH_STYLES = {
    "morning": {
        "header_bg": "linear-gradient(135deg, #FADBD8 0%, #D4E6F1 100%)",
        "uploader_border": "#AED6F1",
        "uploader_bg": "#F8F9F9",
        "text_primary": "#2C3E50",
        "text_secondary": "#5D6D7E",
    },
    "day": {
        "header_bg": "linear-gradient(135deg, #D6EAF8 0%, #EBF5FB 100%)",
        "uploader_border": "#85C1E9",
        "uploader_bg": "#F8F9F9",
        "text_primary": "#2C3E50",
        "text_secondary": "#5D6D7E",
    },
    "evening": {
        "header_bg": "linear-gradient(135deg, #FADBD8 0%, #D7BDE2 100%)",
        "uploader_border": "#C39BD3",
        "uploader_bg": "#F8F9F9",
        "text_primary": "#2C3E50",
        "text_secondary": "#5D6D7E",
    },
    "night": {
        "header_bg": "linear-gradient(135deg, #1A5276 0%, #2E86C1 100%)",
        "uploader_border": "#5DADE2",
        "uploader_bg": "#1B4F72",
        "text_primary": "#EAF2F8",
        "text_secondary": "#D4E6F1",
    },
    # Праздничные темы (осветлённые)
    "new_year": {
        "header_bg": "linear-gradient(135deg, #1B4F72 0%, #2E86C1 100%)",
        "uploader_border": "#5DADE2",
        "uploader_bg": "#1B4F72",
        "text_primary": "#EAF2F8",
        "text_secondary": "#D4E6F1",
    },
    "spring": {
        "header_bg": "linear-gradient(135deg, #D5F5E3 0%, #FADBD8 100%)",
        "uploader_border": "#A9DFBF",
        "uploader_bg": "#F8F9F9",
        "text_primary": "#2C3E50",
        "text_secondary": "#5D6D7E",
    },
    "summer": {
        "header_bg": "linear-gradient(135deg, #F9E79F 0%, #FADBD8 100%)",
        "uploader_border": "#F7DC6F",
        "uploader_bg": "#F8F9F9",
        "text_primary": "#2C3E50",
        "text_secondary": "#5D6D7E",
    },
    "childrens_day": {
        "header_bg": "linear-gradient(135deg, #FADBD8 0%, #D7BDE2 100%)",
        "uploader_border": "#F1948A",
        "uploader_bg": "#F8F9F9",
        "text_primary": "#2C3E50",
        "text_secondary": "#5D6D7E",
    },
    "knowledge_day": {
        "header_bg": "linear-gradient(135deg, #85C1E9 0%, #BB8FCE 100%)",
        "uploader_border": "#5DADE2",
        "uploader_bg": "#1B4F72",
        "text_primary": "#EAF2F8",
        "text_secondary": "#D4E6F1",
    },
    "april_fools": {
        "header_bg": "linear-gradient(135deg, #F9E79F 0%, #FADBD8 100%)",
        "uploader_border": "#F7DC6F",
        "uploader_bg": "#F8F9F9",
        "text_primary": "#2C3E50",
        "text_secondary": "#5D6D7E",
    },
    "magic": {
        "header_bg": "linear-gradient(135deg, #2C3E50 0%, #6C3483 100%)",
        "uploader_border": "#8E44AD",
        "uploader_bg": "#1B4F72",
        "text_primary": "#EAF2F8",
        "text_secondary": "#D4E6F1",
    },
    "scifi": {
        "header_bg": "linear-gradient(135deg, #1B4F72 0%, #2E86C1 100%)",
        "uploader_border": "#5DADE2",
        "uploader_bg": "#1B4F72",
        "text_primary": "#EAF2F8",
        "text_secondary": "#D4E6F1",
    },
    "military": {
        "header_bg": "linear-gradient(135deg, #2C3E50 0%, #5D6D7E 100%)",
        "uploader_border": "#7F8C8D",
        "uploader_bg": "#1B4F72",
        "text_primary": "#EAF2F8",
        "text_secondary": "#D4E6F1",
    },
}

def get_page_styles(page_name: str, theme: str) -> dict:
    """Возвращает стили для конкретной страницы и темы."""
    pages = {
        "kr_month": KR_MONTH_STYLES,
        # Можно добавить другие страницы позже
        # "kr_week": KR_WEEK_STYLES,
        # "os": OS_STYLES,
    }
    page_styles = pages.get(page_name, KR_MONTH_STYLES)
    return page_styles.get(theme, page_styles["day"])
