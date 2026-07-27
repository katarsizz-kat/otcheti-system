import streamlit as st
import pandas as pd
import os
import sys
from typing import List, Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.pptx_builder import generate_flexible_presentation

st.set_page_config(page_title="Презентация КР", page_icon="🍕", layout="wide")

st.markdown("""
    <h1 style='text-align: center; color: #E12D26; font-family: Oswald;'>
        🍕 КОНСТРУКТОР ПРЕЗЕНТАЦИЙ
    </h1>
    <p style='text-align: center; color: #03592D; font-family: Roboto Condensed; font-size: 20px;'>
        Загрузите файлы и опишите структуру — мы соберём идеальную презентацию!
    </p>
""", unsafe_allow_html=True)

st.divider()

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
    st.markdown(f"** Загружено файлов: {len(st.session_state.uploaded_files)}**")
    
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
    if st.button("️ Очистить все файлы", type="secondary"):
        st.session_state.uploaded_files = []
        st.rerun()

# ==========================================
# 📝 БЛОК 2: СТРУКТУРА ПРЕЗЕНТАЦИИ
# ==========================================
st.divider()
st.subheader(" 2. Структура презентации")

st.markdown("""
**Опишите, какие слайды нужны** (каждый слайд с новой строки):

Пример:
