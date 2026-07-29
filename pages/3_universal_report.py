# pages/3_universal_report.py
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

st.set_page_config(page_title="Универсальный отчёт", layout="wide", page_icon="📊")

# Стили
st.markdown("""
<style>
.stApp { background: #f0f2f6 !important; }
.header-block {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 24px;
    border-radius: 16px;
    margin-bottom: 24px;
    color: white;
}
.content-block {
    background: white;
    padding: 24px;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.input-box {
    background: #fff3cd;
    border: 3px solid #ffc107;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
    box-shadow: 0 4px 15px rgba(255, 193, 7, 0.4);
}
textarea::placeholder {
    color: #6c757d !important;
    font-style: italic;
}
</style>
""", unsafe_allow_html=True)

# Функции
def normalize_text(text):
    if not isinstance(text, str): return ""
    # 1. Латиница в кириллицу
    replacements = {'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с', 'y': 'у', 'x': 'х',
                   'A': 'А', 'E': 'Е', 'O': 'О', 'P': 'Р', 'C': 'С', 'Y': 'У', 'X': 'Х', 'ё': 'е', 'Ё': 'Е'}
    for lat, cyr in replacements.items(): text = text.replace(lat, cyr)
    
    # 2. Базовая очистка
    text = text.lower().replace('"', '').replace("'", "")
    text = re.sub(r'\(.*?\)', '', text) # убираем скобки
    
    # 3. Убираем слова-паразиты для пицц (тесто, пицца, см)
    text = re.sub(r'\bпицца\b|\bpizza\b', '', text)
    text = re.sub(r'\bтонкое\b|\bтрадиционное\b|\bтесто\b|\bсм\b', '', text)
    
    # 4. Унификация чисел (чтобы "4 сыра" и "четыре сыра" были равны)
    num_words = {'четыре': '4', 'пять': '5', 'шесть': '6', 'семь': '7', 'восемь': '8', 'девять': '9', 'десять': '10'}
    for word, digit in num_words.items():
        text = text.replace(word, digit)
        
    # 5. Убираем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_size(text):
    """Извлекает размер пиццы (15, 23, 30, 35, 40) из строки"""
    if not isinstance(text, str): return None
    match = re.search(r'\b(15|23|30|35|40)\b', str(text))
    return match.group(1) if match else None

def map_city(legal_entity):
    le = str(legal_entity)
    if 'СПБ' in le: return 'СПБ'
    elif 'ПД' in le and 'СПБ' not in le: return 'Тюмень'
    return None

def extract_period(uploaded_file):
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

def read_file(uploaded_file):
    df = pd.read_excel(uploaded_file, header=None)
    header_row = None
    for idx, row in df.iterrows():
        vals = [str(v) for v in row.values if pd.notna(v)]
        if 'Юридическое лицо' in ' '.join(vals) and 'Блюдо' in ' '.join(vals):
            header_row = idx
            break
    if header_row is None: raise ValueError("Не найдены заголовки!")
    headers = df.iloc[header_row].values
    df = df[header_row + 1:].copy()
    df.columns = headers
    df = df.reset_index(drop=True)
    df = df[~df['Юридическое лицо'].astype(str).str.contains('OLAP|всего|Итого', na=False)]
    df = df.dropna(how='all')
    df['Юридическое лицо'] = df['Юридическое лицо'].ffill()
    df['Категория блюда'] = df['Категория блюда'].ffill()
    df = df[~df['Блюдо'].astype(str).str.contains(r'\+', na=False)]
    df = df[~df['Блюдо'].astype(str).str.contains('персонал', case=False, na=False)]
    df = df[df['Блюдо'].notna()]
    df['Количество блюд'] = pd.to_numeric(df['Количество блюд'], errors='coerce').fillna(0)
    df['Сумма со скидкой, р.'] = pd.to_numeric(df['Сумма со скидкой, р.'], errors='coerce').fillna(0)
    return df

