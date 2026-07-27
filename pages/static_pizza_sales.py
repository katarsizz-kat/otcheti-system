# pages/static_pizza_sales.py
import streamlit as st
import pandas as pd
import numpy as np
import re
import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Продажи пицц по размерам", layout="wide", page_icon="🍕")

# ==========================================================
# ДИНАМИЧЕСКИЕ СТИЛИ (НЕБО ПО ВРЕМЕНИ СУТОК)
# ==========================================================

def get_sky_gradient():
    """Возвращает градиент неба в зависимости от времени суток."""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:  # Утро - восход
        return {
            "header": "linear-gradient(135deg, #FF8C42 0%, #5DADE2 100%)",
            "block": "linear-gradient(135deg, #FFF5EB 0%, #EBF5FB 100%)",
            "text": "#FFFFFF",
            "button_text": "#FFFFFF",
            "button_bg": "#FF6B35"
        }
    elif 12 <= hour < 18:  # День - ясное небо
        return {
            "header": "linear-gradient(135deg, #3498DB 0%, #EBF5FB 100%)",
            "block": "linear-gradient(135deg, #EBF5FB 0%, #FFFFFF 100%)",
            "text": "#FFFFFF",
            "button_text": "#FFFFFF",
            "button_bg": "#2E86C1"
        }
    elif 18 <= hour < 23:  # Вечер - закат
        return {
            "header": "linear-gradient(135deg, #2874A6 0%, #F39C12 100%)",
            "block": "linear-gradient(135deg, #FDEBD0 0%, #D4E6F1 100%)",
            "text": "#FFFFFF",
            "button_text": "#FFFFFF",
            "button_bg": "#D68910"
        }
    else:  # Ночь
        return {
            "header": "linear-gradient(135deg, #1B4F72 0%, #5DADE2 100%)",
            "block": "linear-gradient(135deg, #D6EAF8 0%, #FFFFFF 100%)",
            "text": "#FFFFFF",
            "button_text": "#1B4F72",
            "button_bg": "#2E86C1"
        }

def apply_dynamic_styles():
    """Применяет динамические стили."""
    sky = get_sky_gradient()
    
    st.markdown(f"""
    <style>
        .stApp {{
            background: {sky['block']} !important;
        }}
        .header-block {{
            background: {sky['header']};
            padding: 24px;
            border-radius: 16px;
            margin-bottom: 24px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.15);
            border: 2px solid rgba(255,255,255,0.3);
        }}
        .header-block h1 {{
            margin: 0;
            color: {sky['text']};
            font-size: 36px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        .header-block p {{
            margin-top: 8px;
            margin-bottom: 0;
            font-size: 18px;
            color: {sky['text']};
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        }}
        .content-block {{
            background: rgba(255, 255, 255, 0.95);
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border: 1px solid #D6EAF8;
        }}
        .stButton>button {{
            background: {sky['button_bg']} !important;
            color: {sky['button_text']} !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: bold !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
            transition: all 0.3s ease !important;
        }}
        .stButton>button:hover {{
            filter: brightness(1.1) !important;
            transform: translateY(-2px) !important;
        }}
        hr {{
            border: none;
            border-top: 2px solid #D6EAF8;
            margin: 24px 0;
        }}
    </style>
    """, unsafe_allow_html=True)

def apply_file_uploader_styles():
    """Применяет стили для блоков загрузки файлов."""
    st.markdown("""
    <style>
        .element-container:has(> .stFileUploader) {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border: 2px solid transparent;
            transition: all 0.3s ease;
        }
        .element-container:has(> .stFileUploader):hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        }
        .stFileUploader [data-testid="stFileUploader"] {
            background: white;
            border-radius: 8px;
            padding: 10px;
        }
        .stFileUploader label {
            font-weight: bold;
            color: #2C3E50;
        }
        .stFileUploader > div > div {
            border: 2px dashed rgba(0,0,0,0.2) !important;
            border-radius: 8px !important;
            background: rgba(255,255,255,0.8) !important;
            transition: all 0.3s ease !important;
        }
        .stFileUploader > div > div:hover {
            border-color: #3498DB !important;
            background: rgba(255,255,255,1) !important;
        }
        .stFileUploader small {
            color: #7F8C8D;
            font-size: 12px;
        }
    </style>
    """, unsafe_allow_html=True)

def greeting_by_time():
    hour = datetime.now().hour
    if 5 <= hour < 12: return "☀️ Доброе утро!"
    if 12 <= hour < 18: return "🌤 Добрый день!"
    if 18 <= hour < 23: return " Добрый вечер!"
    return "🌙 Доброй ночи!"

# ==========================================================
# СТАТИЧНЫЙ СПИСОК ПИЦЦ (из примера)
# ==========================================================

STATIC_PIZZA_LIST = [
    # Рейтинг 6
    (6, "Большая Бонанза"),
    (6, "6 сыров"),
    (6, "8 сыров"),
    (6, "Любимая папина пицца"),
    # Рейтинг 5
    (5, "Мясная"),
    (5, "4 сыра"),
    (5, "Итальянская с моцареллой и пепперони"),
    (5, "Маленькая Италия"),
    (5, "Баварская"),
    (5, "Папа Микс"),
    (5, "Цыпленок Рэнч"),
    (5, "Альфредо"),
    (5, "Мексиканская"),
    (5, "Супер Папа"),
    (5, "Цыпленок Барбекю"),
    # Рейтинг 4
    (4, "Чизбургер"),
    (4, "Цыплёнок Флорентина"),
    (4, "Мясное барбекю"),
    (4, "Гавайская"),
    (4, "Двойная пепперони"),
    # Рейтинг 3
    (3, "Пепперони"),
    (3, "Ветчина и Грибы"),
    (3, "Чикен Пармеджано"),
    # Рейтинг 2
    (2, "Вегетарианская"),
    (2, "Маргарита"),
    (2, "Капричиоза"),
    (2, "Цыплёнок Грин"),
    # Рейтинг 1
    (1, "Сырная Пицца"),
]

# ==========================================================
# ФУНКЦИИ ПАРСИНГА
# ==========================================================

def normalize_text(text):
    """Нормализует текст для сравнения."""
    if not isinstance(text, str): 
        return ""
    replacements = {
        'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с', 'y': 'у', 'x': 'х',
        'A': 'А', 'E': 'Е', 'O': 'О', 'P': 'Р', 'C': 'С', 'Y': 'У', 'X': 'Х',
        'ё': 'е', 'Ё': 'Е'
    }
    for lat, cyr in replacements.items():
        text = text.replace(lat, cyr)
    text = text.lower().replace('"', '')
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'^пицца\s*', '', text)
    text = re.sub(r'\bпромо\b', '', text)
    text = re.sub(r'\bподарок\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def map_city(legal_entity):
    """Определяет город по юридическому лицу."""
    le = str(legal_entity)
    if 'СПБ' in le:
        return 'СПБ'
    elif 'ПД' in le and 'СПБ' not in le:
        return 'Тюмень'
    return None

def extract_size_from_category(category):
    """Извлекает размер из категории (например, 'Тесто 23 трад' -> 23)."""
    category_str = str(category).lower()
    for size in [40, 35, 30, 23, 15]:
        if str(size) in category_str:
            return size
    return None

def extract_period_from_file(uploaded_file):
    """Извлекает период из файла (например, '01.07.2026-31.07.2026')."""
    df = pd.read_excel(uploaded_file, header=None, nrows=10)
    
    for idx, row in df.iterrows():
        for val in row.values:
            if pd.notna(val) and 'Период' in str(val):
                # Ищем даты в строке
                match = re.search(r'(\d{2}\.\d{2}\.\d{4})\s+по\s+(\d{2}\.\d{2}\.\d{4})', str(val))
                if match:
                    start_date = match.group(1)
                    end_date = match.group(2)
                    # Преобразуем формат
                    start_dt = datetime.strptime(start_date, '%d.%m.%Y')
                    end_dt = datetime.strptime(end_date, '%d.%m.%Y')
                    return f"{start_dt.strftime('%d.%m')}-{end_dt.strftime('%d.%m.%Y')}"
    
    # Если не нашли период, возвращаем текущий месяц
    now = datetime.now()
    return f"01.{now.strftime('%m')}.{now.year}"

def read_and_parse_file(uploaded_file):
    """Читает и парсит основной файл."""
    df = pd.read_excel(uploaded_file, header=None)
    
    # Находим строку заголовков
    header_row = None
    for idx, row in df.iterrows():
        vals = [str(v) for v in row.values if pd.notna(v)]
        if 'Юридическое лицо' in ' '.join(vals) and 'Блюдо' in ' '.join(vals):
            header_row = idx
            break
    
    if header_row is None:
        raise ValueError("Не найдена строка заголовков в файле!")
    
    headers = df.iloc[header_row].values
    df = df[header_row + 1:].copy()
    df.columns = headers
    df = df.reset_index(drop=True)
    
    # Удаляем служебные строки
    df = df[~df['Юридическое лицо'].astype(str).str.contains('OLAP|всего|Итого', na=False)]
    df = df.dropna(how='all')
    
    # Заполняем пропущенные значения
    df['Юридическое лицо'] = df['Юридическое лицо'].ffill()
    df['Категория блюда'] = df['Категория блюда'].ffill()
    
    # Удаляем половинки и персонал
    df = df[~df['Блюдо'].astype(str).str.contains('\+', na=False)]
    df = df[~df['Блюдо'].astype(str).str.lower().str.contains('персонал', na=False)]
    df = df[df['Блюдо'].notna()]
    df = df[df['Блюдо'].astype(str).str.strip() != '']
    
    # Конвертируем числовые колонки
    df['Количество блюд'] = pd.to_numeric(df['Количество блюд'], errors='coerce').fillna(0)
    
    return df

def aggregate_pizza_data(df):
    """Агрегирует данные по пиццам для каждого города и размера."""
    df = df.copy()
    df['Город'] = df['Юридическое лицо'].apply(map_city)
    df = df[df['Город'].notna()]
    
    # Фильтруем только пиццы (категории с тестом)
    df['Категория_lower'] = df['Категория блюда'].astype(str).str.lower()
    df_pizza = df[df['Категория_lower'].str.contains('тесто', na=False)].copy()
    
    # Извлекаем размер
    df_pizza['Размер'] = df_pizza['Категория блюда'].apply(extract_size_from_category)
    df_pizza = df_pizza[df_pizza['Размер'].isin([23, 30, 35, 40])]
    
    # Нормализуем названия пицц
    df_pizza['Блюдо_norm'] = df_pizza['Блюдо'].apply(normalize_text)
    
    # Создаем словарь с данными для каждого города
    result = {}
    for city in ['СПБ', 'Тюмень']:
        city_data = df_pizza[df_pizza['Город'] == city]
        
        # Создаем таблицу: пицца x размер
        pizza_data = {}
        for rating, pizza_name in STATIC_PIZZA_LIST:
            pizza_norm = normalize_text(pizza_name)
            sizes = {23: 0, 30: 0, 35: 0, 40: 0}
            
            # Ищем эту пиццу в данных
            for _, row in city_data.iterrows():
                if row['Блюдо_norm'] == pizza_norm or pizza_norm in row['Блюдо_norm']:
                    size = row['Размер']
                    if size in sizes:
                        sizes[size] += int(row['Количество блюд'])
            
            pizza_data[pizza_name] = {
                'rating': rating,
                'sizes': sizes,
                'total': sum(sizes.values())
            }
        
        result[city] = pizza_data
    
    return result

# ==========================================================
# СОЗДАНИЕ EXCEL
# ==========================================================

def create_excel_report(data, period_str):
    """Создает Excel файл с отчетом."""
    wb = Workbook()
    if 'Sheet' in wb.sheetnames:
        del wb['Sheet']
    
    ws = wb.create_sheet("Продажи по размерам")
    
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Строка 1: Период (желтый фон)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=13)
    header_cell = ws.cell(1, 1, period_str)
    header_cell.font = Font(bold=True, size=16)
    header_cell.alignment = Alignment(horizontal='center', vertical='center')
    header_cell.fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
    
    # Строка 2: Города (голубой фон)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=6)
    spb_header = ws.cell(2, 1, "СПб сейчас")
    spb_header.font = Font(bold=True, size=12)
    spb_header.alignment = Alignment(horizontal='center', vertical='center')
    spb_header.fill = PatternFill(start_color='00BFFF', end_color='00BFFF', fill_type='solid')
    
    ws.merge_cells(start_row=2, start_column=8, end_row=2, end_column=13)
    tmn_header = ws.cell(2, 8, "Тюмень сейчас")
    tmn_header.font = Font(bold=True, size=12)
    tmn_header.alignment = Alignment(horizontal='center', vertical='center')
    tmn_header.fill = PatternFill(start_color='00BFFF', end_color='00BFFF', fill_type='solid')
    
    # Строка 3: Заголовки колонок с размерами
    # СПБ: колонки 1-6 (рейтинг, название, 23, 30, 35, 40)
    # Тюмень: колонки 8-13 (рейтинг, название, 23, 30, 35, 40)
    
    headers_spb = ['', '', '23', '30', '35', '40']
    headers_tmn = ['', '', '23', '30', '35', '40']
    
    for col_idx, header in enumerate(headers_spb, 1):
        cell = ws.cell(3, col_idx, header)
        cell.font = Font(bold=True, size=10)
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    for col_idx, header in enumerate(headers_tmn, 8):
        cell = ws.cell(3, col_idx, header)
        cell.font = Font(bold=True, size=10)
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Заполняем данными
    current_row = 4
    current_rating = None
    
    for rating, pizza_name in STATIC_PIZZA_LIST:
        # Добавляем пустую строку между рейтингами
        if current_rating is not None and current_rating != rating:
            current_row += 1
        
        current_rating = rating
        
        # СПБ: колонки 1-6
        ws.cell(current_row, 1, rating).border = thin_border
        ws.cell(current_row, 1).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(current_row, 2, pizza_name).border = thin_border
        
        spb_data = data['СПБ'][pizza_name]['sizes']
        for col_idx, size in enumerate([23, 30, 35, 40], 3):
            cell = ws.cell(current_row, col_idx, spb_data[size])
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Тюмень: колонки 8-13
        ws.cell(current_row, 8, rating).border = thin_border
        ws.cell(current_row, 8).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(current_row, 9, pizza_name).border = thin_border
        
        tmn_data = data['Тюмень'][pizza_name]['sizes']
        for col_idx, size in enumerate([23, 30, 35, 40], 10):
            cell = ws.cell(current_row, col_idx, tmn_data[size])
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        current_row += 1
    
    # Итоговая строка с суммами
    total_row = current_row + 1
    
    # СПБ ИТОГО
    ws.cell(total_row, 2, 'ИТОГО').font = Font(bold=True, size=11)
    ws.cell(total_row, 2).border = thin_border
    
    for col_idx, size in enumerate([23, 30, 35, 40], 3):
        size_col = get_column_letter(col_idx)
        formula = f"=SUM({size_col}4:{size_col}{total_row-1})"
        cell = ws.cell(total_row, col_idx, formula)
        cell.font = Font(bold=True, size=11)
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Тюмень ИТОГО
    ws.cell(total_row, 9, 'ИТОГО').font = Font(bold=True, size=11)
    ws.cell(total_row, 9).border = thin_border
    
    for col_idx, size in enumerate([23, 30, 35, 40], 10):
        size_col = get_column_letter(col_idx)
        formula = f"=SUM({size_col}4:{size_col}{total_row-1})"
        cell = ws.cell(total_row, col_idx, formula)
        cell.font = Font(bold=True, size=11)
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Применяем границы ко всей таблице
    for row in range(1, total_row + 1):
        for col in range(1, 14):
            cell = ws.cell(row, col)
            if cell.border.left.style == 'none':
                cell.border = thin_border
    
    # Настройка ширины колонок
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 40
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 10
    ws.column_dimensions['F'].width = 10
    ws.column_dimensions['G'].width = 3
    ws.column_dimensions['H'].width = 5
    ws.column_dimensions['I'].width = 40
    ws.column_dimensions['J'].width = 10
    ws.column_dimensions['K'].width = 10
    ws.column_dimensions['L'].width = 10
    ws.column_dimensions['M'].width = 10
    
    return wb

