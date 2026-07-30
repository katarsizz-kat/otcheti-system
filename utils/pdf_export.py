"""Модуль для экспорта календаря в PDF."""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import io
import calendar
import os


def get_cyrillic_font():
    """Получить шрифт с поддержкой кириллицы."""
    # Пробуем найти шрифты с поддержкой кириллицы
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/TTF/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
        '/usr/local/share/fonts/DejaVuSans.ttf',
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font_name = os.path.basename(font_path).replace('.ttf', '')
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                return font_name, font_name
            except Exception as e:
                print(f"Font error {font_path}: {e}")
                continue
    
    # Fallback на стандартные шрифты (кириллица может не работать)
    return 'Helvetica', 'Helvetica'


def create_month_calendar(events: List[Dict], year: int, month: int, 
                         font_name: str, font_name_bold: str) -> list:
    """Создать календарную сетку для одного месяца."""
    cal = calendar.monthcalendar(year, month)
    month_names = [
        '', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    
    # Группируем события по дням
    events_by_day = {}
    for event in events:
        try:
            event_date = datetime.fromisoformat(str(event['start_date']).replace('Z', '+00:00')).date()
            if event_date.year == year and event_date.month == month:
                day = event_date.day
                if day not in events_by_day:
                    events_by_day[day] = []
                events_by_day[day].append(event)
        except:
            pass
    
    # Создаем таблицу
    table_data = []
    
    # Заголовок месяца
    table_data.append([
        Paragraph(f"<b>{month_names[month]} {year}</b>", 
                 style=ParagraphStyle('MonthTitle', fontName=font_name_bold, fontSize=16, alignment=1))
    ] * 7)
    
    # Дни недели
    table_data.append([
        Paragraph(f"<b>{day}</b>", 
                 style=ParagraphStyle('Weekday', fontName=font_name_bold, fontSize=10, alignment=1))
        for day in weekdays
    ])
    
    # Дни месяца
    for week in cal:
        week_row = []
        for day in week:
            if day == 0:
                week_row.append("")
            else:
                events_text = ""
                if day in events_by_day:
                    for event in events_by_day[day][:3]:
                        title = event.get('title', '')[:25]
                        events_text += f"• {title}\n"
                    if len(events_by_day[day]) > 3:
                        events_text += f"... ещё {len(events_by_day[day]) - 3}"
                
                cell_text = f"<b>{day}</b>\n{events_text}"
                week_row.append(Paragraph(cell_text, 
                    style=ParagraphStyle('DayCell', fontName=font_name, fontSize=9, alignment=0, leading=10)))
        table_data.append(week_row)
    
    return table_data


def create_pdf_calendar(events: List[Dict], title: str = "Календарь событий", 
                       months_ahead: int = 3) -> bytes:
    """
    Создать PDF файл с календарём по месяцам.
    
    Args:
        events: Список событий
        title: Заголовок документа
        months_ahead: Количество месяцев вперёд для экспорта (по умолчанию 3)
    """
    buffer = io.BytesIO()
    
    font_name, font_name_bold = get_cyrillic_font()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1.5*cm,
        bottomMargin=1*cm
    )
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('CustomTitle', fontName=font_name_bold, fontSize=20, alignment=1, spaceAfter=20))
    styles.add(ParagraphStyle('CustomSubtitle', fontName=font_name, fontSize=10, alignment=1, spaceAfter=10))
    
    elements = []
    
    elements.append(Paragraph(title, styles['CustomTitle']))
    generated_date = datetime.now().strftime("%d.%m.%Y %H:%M")
    elements.append(Paragraph(f"Сгенерировано: {generated_date}", styles['CustomSubtitle']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Определяем диапазон месяцев
    today = date.today()
    end_date = today + timedelta(days=30 * months_ahead)
    
    if not events:
        months_to_show = [(today.year, today.month)]
    else:
        months_set = set()
        for event in events:
            try:
                event_date = datetime.fromisoformat(str(event['start_date']).replace('Z', '+00:00')).date()
                if today <= event_date <= end_date:
                    months_set.add((event_date.year, event_date.month))
            except:
                pass
        
        if not months_set:
            months_to_show = [(today.year, today.month)]
        else:
            months_to_show = sorted(months_set)
    
    # Создаём календарь для каждого месяца
    for idx, (year, month) in enumerate(months_to_show):
        month_events = [e for e in events if 
                       datetime.fromisoformat(str(e['start_date']).replace('Z', '+00:00')).year == year and
                       datetime.fromisoformat(str(e['start_date']).replace('Z', '+00:00')).month == month]
        
        table_data = create_month_calendar(month_events, year, month, font_name, font_name_bold)
        
        table = Table(table_data, colWidths=[4.2*cm] * 7)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 16),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#2ECC71')),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.white),
            ('FONTNAME', (0, 1), (-1, 1), font_name_bold),
            ('FONTSIZE', (0, 1), (-1, 1), 10),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        elements.append(table)
        
        if idx < len(months_to_show) - 1:
            elements.append(PageBreak())
    
    try:
        doc.build(elements)
    except Exception as e:
        print(f"Error building PDF: {e}")
        doc.build(elements, canvasmaker=None)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
