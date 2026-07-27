from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml import parse_xml
import pandas as pd
from typing import Dict, List

# ==========================================
# 🎨 ФИРМЕННЫЕ ЦВЕТА (из Брендбука)
# ==========================================
class PJColors:
    TOMATO_RED = RGBColor(225, 45, 38)
    BASIL_GREEN = RGBColor(3, 89, 45)
    OLIVE_GREEN = RGBColor(17, 72, 52)
    CHEESE_YELLOW = RGBColor(255, 225, 33)
    DOUGH_BEIGE = RGBColor(244, 232, 220)
    BAKED_RED = RGBColor(127, 22, 31)
    WHITE = RGBColor(255, 255, 255)
    BLACK = RGBColor(0, 0, 0)

class PJFonts:
    HEADLINE = "Oswald"
    BODY = "Roboto Condensed"

class PJSlogans:
    MAIN = "Лучшие ингредиенты. Лучшая пицца."
    EMOTION = "Когда есть вкус, есть эмоции."
    TRANSPARENCY = "Мы открыты, честны и уверены в своем продукте."
    CARE = "Дарить людям хорошее настроение через еду и сервис."

# ==========================================
# 🛠️ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================
def _set_slide_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color

def _add_text(slide, left, top, width, height, text, font_name, font_size, color, bold=False, align=PP_ALIGN.LEFT):
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

    # Убираем границы таблицы
    tcPr = cell._tc.get_or_add_tcPr()
    for border in ['a:lnL', 'a:lnR', 'a:lnT', 'a:lnB']:
        ln = parse_xml(f'<{border} w="0" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:noFill/></{border}>')
        tcPr.append(ln)

