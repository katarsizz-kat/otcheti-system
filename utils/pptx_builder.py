import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml import parse_xml
from config.brand import PJColors, PJFonts, PJSlogans

# ==========================================
# 🛠️ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================
def _set_slide_bg(slide, color):
    """Устанавливает цвет фона слайда."""
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color

def _add_text(slide, left, top, width, height, text, font_name, font_size, color, bold=False, align=PP_ALIGN.LEFT):
    """Добавляет текстовый блок с соблюдением правил типографики."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.name = font_name
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.alignment = align
    return txBox

def _format_cell(cell, text, font_name, font_size, font_color, bg_color=None, bold=False, align=PP_ALIGN.CENTER):
    """Форматирует ячейку таблицы. Убираем лишний визуальный шум (границы)."""
    cell.text = str(text)
    for paragraph in cell.text_frame.paragraphs:
        paragraph.font.name = font_name
        paragraph.font.size = Pt(font_size)
        paragraph.font.color.rgb = font_color
        paragraph.font.bold = bold
        paragraph.alignment = align
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    
    if bg_color:
        cell.fill.solid()
        cell.fill.fore_color.rgb = bg_color

    # Скрываем границы таблицы (требование брендбука: чистота композиции)
    tcPr = cell._tc.get_or_add_tcPr()
    for border in ['a:lnL', 'a:lnR', 'a:lnT', 'a:lnB']:
        ln = parse_xml(f'<{border} w="0" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:noFill/></{border}>')
        tcPr.append(ln)

# ==========================================
# 🍕 ГЛАВНАЯ ФУНКЦИЯ ГЕНЕРАЦИИ
# ==========================================
def generate_kr_presentation(df_ratings, df_reviews, period_text, output_path="КР_Презентация.pptx"):
    """
    Генерирует презентацию Клиентского Рейтинга строго по брендбуку Папа Джонс.
    """
    prs = Presentation()
    # Стандартный широкий формат 16:9
    prs.slide.width = Inches(13.333)
    prs.slide.height = Inches(7.5)

    # --- СЛАЙД 1: ТИТУЛЬНЫЙ ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, PJColors.TOMATO_RED)

    _add_text(slide, Inches(1), Inches(1.5), Inches(11), Inches(1.5),
              "КЛИЕНТСКИЙ РЕЙТИНГ", PJFonts.HEADLINE, 64, PJColors.WHITE, bold=True, align=PP_ALIGN.CENTER)
    
    _add_text(slide, Inches(1), Inches(3.2), Inches(11), Inches(1),
              period_text, PJFonts.BODY, 36, PJColors.CHEESE_YELLOW, align=PP_ALIGN.CENTER)
    
    _add_text(slide, Inches(1), Inches(5.5), Inches(11), Inches(1),
              PJSlogans.EMOTION, PJFonts.BODY, 28, PJColors.WHITE, align=PP_ALIGN.CENTER)

    # --- СЛАЙД 2: ОЦЕНКИ (Сайт, Агрегаторы, Геосервисы) ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, PJColors.WHITE)

    _add_text(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.8),
              "СРЕДНИЕ ОЦЕНКИ", PJFonts.HEADLINE, 44, PJColors.BASIL_GREEN, bold=True)
    
    _add_text(slide, Inches(0.5), Inches(1.1), Inches(12), Inches(0.5),
              "Делаем каждый момент особенным!", PJFonts.BODY, 24, PJColors.OLIVE_GREEN)

    # Таблица оценок (Адаптируй под реальные данные из df_ratings)
    rows, cols = 5, 4 
    table_shape = slide.shapes.add_table(rows, cols, Inches(1.5), Inches(2), Inches(10), Inches(4))
    table = table_shape.table

    headers = ["Город / Метрика", "Сайт", "Агрегаторы", "Геосервисы"]
    for i, h in enumerate(headers):
        _format_cell(table.cell(0, i), h, PJFonts.HEADLINE, 20, PJColors.WHITE, PJColors.OLIVE_GREEN, bold=True)

    # ⚠️ ЗАГЛУШКА: Подставь сюда реальные данные из df_ratings
    data = [
        ["Санкт-Петербург", "4.8", "4.7", "4.9"],
        ["Тюмень", "4.9", "4.8", "4.8"],
        ["Общий средний", "4.85", "4.75", "4.85"],
        ["Цель на месяц", "4.9", "4.9", "4.9"]
    ]

    for r_idx, row_data in enumerate(data):
        bg = PJColors.DOUGH_BEIGE if r_idx % 2 == 0 else PJColors.WHITE
        for c_idx, val in enumerate(row_data):
            is_bold = (r_idx == 2) # Выделяем итог
            _format_cell(table.cell(r_idx + 1, c_idx), val, PJFonts.BODY, 18, PJColors.BLACK, bg, bold=is_bold)

    # --- СЛАЙД 3: АНАЛИЗ ОТЗЫВОВ (Жалобы) ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, PJColors.WHITE)

    _add_text(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.8),
              "АНАЛИЗ ОТЗЫВОВ", PJFonts.HEADLINE, 44, PJColors.TOMATO_RED, bold=True)
    
    _add_text(slide, Inches(0.5), Inches(1.1), Inches(12), Inches(0.5),
              PJSlogans.TRANSPARENCY, PJFonts.BODY, 24, PJColors.OLIVE_GREEN)

    rows, cols = 6, 3
    table_shape = slide.shapes.add_table(rows, cols, Inches(2.5), Inches(2), Inches(8), Inches(4))
    table = table_shape.table

    headers = ["Категория", "Санкт-Петербург", "Тюмень"]
    for i, h in enumerate(headers):
        _format_cell(table.cell(0, i), h, PJFonts.HEADLINE, 20, PJColors.WHITE, PJColors.TOMATO_RED, bold=True)

    complaints = ["Продукт", "Приготовление", "Перепутали", "Сервис", "Опоздание"]
    
    # ⚠️ ЗАГЛУШКА: Подставь сюда реальные данные из df_reviews
    spb_data = ["2", "1", "0", "3", "1"] 
    tym_data = ["1", "0", "1", "1", "0"]

    for r_idx, cat in enumerate(complaints):
        bg = PJColors.DOUGH_BEIGE if r_idx % 2 == 0 else PJColors.WHITE
        _format_cell(table.cell(r_idx + 1, 0), cat, PJFonts.BODY, 18, PJColors.BLACK, bg, bold=True, align=PP_ALIGN.LEFT)
        _format_cell(table.cell(r_idx + 1, 1), spb_data[r_idx], PJFonts.BODY, 18, PJColors.BLACK, bg)
        _format_cell(table.cell(r_idx + 1, 2), tym_data[r_idx], PJFonts.BODY, 18, PJColors.BLACK, bg)

    # --- СЛАЙД 4: ФИНАЛЬНЫЙ ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, PJColors.BASIL_GREEN)

    _add_text(slide, Inches(1), Inches(2.5), Inches(11), Inches(1.5),
              PJSlogans.MAIN, PJFonts.HEADLINE, 54, PJColors.WHITE, bold=True, align=PP_ALIGN.CENTER)
    
    _add_text(slide, Inches(1), Inches(4.5), Inches(11), Inches(1),
              PJSlogans.CARE, PJFonts.BODY, 28, PJColors.CHEESE_YELLOW, align=PP_ALIGN.CENTER)

    prs.save(output_path)
    return output_path
