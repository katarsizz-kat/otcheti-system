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
import os


def get_cyrillic_font():
    """Получить шрифт с поддержкой кириллицы."""
    # Пробуем зарегистрировать шрифты с поддержкой кириллицы
    try:
        # Пытаемся зарегистрировать DejaVu Sans (обычно есть в системе)
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/TTF/DejaVuSans.ttf',
            'DejaVuSans.ttf',
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', font_path.replace('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf')))
                    return 'DejaVuSans', 'DejaVuSans-Bold'
                except:
                    continue
        
        # Если DejaVu не найден, пробуем другие шрифты
        alternative_fonts = [
            'Arial',
            'Times New Roman',
            'LiberationSans',
        ]
        
        for font_name in alternative_fonts:
            try:
                pdfmetrics.registerFont(TTFont(font_name, f'{font_name}.ttf'))
                return font_name, f'{font_name}-Bold'
            except:
                continue
                
    except Exception as e:
        print(f"Warning: Could not register custom fonts: {e}")
    
    # Если ничего не помогло, используем стандартный шрифт
    # (но кириллица может не отображаться)
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
    
    # Получаем шрифты
    font_name, font_name_bold = get_cyrillic_font()
    
    # Стили
    styles = getSampleStyleSheet()
    
    # Создаём стили с поддержкой кириллицы
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        alignment=1,  # Центр
        textColor=colors.HexColor('#2C3E50'),
        fontName=font_name_bold
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10
    )
    
    # Элементы документа
    elements = []
    
    # Заголовок
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Информация о генерации
    generated_date = datetime.now().strftime("%d.%m.%Y %H:%M")
    elements.append(Paragraph(f"<i>Сгенерировано: {generated_date}</i>", normal_style))
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
        header_text = f"<b>{date_str}</b>"
        if day_name_ru:
            header_text += f" {day_name_ru}"
        
        table_data.append([
            header_text,
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
        ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
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
        ('FONTNAME', (0, 1), (-1, 1), font_name_bold),
    ]))
    
    elements.append(table)
    
    # Генерируем PDF
    try:
        doc.build(elements)
    except Exception as e:
        print(f"Error building PDF: {e}")
        # Пытаемся построить с базовыми стилями
        doc.build(elements, canvasmaker=None)
    
    # Получаем PDF как байты
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
