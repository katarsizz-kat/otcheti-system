import streamlit as st
import pandas as pd
import os
import sys
from typing import List, Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.pptx_builder import generate_flexible_presentation

st.set_page_config(page_title="Презентация КР", page_icon="🍕", layout="wide")

# Стандартная шапка как на других страницах
st.title("🍕 Генерация презентации")
st.markdown("---")

st.write("Загрузите Excel-файлы с данными клиентского рейтинга и опишите структуру презентации.")

# ==========================================
#  БЛОК 1: ЗАГРУЗКА ФАЙЛОВ
# ==========================================
st.subheader("📁 1. Загрузка данных")

# Инициализация session_state для хранения файлов
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []

col1, col2 = st.columns([3, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Загрузите Excel-файл", 
        type=['xlsx'], 
        accept_multiple_files=False,
        key=f"file_{len(st.session_state.uploaded_files)}"
    )

with col2:
    if st.button("➕ Добавить файл", type="secondary", use_container_width=True):
        if uploaded_file is not None:
            st.session_state.uploaded_files.append(uploaded_file)
            st.success(f"✅ Файл {uploaded_file.name} добавлен!")
        else:
            st.warning("⚠️ Сначала выберите файл!")

# Отображение загруженных файлов
if st.session_state.uploaded_files:
    st.markdown(f"**Загружено файлов: {len(st.session_state.uploaded_files)}**")
    
    # Показываем список с возможностью удаления
    files_to_remove = []
    for idx, file in enumerate(st.session_state.uploaded_files):
        col_a, col_b, col_c = st.columns([6, 2, 1])
        with col_a:
            st.text(f"{idx + 1}. {file.name}")
        with col_b:
            st.text(f"📊 {round(file.size / 1024, 1)} KB")
        with col_c:
            if st.button("🗑️", key=f"remove_{idx}"):
                files_to_remove.append(idx)
    
    # Удаляем файлы, если нужно
    if files_to_remove:
        for idx in sorted(files_to_remove, reverse=True):
            st.session_state.uploaded_files.pop(idx)
        st.rerun()
    
    # Кнопка очистки всех
    if st.button("🗑️ Очистить все файлы", type="secondary"):
        st.session_state.uploaded_files = []
        st.rerun()

# ==========================================
# 📝 БЛОК 2: СТРУКТУРА ПРЕЗЕНТАЦИИ
# ==========================================
st.divider()
st.subheader("📝 2. Структура презентации")

st.markdown("""
**Опишите, какие слайды нужны** (каждый слайд с новой строки):

Пример:
Титульный слайд: Клиентский рейтинг за Июнь 2026
Общие показатели по сети
Оценки по Санкт-Петербургу
Оценки по Тюмени
Анализ жалоб: Продукт и Приготовление
Анализ жалоб: Сервис и Доставка
Положительные отзывы
Итоги и рекомендации
""")

presentation_structure = st.text_area(
    "Структура презентации:",
    height=200,
    placeholder="Введите название каждого слайда с новой строки..."
)

# ==========================================
# 🎨 БЛОК 3: ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ
# ==========================================
st.divider()
st.subheader("⚙️ 3. Настройки")

col_x, col_y = st.columns(2)

with col_x:
    report_period = st.text_input("Период отчёта", value="Июнь 2026")
    
with col_y:
    color_theme = st.selectbox(
        "Цветовая тема",
        ["Классическая (Томат + Базилик)", "Оливковая", "Сырная"],
        index=0
    )

# ==========================================
#  ГЕНЕРАЦИЯ ПРЕЗЕНТАЦИИ
# ==========================================
st.divider()

if st.button("🍕 Сгенерировать презентацию", type="primary", use_container_width=True):
    
    if not st.session_state.uploaded_files:
        st.error("❌ Загрузите хотя бы один файл!")
        st.stop()
    
    if not presentation_structure.strip():
        st.error(" Опишите структуру презентации!")
        st.stop()
    
    with st.spinner("🔥 Готовим презентацию... Анализируем данные из файлов..."):
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Шаг 1: Чтение всех файлов
        status_text.text("📖 Читаем файлы...")
        all_dataframes = {}
        for idx, file in enumerate(st.session_state.uploaded_files):
            file.seek(0)  # Сбрасываем указатель в начало
            try:
                # Читаем все листы
                df_sheets = pd.read_excel(file, sheet_name=None)
                
                # Обрабатываем каждый лист - убираем пустые строки и столбцы
                processed_sheets = {}
                for sheet_name, df in df_sheets.items():
                    # Удаляем полностью пустые строки и столбцы
                    df = df.dropna(how='all', axis=0)  # пустые строки
                    df = df.dropna(how='all', axis=1)  # пустые столбцы
                    # Заполняем NaN пустыми строками для отображения
                    df = df.fillna('')
                    processed_sheets[sheet_name] = df
                
                all_dataframes[file.name] = processed_sheets
                progress_bar.progress((idx + 1) / len(st.session_state.uploaded_files) * 0.3)
            except Exception as e:
                st.error(f"❌ Ошибка чтения файла {file.name}: {e}")
                st.stop()
        
        # Шаг 2: Парсинг структуры
        status_text.text(" Анализируем структуру...")
        slides_structure = [line.strip() for line in presentation_structure.split('\n') if line.strip()]
        progress_bar.progress(0.5)
        
        # Шаг 3: Генерация презентации
        status_text.text("🎨 Создаём слайды...")
        
        safe_period = "".join(c for c in report_period if c.isalnum() or c in (' ', '_')).rstrip()
        output_filename = f"Презентация_КР_{safe_period}.pptx"
        
        try:
            pptx_path = generate_flexible_presentation(
                all_dataframes=all_dataframes,
                slides_structure=slides_structure,
                period_text=report_period,
                theme=color_theme,
                output_path=output_filename
            )
            
            progress_bar.progress(1.0)
            status_text.text("✅ Презентация готова!")
            
            # Кнопка скачивания
            with open(pptx_path, "rb") as file:
                st.download_button(
                    label="💾 Скачать презентацию (PPTX)",
                    data=file,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )
            
            # Показываем превью
            st.success(f"🎉 Презентация успешно создана! Слайдов: {len(slides_structure)}")
            st.info(f"📊 Использовано файлов: {len(st.session_state.uploaded_files)}")
            
            if os.path.exists(pptx_path):
                os.remove(pptx_path)
                
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ Ошибка генерации: {e}")
            import traceback
            st.code(traceback.format_exc())