# ==========================================
# 🍕 ГЛАВНАЯ ФУНКЦИЯ ГЕНЕРАЦИИ
# ==========================================
def generate_flexible_presentation(
    all_dataframes: Dict[str, Dict[str, pd.DataFrame]], 
    slides_structure: List[str],
    period_text: str,
    theme: str = "Классическая (Томат + Базилик)",
    output_path: str = "Гибкая_презентация.pptx"
):
    """
    Генерирует презентацию с гибкой структурой на основе загруженных файлов.
    """
    prs = Presentation()
    # ✅ ИСПРАВЛЕНИЕ: задаем размеры слайда напрямую
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # Выбираем цвета темы
    if "Оливковая" in theme:
        primary_color = PJColors.OLIVE_GREEN
        secondary_color = PJColors.BASIL_GREEN
    elif "Сырная" in theme:
        primary_color = PJColors.CHEESE_YELLOW
        secondary_color = PJColors.TOMATO_RED
    else:
        primary_color = PJColors.TOMATO_RED
        secondary_color = PJColors.BASIL_GREEN
    
    # --- СЛАЙД 1: ТИТУЛЬНЫЙ ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, primary_color)
    
    _add_text(slide, Inches(1), Inches(1.5), Inches(11), Inches(1.5),
              "КЛИЕНТСКИЙ РЕЙТИНГ", PJFonts.HEADLINE, 64, PJColors.WHITE, bold=True, align=PP_ALIGN.CENTER)
    
    _add_text(slide, Inches(1), Inches(3.2), Inches(11), Inches(1),
              period_text, PJFonts.BODY, 36, PJColors.CHEESE_YELLOW, align=PP_ALIGN.CENTER)
    
    _add_text(slide, Inches(1), Inches(5.5), Inches(11), Inches(1),
              PJSlogans.EMOTION, PJFonts.BODY, 28, PJColors.WHITE, align=PP_ALIGN.CENTER)
    
    # --- ГЕНЕРАЦИЯ СЛАЙДОВ ПО СТРУКТУРЕ ---
    file_list = list(all_dataframes.keys())
    
    for slide_idx, slide_title in enumerate(slides_structure):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _set_slide_bg(slide, PJColors.WHITE)
        
        # Заголовок слайда
        _add_text(slide, Inches(0.5), Inches(0.3), Inches(12), Inches(0.8),
                  slide_title, PJFonts.HEADLINE, 40, secondary_color, bold=True)
        
        # Определяем тип слайда по ключевым словам
        slide_lower = slide_title.lower()
        
        if "общ" in slide_lower or "показател" in slide_lower or "сеть" in slide_lower:
            # Общий слайд — показываем сводку по всем файлам
            rows = len(file_list) + 1
            cols = 3
            table_shape = slide.shapes.add_table(rows, cols, Inches(1), Inches(1.5), Inches(11), Inches(4))
            table = table_shape.table
            
            _format_cell(table.cell(0, 0), "Файл", PJFonts.HEADLINE, 18, PJColors.WHITE, secondary_color, bold=True)
            _format_cell(table.cell(0, 1), "Листов", PJFonts.BODY, 18, PJColors.WHITE, secondary_color, bold=True)
            _format_cell(table.cell(0, 2), "Строк данных", PJFonts.BODY, 18, PJColors.WHITE, secondary_color, bold=True)
            
            for idx, filename in enumerate(file_list):
                sheets = all_dataframes[filename]
                total_rows = sum(len(df) for df in sheets.values())
                
                _format_cell(table.cell(idx + 1, 0), filename, PJFonts.BODY, 16, PJColors.BLACK, 
                           PJColors.DOUGH_BEIGE if idx % 2 == 0 else PJColors.WHITE)
                _format_cell(table.cell(idx + 1, 1), str(len(sheets)), PJFonts.BODY, 16, PJColors.BLACK,
                           PJColors.DOUGH_BEIGE if idx % 2 == 0 else PJColors.WHITE)
                _format_cell(table.cell(idx + 1, 2), str(total_rows), PJFonts.BODY, 16, PJColors.BLACK,
                           PJColors.DOUGH_BEIGE if idx % 2 == 0 else PJColors.WHITE)
        
        else:
            # Стандартный слайд — показываем данные из первого файла
            if file_list:
                first_file = file_list[0]
                first_sheet_name = list(all_dataframes[first_file].keys())[0]
                df = all_dataframes[first_file][first_sheet_name]
                
                # Показываем первые 10 строк
                rows = min(len(df.head(10)) + 1, 11)
                cols = len(df.columns)
                
                if cols > 0 and rows > 1:
                    table_shape = slide.shapes.add_table(rows, cols, Inches(0.5), Inches(1.5), 
                                                        Inches(12), Inches(4.5))
                    table = table_shape.table
                    
                    # Заголовки колонок
                    for col_idx, col_name in enumerate(df.columns):
                        _format_cell(table.cell(0, col_idx), str(col_name), 
                                   PJFonts.HEADLINE, 14, PJColors.WHITE, secondary_color, bold=True)
                    
                    # Данные
                    for row_idx, row in df.head(10).iterrows():
                        bg = PJColors.DOUGH_BEIGE if row_idx % 2 == 0 else PJColors.WHITE
                        for col_idx, value in enumerate(row):
                            _format_cell(table.cell(row_idx + 1, col_idx), str(value),
                                       PJFonts.BODY, 12, PJColors.BLACK, bg)
        
        # Номер слайда
        _add_text(slide, Inches(12), Inches(7), Inches(1), Inches(0.5),
                  f"{slide_idx + 2}/{len(slides_structure) + 1}", 
                  PJFonts.BODY, 12, PJColors.OLIVE_GREEN)
    
    # --- ФИНАЛЬНЫЙ СЛАЙД ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_bg(slide, secondary_color)
    
    _add_text(slide, Inches(1), Inches(2.5), Inches(11), Inches(1.5),
              PJSlogans.MAIN, PJFonts.HEADLINE, 54, PJColors.WHITE, bold=True, align=PP_ALIGN.CENTER)
    
    _add_text(slide, Inches(1), Inches(4.5), Inches(11), Inches(1),
              PJSlogans.CARE, PJFonts.BODY, 28, PJColors.CHEESE_YELLOW, align=PP_ALIGN.CENTER)
    
    prs.save(output_path)
    return output_path
