import streamlit as st
import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.pptx_builder import generate_kr_presentation

st.set_page_config(page_title="Презентация КР", page_icon="🍕", layout="wide")

st.markdown("""
    <h1 style='text-align: center; color: #E12D26; font-family: Oswald;'>
        🍕 ГЕНЕРАЦИЯ ПРЕЗЕНТАЦИИ
    </h1>
    <p style='text-align: center; color: #03592D; font-family: Roboto Condensed; font-size: 20px;'>
        Когда есть вкус, есть эмоции. Формируем отчёт в фирменном стиле.
    </p>
""", unsafe_allow_html=True)

st.divider()

# Проверяем session_state
df_ratings = st.session_state.get('df_ratings', None)
df_reviews = st.session_state.get('df_reviews', None)

if df_ratings is None or df_reviews is None:
    st.warning("⚠️ Данные не найдены. Загрузите файлы здесь или обработайте их на странице 'КР Неделя'.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        file_site = st.file_uploader("📊 Сайт", type=['xlsx'], key="site_pptx")
    with col2:
        file_agg = st.file_uploader("📊 Агрегаторы", type=['xlsx'], key="agg_pptx")
    with col3:
        file_geo = st.file_uploader("📊 Геосервисы", type=['xlsx'], key="geo_pptx")
    
    if file_site and file_agg and file_geo:
        if st.button("🔄 Обработать данные для презентации", type="primary"):
            with st.spinner("Анализируем вкусы и настроения..."):
                # ⚠️ ЗДЕСЬ НУЖНО ВЫЗВАТЬ ТУ ЖЕ ФУНКЦИЮ ОБРАБОТКИ, ЧТО И НА СТРАНИЦЕ 2
                # Например:
                # df_ratings, df_reviews = process_kr_files(file_site, file_agg, file_geo)
                
                # Временно заглушка - замени на свою функцию
                st.error("❌ Нужно добавить функцию обработки файлов. См. инструкцию ниже.")
                st.stop()
    st.stop()

# Если данные есть - показываем интерфейс генерации
st.success("✅ Данные успешно загружены и готовы к экспорту!")

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📈 Краткая сводка")
    st.dataframe(df_ratings.head(), use_container_width=True)

with col_right:
    st.subheader("⚙️ Параметры")
    report_period = st.text_input("Период отчёта", value="Неделя 12-18 Авг")
    
    st.markdown("---")
    
    if st.button("🍕 Сгенерировать PowerPoint", type="primary", use_container_width=True):
        with st.spinner("Готовим презентацию... Добавляем лучшие ингредиенты!"):
            safe_period = "".join(c for c in report_period if c.isalnum() or c in (' ', '_')).rstrip()
            output_filename = f"КР_Презентация_{safe_period}.pptx"
            
            pptx_path = generate_kr_presentation(
                df_ratings=df_ratings, 
                df_reviews=df_reviews, 
                period_text=report_period,
                output_path=output_filename
            )
            
            with open(pptx_path, "rb") as file:
                st.download_button(
                    label="💾 Скачать презентацию (PPTX)",
                    data=file,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )
            
            if os.path.exists(pptx_path):
                os.remove(pptx_path)
                
            st.balloons()