# ==========================================================
# ИНТЕРФЕЙС
# ==========================================================

apply_dynamic_styles()
apply_file_uploader_styles()

st.markdown(f"""
<div class="header-block">
    <h1>🍕 Продажи пицц по размерам</h1>
    <p>{greeting_by_time()}</p>
    <p style="margin-top:10px; margin-bottom:0; font-size:16px;">
        Отчет по продажам статичного списка пицц с разбивкой по размерам (23, 30, 35, 40 см)
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="content-block">
    <h3>📋 Описание отчета</h3>
    <p>Отчет показывает количество проданных пицц из фиксированного списка с разбивкой по размерам для СПб и Тюмени.</p>
    <p><b>Список пицц фиксирован и идет в строго определенном порядке по рейтингу.</b></p>
    <p><b>Период отчета автоматически определяется из загруженного файла.</b></p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="content-block">', unsafe_allow_html=True)
st.markdown("###  Загрузка файла")
file_main = st.file_uploader(
    "Загрузите файл рейтинг_продукт (Excel)",
    type=['xlsx'],
    key="static_pizza",
    help="Загрузите OLAP-отчет с продажами пицц"
)
st.markdown('</div>', unsafe_allow_html=True)

if file_main:
    st.markdown('<div class="content-block">', unsafe_allow_html=True)
    
    # Извлекаем период из файла
    try:
        period_str = extract_period_from_file(file_main)
        file_main.seek(0)
        st.info(f"📅 Обнаруженный период: **{period_str}**")
    except Exception as e:
        period_str = f"01.{datetime.now().strftime('%m')}.{datetime.now().year}"
        st.warning(f"⚠️ Не удалось определить период из файла. Используется текущий месяц.")
    
    if st.button("📊 Сгенерировать отчет", type="primary", use_container_width=True):
        with st.spinner("⏳ Формирую отчет..."):
            try:
                # Читаем и парсим файл
                df = read_and_parse_file(file_main)
                
                # Агрегируем данные
                data = aggregate_pizza_data(df)
                
                # Создаем Excel
                wb = create_excel_report(data, period_str)
                
                # Сохраняем в BytesIO
                output = io.BytesIO()
                wb.save(output)
                output.seek(0)
                
                st.success("✅ Отчет сформирован!")
                
                # Показываем превью для СПБ
                st.subheader("📋 Превью данных (СПБ)")
                
                # Создаем DataFrame для отображения
                preview_data = []
                for rating, pizza_name in STATIC_PIZZA_LIST:
                    row = {
                        'Рейтинг': rating,
                        'Пицца': pizza_name,
                    }
                    for size in [23, 30, 35, 40]:
                        row[f'{size} см'] = data['СПБ'][pizza_name]['sizes'][size]
                    row['Всего'] = data['СПБ'][pizza_name]['total']
                    preview_data.append(row)
                
                df_preview = pd.DataFrame(preview_data)
                st.dataframe(df_preview, use_container_width=True)
                
                # Кнопка скачивания
                st.download_button(
                    label="📥 Скачать отчет Excel",
                    data=output,
                    file_name=f"Продажи_пицц_по_размерам_{period_str.replace('.', '-')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"❌ Ошибка при формировании отчета: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("👆 Загрузите файл для начала работы")
