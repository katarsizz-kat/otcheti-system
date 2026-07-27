import streamlit as st
import os
import sys

# Добавляем корень проекта в путь, если нужно (чтобы видеть utils и config)
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

# Получаем данные из session_state (если они туда сохраняются на странице 2_KR_week)
df_ratings = st.session_state.get('df_ratings', None)
df_reviews = st.session_state.get('df_reviews', None)

if df_ratings is None or df_reviews is None:
    st.warning("⚠️ Данные не найдены. Перейдите на страницу 'КР Неделя/Месяц', загрузите файлы и обработайте их, либо загрузите их здесь.")
    
    # Здесь можно добавить дублирующие file_uploader'ы, если нужно
    st.stop()

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
            
            # Вызываем изолированную функцию
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
