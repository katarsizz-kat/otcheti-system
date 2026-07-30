"""Модуль для экспорта календаря в PDF."""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime, date, timedelta
from typing import List, Dict
import io


def register_russian_fonts():
    """Зарегистрировать шрифты с поддержкой кириллицы."""
    # Используем встроенные шрифты с поддержкой кириллицы
    try:
        # Пробуем зарегистрировать DejaVu Sans (если есть в системе)
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
        return 'DejaVuSans', 'DejaVuSans-Bold'
    except:
        # Если не получилось, используем стандартные шрифты
        # Они могут не поддерживать кириллицу, но это лучше чем ничего
        return 'Helvetica', 'Helvetica-Bold'


def create_pdf_calendar(events: List[Dict], title: str = "Календарь событий") -> bytes:
    """
    Создать PDF файл с календарём событий.
    
    Args:
        events: Список событий
        title: Заголовок документа
    
    Returns:
        bytes: PDF файл в виде байтов
    """
    buffer = io.BytesIO()
    
    # Создаём документ в альбомной ориентации
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    # Стили
    styles = getSampleStyleSheet()
    
    # Создаём стили с поддержкой кириллицы
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        alignment=1,  # Центр
        textColor=colors.HexColor('#2C3E50')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        textColor=colors.HexColor('#34495E')
    )
    
    # Элементы документа
    elements = []
    
    # Заголовок
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Информация о генерации
    generated_date = datetime.now().strftime("%d.%m.%Y %H:%M")
    elements.append(Paragraph(f"<i>Сгенерировано: {generated_date}</i>", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Группируем события по датам
    events_by_date = {}
    for event in events:
        event_date = event.get('start_date', '')
        if event_date not in events_by_date:
            events_by_date[event_date] = []
        events_by_date[event_date].append(event)
    
    # Сортируем даты
    sorted_dates = sorted(events_by_date.keys())
    
    # Создаём таблицу
    table_data = [['Дата', 'Время', 'Событие', 'Категория', 'Локация']]
    
    for event_date in sorted_dates:
        date_events = events_by_date[event_date]
        
        # Форматируем дату
        try:
            date_obj = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            date_str = date_obj.strftime("%d.%m.%Y")
            day_name = date_obj.strftime("%A")
            
            # Перевод дней недели на русский
            day_names_ru = {
                'Monday': 'Понедельник',
                'Tuesday': 'Вторник',
                'Wednesday': 'Среда',
                'Thursday': 'Четверг',
                'Friday': 'Пятница',
                'Saturday': 'Суббота',
                'Sunday': 'Воскресенье'
            }
            day_name_ru = day_names_ru.get(day_name, day_name)
        except:
            date_str = event_date
            day_name_ru = ""
        
        # Добавляем дату как заголовок секции
        table_data.append([
            f"<b>{date_str}</b> {day_name_ru}" if day_name_ru else f"<b>{date_str}</b>",
            "",
            "",
            "",
            ""
        ])
        
        # Добавляем события
        for event in date_events:
            title_event = event.get('title', '')
            category = event.get('category', '')
            location = event.get('location_custom') or event.get('location_type', '')
            
            # Форматируем время
            try:
                time_str = date_obj.strftime("%H:%M")
            except:
                time_str = ""
            
            table_data.append([
                "",
                time_str,
                title_event,
                category,
                location
            ])
        
        # Пустая строка между датами
        table_data.append(["", "", "", "", ""])
    
    # Создаём таблицу
    table = Table(table_data, colWidths=[3.5*cm, 2*cm, 7*cm, 3*cm, 4*cm])
    
    # Стили таблицы
    table.setStyle(TableStyle([
        # Заголовок
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Чередование цветов строк
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ECF0F1'), colors.white]),
        
        # Границы
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # Отступы
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        
        # Выделение заголовков дат
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#2ECC71')),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
    ]))
    
    elements.append(table)
    
    # Генерируем PDF
    doc.build(elements)
    
    # Получаем PDF как байты
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


def create_pdf_summary(events: List[Dict], days: int = 30) -> bytes:
    """
    Создать PDF с краткой сводкой событий.
    
    Args:
        events: Список событий
        days: Количество дней для сводки
    
    Returns:
        bytes: PDF файл
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Заголовок
    title = Paragraph(f"События на ближайшие {days} дней", styles['Heading1'])
    elements.append(title)
    elements.append(Spacer(1, 1*cm))
    
    # Статистика
    total_events = len(events)
    categories = {}
    for event in events:
        cat = event.get('category', 'Другое')
        categories[cat] = categories.get(cat, 0) + 1
    
    elements.append(Paragraph(f"<b>Всего событий:</b> {total_events}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    elements.append(Paragraph("<b>По категориям:</b>", styles['Normal']))
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        elements.append(Paragraph(f"• {cat}: {count}", styles['Normal']))
    
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