def aggregate_data(df, rules_text):
    df = df.copy()
    df['Город'] = df['Юридическое лицо'].apply(map_city)
    df = df[df['Город'].notna()]
    
    # Предварительно вычисляем нормализованные имена и размеры для скорости
    df['Блюдо_norm'] = df['Блюдо'].apply(normalize_text)
    df['Размер'] = df['Блюдо'].apply(extract_size)
    
    rules = [line.strip() for line in rules_text.split('\n') if line.strip()]
    result = {}
    
    for city in ['СПБ', 'Тюмень']:
        city_data = df[df['Город'] == city]
        city_result = {}
        
        for rule in rules:
            rule_norm = normalize_text(rule)
            rule_size = extract_size(rule)
            rule_tokens = set(rule_norm.split())
            
            # 1. Быстрая фильтрация по размеру (если он указан в правиле)
            if rule_size:
                subset = city_data[city_data['Размер'] == rule_size]
            else:
                subset = city_data.copy()
            
            # 2. Проверка: все ли слова из правила есть в названии блюда
            def check_match(dish_norm):
                dish_tokens = set(dish_norm.split())
                return rule_tokens.issubset(dish_tokens)
            
            matches = subset[subset['Блюдо_norm'].apply(check_match)]
            
            city_result[rule] = {
                'qty': int(matches['Количество блюд'].sum()),
                'sum': round(matches['Сумма со скидкой, р.'].sum(), 2)
            }
        result[city] = city_result
    return result

def create_excel(data, period_str, rules):
    wb = Workbook()
    if 'Sheet' in wb.sheetnames: del wb['Sheet']
    ws = wb.create_sheet("Отчёт")
    border = Border(left=Side('thin'), right=Side('thin'), top=Side('thin'), bottom=Side('thin'))
    
    yellow_fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
    blue_fill = PatternFill(start_color='00BFFF', end_color='00BFFF', fill_type='solid')
    
    # Период
    ws.merge_cells('A1:H1')
    c = ws.cell(1, 1, period_str)
    c.font = Font(bold=True, size=16)
    c.alignment = Alignment(horizontal='center')
    c.fill = yellow_fill
    
    # Города
    ws.merge_cells('A2:D2')
    c = ws.cell(2, 1, "СПб сейчас")
    c.font = Font(bold=True, size=12)
    c.alignment = Alignment(horizontal='center')
    c.fill = blue_fill
    
    ws.merge_cells('E2:H2')
    c = ws.cell(2, 5, "Тюмень сейчас")
    c.font = Font(bold=True, size=12)
    c.alignment = Alignment(horizontal='center')
    c.fill = blue_fill
    
    # Заголовки
    for col, header in [(1, 'Наименование'), (2, 'Количество'), (3, 'Сумма, ₽'),
                        (5, 'Наименование'), (6, 'Количество'), (7, 'Сумма, ₽')]:
        c = ws.cell(3, col, header)
        c.font = Font(bold=True, size=10)
        c.border = border
        c.alignment = Alignment(horizontal='center')
    
    # Данные
    row = 4
    for rule in rules:
        ws.cell(row, 1, rule).border = border
        ws.cell(row, 2, data['СПБ'][rule]['qty']).border = border
        ws.cell(row, 2).alignment = Alignment(horizontal='center')
        ws.cell(row, 3, data['СПБ'][rule]['sum']).border = border
        ws.cell(row, 3).number_format = '#,##0.00'
        
        ws.cell(row, 5, rule).border = border
        ws.cell(row, 6, data['Тюмень'][rule]['qty']).border = border
        ws.cell(row, 6).alignment = Alignment(horizontal='center')
        ws.cell(row, 7, data['Тюмень'][rule]['sum']).border = border
        ws.cell(row, 7).number_format = '#,##0.00'
        row += 1
    
    # Итого
    total_row = row + 1
    for col in [1, 5]:
        c = ws.cell(total_row, col, 'ИТОГО')
        c.font = Font(bold=True, size=11)
        c.border = border
    
    for col in [2, 6]:
        c = ws.cell(total_row, col, f"=SUM({get_column_letter(col)}4:{get_column_letter(col)}{total_row-1})")
        c.font = Font(bold=True, size=11)
        c.border = border
        c.alignment = Alignment(horizontal='center')
    
    for col in [3, 7]:
        c = ws.cell(total_row, col, f"=SUM({get_column_letter(col)}4:{get_column_letter(col)}{total_row-1})")
        c.font = Font(bold=True, size=11)
        c.border = border
        c.number_format = '#,##0.00'
    
    ws.column_dimensions['A'].width = 40
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 3
    ws.column_dimensions['E'].width = 40
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 15
    
    return wb

