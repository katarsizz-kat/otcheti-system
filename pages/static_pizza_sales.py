st.write("🔥 ТЕСТ — если вы видите это, файл работает!")


# pages/static_pizza_sales.py
import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Продажи пицц по размерам", layout="wide", page_icon="")

# ==========================================================
# СТИЛИ
# ==========================================================

def apply_styles():
    st.markdown("""
    <style>
        .stApp { background: linear-gradient(135deg, #EBF5FB 0%, #FFFFFF 100%) !important; }
        .header-block {
            background: linear-gradient(135deg, #3498DB 0%, #EBF5FB 100%);
            padding: 24px;
            border-radius: 16px;
            margin-bottom: 24px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.15);
        }
        .header-block h1 { margin: 0; color: #FFFFFF; font-size: 36px; }
        .header-block p { margin-top: 8px; color: #FFFFFF; font-size: 18px; }
        .content-block {
            background: rgba(255, 255, 255, 0.95);
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .stButton>button {
            background: #2E86C1 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: bold !important;
        }
        .input-box {
            background: #FFF9E6;
            border: 3px solid #F39C12;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
        }
        .input-box h3 {
            color: #D68910;
            margin-top: 0;
            margin-bottom: 12px;
            font-size: 22px;
        }
        textarea {
            font-family: 'Courier New', monospace !important;
            font-size: 14px !important;
            border: 2px solid #F39C12 !important;
            border-radius: 8px !important;
        }
    </style>
    """, unsafe_allow_html=True)

# ==========================================================
# ФУНКЦИИ
# ==========================================================

def normalize_text(text):
    if not isinstance(text, str): return ""
    replacements = {'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с', 'y': 'у', 'x': 'х',
                   'A': 'А', 'E': 'Е', 'O': 'О', 'P': 'Р', 'C': 'С', 'Y': 'У', 'X': 'Х', 'ё': 'е', 'Ё': 'Е'}
    for lat, cyr in replacements.items(): text = text.replace(lat, cyr)
    text = text.lower().replace('"', '')
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'^пицца\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def map_city(legal_entity):
    le = str(legal_entity)
    if 'СПБ' in le: return 'СПБ'
    elif 'ПД' in le and 'СПБ' not in le: return 'Тюмень'
    return None

def extract_size_from_category(category):
    category_str = str(category).lower()
    for size in [40, 35, 30, 23, 15]:
        if str(size) in category_str:
            return size
    return None

def extract_period_from_file(uploaded_file):
    df = pd.read_excel(uploaded_file, header=None, nrows=10)
    for idx, row in df.iterrows():
        for val in row.values:
            if pd.notna(val) and 'Период' in str(val):
                match = re.search(r'(\d{2}\.\d{2}\.\d{4})\s+по\s+(\d{2}\.\d{2}\.\d{4})', str(val))
                if match:
                    start = datetime.strptime(match.group(1), '%d.%m.%Y')
                    end = datetime.strptime(match.group(2), '%d.%m.%Y')
                    return f"{start.strftime('%d.%m')}-{end.strftime('%d.%m.%Y')}"
    return f"01.{datetime.now().strftime('%m')}.{datetime.now().year}"

def read_and_parse_file(uploaded_file):
    df = pd.read_excel(uploaded_file, header=None)
    header_row = None
    for idx, row in df.iterrows():
        vals = [str(v) for v in row.values if pd.notna(v)]
        if 'Юридическое лицо' in ' '.join(vals) and 'Блюдо' in ' '.join(vals):
            header_row = idx; break
    if header_row is None: raise ValueError("Не найдены заголовки!")
    headers = df.iloc[header_row].values
    df = df[header_row + 1:].copy()
    df.columns = headers
    df = df.reset_index(drop=True)
    df = df[~df['Юридическое лицо'].astype(str).str.contains('OLAP|всего|Итого', na=False)]
    df = df.dropna(how='all')
    df['Юридическое лицо'] = df['Юридическое лицо'].ffill()
    df['Категория блюда'] = df['Категория блюда'].ffill()
    df = df[~df['Блюдо'].astype(str).str.contains('\+', na=False)]
    df = df[~df['Блюдо'].astype(str).str.lower().str.contains('персонал', na=False)]
    df = df[df['Блюдо'].notna()]
    df['Количество блюд'] = pd.to_numeric(df['Количество блюд'], errors='coerce').fillna(0)
    return df

def find_pizza_in_list(pizza_name_normalized, pizza_list):
    """Находит пиццу в списке по нормализованному названию."""
    for rating, display_name in pizza_list:
        display_norm = normalize_text(display_name)
        if pizza_name_normalized == display_norm or display_norm in pizza_name_normalized:
            return display_name
    return None

