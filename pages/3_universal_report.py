# pages/3_universal_report.py
import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
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
}
</style>
""", unsafe_allow_html=True)

# Функции
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
    df = df[~df['Блюдо'].astype(str).str.contains('\+', na=False)]
    df = df[~df['Блюдо'].astype(str).lower().str.contains('персонал', na=False)]
    df = df[df['Блюдо'].notna()]
    df['Количество блюд'] = pd.to_numeric(df['Количество блюд'], errors='coerce').fillna(0)
    df['Сумма со скидкой, р.'] = pd.to_numeric(df['Сумма со скидкой, р.'], errors='coerce').fillna(0)
    return df

def aggregate_data(df, rules_text):
    df = df.copy()
    df['Город'] = df['Юридическое лицо'].apply(map_city)
    df = df[df['Город'].notna()]
    df['Блюдо_norm'] = df['Блюдо'].apply(normalize_text)
    rules = [line.strip() for line in rules_text.split('\n') if line.strip()]
    result = {}
    for city in ['СПБ', 'Тюмень']:
        city_data = df[df['Город'] == city]
        city_result = {}
        for rule in rules:
            rule_norm = normalize_text(rule)
            matching = city_data[city_data['Блюдо_norm'].str.contains(rule_norm, na=False)]
            city_result[rule] = {
                'qty': int(matching['Количество блюд'].sum()),
                'sum': round(matching['Сумма со скидкой, р.'].sum(), 2)
            }
        result[city] = city_result
    return result

def create_excel(data, period_str, rules):
    wb = Workbook()
    if 'Sheet' in wb.sheetnames: del wb['Sheet']
    ws = wb.create_sheet("Отчёт")
    border = Border(left=Side('thin'), right=Side('thin'), top=Side('thin'), bottom=Side('thin'))
    
    # Период (без цветной заливки, только жирный шрифт и выравнивание)
    ws.merge_cells('A1:H1')
    c = ws.cell(1, 1, period_str)
    c.font = Font(bold=True, size=16)
    c.alignment = Alignment(horizontal='center')
    
    # Города (без цветной заливки)
    ws.merge_cells('A2:D2')
    c = ws.cell(2, 1, "СПб сейчас")
    c.font = Font(bold=True, size=12)
    c.alignment = Alignment(horizontal='center')
    
    ws.merge_cells('E2:H2')
    c = ws.cell(2, 5, "Тюмень сейчас")
    c.font = Font(bold=True, size=12)
    c.alignment = Alignment(horizontal='center')
    
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
    <p>Гибкий отчёт с настраиваемым списком позиций</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="content-block">
    <h3>📋 Как работает</h3>
    <p><b>Принцип:</b></p>
    <ul>
        <li>Введите список позиций в поле ниже (каждая строка = одна позиция в отчёте)</li>
        <li>Точное совпадение → показывается как есть</li>
        <li>Частичное совпадение → суммируются все подходящие строки</li>
    </ul>
    <p><b>Пример:</b></p>
    <ul>
        <li><code>Картофель из печи 150 гр</code> + <code>Картофель из печи 200 гр</code> → две строки</li>
        <li><code>Картофель из печи</code> → одна строка (сумма обоих видов)</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# ПОЛЕ ВВОДА - ВСЕГДА ВИДНО
st.markdown('<div class="input-box">', unsafe_allow_html=True)
st.markdown("### ✏️ ВВЕДИТЕ СПИСОК ПОЗИЦИЙ")
st.markdown("<p><b>Каждая строка = одна позиция в отчёте.</b><br>Позиции суммируются, если название является частью названия в выгрузке.</p>", unsafe_allow_html=True)

default_rules = """Картофель из печи 150 гр
Картофель из печи 200 гр
Рогалики с колбасками
Рогалики с ветчиной
Сырные палочки
Чикен Джонер
Пепперони
Супер Папа
Мясная"""

rules_text = st.text_area(
    "Список позиций (каждая с новой строки):",
    value=default_rules,
    height=300,
    key="rules_input",
    label_visibility="visible"
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
