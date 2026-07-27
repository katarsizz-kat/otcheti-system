import streamlit as st
import pandas as pd
import os
import time

# Импортируем функцию генерации (убедись, что путь правильный)
# from utils.pptx_gen import create_presentation 
# Или откуда ты её импортируешь, например:
from components import create_presentation 

# ==========================================
# 🎨 НАСТРОЙКИ СТРАНИЦЫ
# ==========================================
st.set_page_config(page_title="Презентация КР", page_icon="🍕", layout="wide")

st.markdown("""
    <h1 style='text-align: center; color: #E12D26; font-family: Oswald;'>
        🍕 ГЕНЕРАЦИЯ ПРЕЗЕНТАЦИИ
    </h1>
    <p style='text-align: center; color: #03592D; font-family: Roboto Condensed; font-size: 20px;'>
        Когда есть вкус, есть эмоции. Формируем красивый отчёт в фирменном стиле.
    </p>
""", unsafe_allow_html=True)

st.divider()

# ==========================================
# 📂 ПОЛУЧЕНИЕ ДАННЫХ
# ==========================================
# Проверяем, есть ли уже обработанные данные в session_state (если ты их туда сохраняешь на стр. 2)
# Если нет, даем возможность загрузить файлы заново.

df_ratings = st.session_state.get('df_ratings', None)
df_reviews = st.session_state.get('df_reviews', None)

if df_ratings is None or df_reviews is None:
    st.warning("⚠️ Данные не найдены. Загрузите исходные файлы Excel для формирования презентации.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        file_site = st.file_uploader("Сайт", type=['xlsx'])
    with col2:
        file_agg = st.file_uploader("Агрегаторы", type=['xlsx'])
    with col3:
        file_geo = st.file_uploader("Геосервисы", type=['xlsx'])
        
    if file_site and file_agg and file_geo:
        if st.button("🔄 Обработать данные для презентации", type="primary"):
            with st.spinner("Анализируем вкусы и настроения..."):
                # ⚠️ ЗДЕСЬ ТВОЯ ЛОГИКА ОБРАБОТКИ ФАЙЛОВ
                # Тебе нужно вызвать ту же функцию, что и на 2-й странице,
                # которая возвращает df_ratings и df_reviews
                
                # Пример-заглушка:
                # df_ratings, df_reviews = process_kr_files(file_site, file_agg, file_geo)
                
                # Сохраняем в session_state, чтобы не грузить файлы снова
                st.session_state['df_ratings'] = df_ratings
                st.session_state['df_reviews'] = df_reviews
                st.rerun()
    st.stop()

# ==========================================
# 📊 ПРЕДПРОСМОТР И ГЕНЕРАЦИЯ
# ==========================================
st.success("✅ Данные успешно загружены и готовы к экспорту!")

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📈 Краткая сводка")
    st.dataframe(df_ratings.head(), use_container_width=True)

with col_right:
    st.subheader("⚙️ Параметры")
    report_period = st.text_input("Период отчёта (например: Неделя 12-18 Авг)", value="Текущая неделя")
    
    st.markdown("---")
    
    if st.button("🍕 Сгенерировать PowerPoint", type="primary", use_container_width=True):
        with st.spinner("Готовим презентацию... Добавляем лучшие ингредиенты!"):
            output_filename = f"Клиентский_рейтинг_Презентация_{report_period.replace(' ', '_')}.pptx"
            
            # Вызываем функцию генерации
            pptx_path = create_presentation(
                df_ratings=df_ratings, 
                df_reviews=df_reviews, 
                period_text=report_period,
                output_path=output_filename
            )
            
            # Даём кнопку на скачивание
            with open(pptx_path, "rb") as file:
                st.download_button(
                    label="💾 Скачать презентацию (PPTX)",
                    data=file,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )
            
            # Удаляем временный файл с сервера
            if os.path.exists(pptx_path):
                os.remove(pptx_path)
                
            st.balloons()