def aggregate_pizza_data(df, pizza_list):
    df = df.copy()
    df['Город'] = df['Юридическое лицо'].apply(map_city)
    df = df[df['Город'].notna()]
    
    df['Категория_lower'] = df['Категория блюда'].astype(str).str.lower()
    df_pizza = df[df['Категория_lower'].str.contains('тесто', na=False)].copy()
    
    df_pizza['Размер'] = df_pizza['Категория блюда'].apply(extract_size_from_category)
    df_pizza = df_pizza[df_pizza['Размер'].isin([23, 30, 35, 40])]
    
    df_pizza['Блюдо_norm'] = df_pizza['Блюдо'].apply(normalize_text)
    
    result = {}
    for city in ['СПБ', 'Тюмень']:
        city_data = df_pizza[df_pizza['Город'] == city]
        pizza_data = {}
        
        for rating, display_name in pizza_list:
            sizes = {23: 0, 30: 0, 35: 0, 40: 0}
            
            for _, row in city_data.iterrows():
                found = find_pizza_in_list(row['Блюдо_norm'], [(rating, display_name)])
                if found == display_name:
                    size = row['Размер']
                    if size in sizes:
                        sizes[size] += int(row['Количество блюд'])
            
            pizza_data[display_name] = {
                'rating': rating,
                'sizes': sizes,
                'total': sum(sizes.values())
            }
        
        result[city] = pizza_data
    
    return result

def create_excel(data, period_str, pizza_list):
    wb = Workbook()
    if 'Sheet' in wb.sheetnames: del wb['Sheet']
    ws = wb.create_sheet("Продажи по размерам")
    border = Border(left=Side('thin'), right=Side('thin'), top=Side('thin'), bottom=Side('thin'))
    
    # Период
    ws.merge_cells('A1:M1')
    c = ws.cell(1, 1, period_str)
    c.font = Font(bold=True, size=16)
    c.alignment = Alignment(horizontal='center')
    c.fill = PatternFill('FFFF00', 'FFFF00', 'solid')
    
    # Города
    ws.merge_cells('A2:F2')
    c = ws.cell(2, 1, "СПб сейчас")
    c.font = Font(bold=True, size=12)
    c.alignment = Alignment(horizontal='center')
    c.fill = PatternFill('00BFFF', '00BFFF', 'solid')
    
    ws.merge_cells('H2:M2')
    c = ws.cell(2, 8, "Тюмень сейчас")
    c.font = Font(bold=True, size=12)
    c.alignment = Alignment(horizontal='center')
    c.fill = PatternFill('00BFFF', '00BFFF', 'solid')
    
    # Заголовки
    for col, header in [(3, '23'), (4, '30'), (5, '35'), (6, '40'),
                        (9, '23'), (10, '30'), (11, '35'), (12, '40')]:
        c = ws.cell(3, col, header)
        c.font = Font(bold=True, size=10)
        c.border = border
        c.alignment = Alignment(horizontal='center')
    
    # Данные
    row = 4
    current_rating = None
    for rating, display_name in pizza_list:
        if current_rating is not None and current_rating != rating:
            row += 1
        current_rating = rating
        
        # СПБ
        ws.cell(row, 1, rating).border = border
        ws.cell(row, 1).alignment = Alignment(horizontal='center')
        ws.cell(row, 2, display_name).border = border
        
        spb_data = data['СПБ'][display_name]['sizes']
        for col_idx, size in enumerate([23, 30, 35, 40], 3):
            ws.cell(row, col_idx, spb_data[size]).border = border
            ws.cell(row, col_idx).alignment = Alignment(horizontal='center')
        
        # Тюмень
        ws.cell(row, 8, rating).border = border
        ws.cell(row, 8).alignment = Alignment(horizontal='center')
        ws.cell(row, 9, display_name).border = border
        
        tmn_data = data['Тюмень'][display_name]['sizes']
        for col_idx, size in enumerate([23, 30, 35, 40], 9):
            ws.cell(row, col_idx, tmn_data[size]).border = border
            ws.cell(row, col_idx).alignment = Alignment(horizontal='center')
        
        row += 1
    
    # Итого
    total_row = row + 1
    ws.cell(total_row, 2, 'ИТОГО').font = Font(bold=True, size=11)
    ws.cell(total_row, 2).border = border
    
    for col in [3, 4, 5, 6]:
        c = ws.cell(total_row, col, f"=SUM({get_column_letter(col)}4:{get_column_letter(col)}{total_row-1})")
        c.font = Font(bold=True, size=11)
        c.border = border
        c.alignment = Alignment(horizontal='center')
    
    ws.cell(total_row, 9, 'ИТОГО').font = Font(bold=True, size=11)
    ws.cell(total_row, 9).border = border
    
    for col in [10, 11, 12, 13]:
        c = ws.cell(total_row, col, f"=SUM({get_column_letter(col)}4:{get_column_letter(col)}{total_row-1})")
        c.font = Font(bold=True, size=11)
        c.border = border
        c.alignment = Alignment(horizontal='center')
    
    # Ширина колонок
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

apply_styles()

st.markdown("""
<div class="header-block">
    <h1>🍕 Продажи пицц по размерам</h1>
    <p>Отчёт по продажам с настраиваемым списком пицц</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="content-block">
    <h3>📋 Как работает</h3>
    <p>Введите список пицц в поле ниже (каждая с новой строки). Система автоматически найдёт их в выгрузке и покажет продажи по размерам.</p>
</div>
""", unsafe_allow_html=True)

# ==========================================================
# 🔥 ПОЛЕ ДЛЯ ВВОДА СПИСКА ПИЦЦ (ВСЕГДА ВИДНО!)
# ==========================================================

st.markdown('<div class="input-box">', unsafe_allow_html=True)
st.markdown("### ✏️ ВВЕДИТЕ СПИСОК ПИЦЦ")
st.markdown("<p><b>Каждая строка = одна пицца в отчёте.</b><br>Укажите рейтинг и название через запятую или просто название.</p>", unsafe_allow_html=True)

default_pizzas = """6, Большая Бонанза
6, 6 сыров
6, 8 сыров
6, Любимая папина пицца
5, Мясная
5, 4 сыра
5, Итальянская с моцареллой и пепперони
5, Маленькая Италия
5, Баварская
5, Папа Микс
5, Цыпленок Рэнч
5, Альфредо
5, Мексиканская
5, Супер Папа
5, Цыпленок Барбекю
4, Чизбургер
4, Цыплёнок Флорентина
4, Мясное барбекю
4, Гавайская
4, Двойная пепперони
3, Пепперони
3, Ветчина и Грибы
3, Чикен Пармеджано
2, Вегетарианская
2, Маргарита
2, Капричиоза
2, Цыплёнок Грин
1, Сырная Пицца"""

pizza_input = st.text_area(
    "Список пицц (рейтинг, название):",
    value=default_pizzas,
    height=400,
    key="pizza_input",
    label_visibility="visible"
)
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================================
# ЗАГРУЗКА ФАЙЛА
# ==========================================================

st.markdown('<div class="content-block">', unsafe_allow_html=True)
file_main = st.file_uploader("📂 Загрузите файл рейтинг_продукт (Excel)", type=['xlsx'], key="pizza_sales")
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================================
# ГЕНЕРАЦИЯ ОТЧЁТА
# ==========================================================

if file_main:
    st.markdown('<div class="content-block">', unsafe_allow_html=True)
    
    try:
        period_str = extract_period_from_file(file_main)
        file_main.seek(0)
        st.info(f" Период: **{period_str}**")
    except:
        period_str = f"01.{datetime.now().strftime('%m')}.{datetime.now().year}"
        st.warning("️ Не удалось определить период")
    
    if st.button("📊 Сгенерировать отчёт", type="primary", use_container_width=True):
        with st.spinner("⏳ Формирую отчёт..."):
            try:
                # Парсим список пицц из ввода
                pizza_list = []
                for line in pizza_input.split('\n'):
                    line = line.strip()
                    if not line: continue
                    parts = line.split(',')
                    if len(parts) >= 2:
                        rating = int(parts[0].strip())
                        name = ','.join(parts[1:]).strip()
                        pizza_list.append((rating, name))
                    else:
                        pizza_list.append((0, line))
                
                if not pizza_list:
                    st.error("❌ Введите хотя бы одну пиццу!")
                else:
                    df = read_and_parse_file(file_main)
                    data = aggregate_pizza_data(df, pizza_list)
                    wb = create_excel(data, period_str, pizza_list)
                    
                    output = io.BytesIO()
                    wb.save(output)
                    output.seek(0)
                    
                    st.success("✅ Отчёт сформирован!")
                    
                    # Превью
                    st.subheader("📋 Превью (СПБ)")
                    preview = []
                    for rating, name in pizza_list:
                        row = {'Рейтинг': rating, 'Пицца': name}
                        for size in [23, 30, 35, 40]:
                            row[f'{size} см'] = data['СПБ'][name]['sizes'][size]
                        row['Всего'] = data['СПБ'][name]['total']
                        preview.append(row)
                    st.dataframe(pd.DataFrame(preview), use_container_width=True)
                    
                    st.download_button(
                        label="📥 Скачать Excel",
                        data=output,
                        file_name=f"Продажи_пицц_{period_str.replace('.', '-')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"❌ Ошибка: {str(e)}")
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("👆 Загрузите файл для начала работы")