# Интерфейс
st.markdown("""
<div class="header-block">
    <h1>📊 Универсальный отчёт</h1>
    <p>Умный отчёт с разбивкой пицц по размерам и нечётким поиском</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="content-block">
    <h3>📋 Как работает умный поиск</h3>
    <ul>
        <li><b>Для пицц:</b> Пишите название и размер, например: <code>Сырная 30</code> или <code>Четыре сыра 35</code>.</li>
        <li><b>Авто-игнорирование:</b> Программа сама игнорирует слова <i>"пицца", "тонкое", "традиционное", "тесто", "см"</i>. Поэтому правило <code>Сырная 30</code> найдёт и сложит <i>"Пицца сырная 30 см традиционное"</i> и <i>"Сырная 30 тонкое тесто"</i>.</li>
        <li><b>Унификация чисел:</b> <code>4 сыра</code> и <code>четыре сыра</code> считаются одной позицией.</li>
        <li><b>Для закусок:</b> Логика та же, пишите как в выгрузке, например: <code>Картофель из печи 150 гр</code>.</li>
        <li><b>Без размера:</b> Если написать просто <code>Сырная</code>, программа просуммирует все размеры этой пиццы.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# ПОЛЕ ВВОДА
st.markdown('<div class="input-box">', unsafe_allow_html=True)
st.markdown("### ✏️ ВВЕДИТЕ СПИСОК ПОЗИЦИЙ")
st.markdown("<p><b>Каждая строка = одна позиция в отчёте.</b></p>", unsafe_allow_html=True)

default_rules = """Сырная 15
Сырная 23
Сырная 30
Сырная 35
Сырная 40
Четыре сыра 30
Пепперони 30
Картофель из печи 150 гр
Рогалики с колбасками"""

rules_text = st.text_area(
    "Список позиций:",
    value="",
    height=300,
    key="rules_input",
    label_visibility="visible",
    placeholder=default_rules
)
st.markdown('</div>', unsafe_allow_html=True)

# ЗАГРУЗКА ФАЙЛА
st.markdown('<div class="content-block">', unsafe_allow_html=True)
st.markdown("### 📂 Загрузка файла")
file_main = st.file_uploader("Загрузите файл рейтинг_продукт (Excel)", type=['xlsx'], key="universal")
st.markdown('</div>', unsafe_allow_html=True)

# ГЕНЕРАЦИЯ
if file_main:
    st.markdown('<div class="content-block">', unsafe_allow_html=True)
    
    try:
        period_str = extract_period(file_main)
        file_main.seek(0)
        st.info(f"📅 Период: **{period_str}**")
    except:
        period_str = f"01.{datetime.now().strftime('%m')}.{datetime.now().year}"
        st.warning("⚠️ Не удалось определить период")
    
    if st.button("📊 Сгенерировать отчёт", type="primary", use_container_width=True):
        with st.spinner("Формирую отчёт..."):
            try:
                df = read_file(file_main)
                rules = [line.strip() for line in rules_text.split('\n') if line.strip()]
                
                if not rules:
                    st.error("❌ Введите хотя бы одну позицию в поле выше!")
                else:
                    data = aggregate_data(df, rules_text)
                    wb = create_excel(data, period_str, rules)
                    
                    output = io.BytesIO()
                    wb.save(output)
                    output.seek(0)
                    
                    st.success("✅ Отчёт сформирован!")
                    
                    st.subheader("📋 Превью (СПБ)")
                    preview = pd.DataFrame([
                        {'Позиция': rule, 'Количество': data['СПБ'][rule]['qty'], 'Сумма, ₽': data['СПБ'][rule]['sum']}
                        for rule in rules
                    ])
                    st.dataframe(preview, use_container_width=True)
                    
                    st.download_button(
                        label="📥 Скачать Excel",
                        data=output,
                        file_name=f"Отчёт_{period_str.replace('.', '-')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"❌ Ошибка: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("👆 Загрузите файл для начала работы")
