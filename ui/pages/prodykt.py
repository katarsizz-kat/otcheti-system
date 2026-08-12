import streamlit as st
from typing import Dict, Any, Callable


def render_prodykt_page(files_state: Dict[str, Any], generator_func: Callable):
    """
    Чистый UI слой страницы Продукт.
    Не содержит openpyxl, pandas, бизнес-логику.
    """

    # Однострочная CSS-анимация появления
    st.markdown(
        "<style>.fade-in{animation:fadeIn .4s ease-out}@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}</style>",
        unsafe_allow_html=True
    )

    st.markdown("<div class='fade-in'>", unsafe_allow_html=True)

    # ==================== ИНСТРУКЦИЯ ====================
    st.markdown(
        """
<div style="background: rgba(255,255,255,0.75); padding: 20px; border-radius: 15px; margin-bottom: 20px; border: 1px solid rgba(0,0,0,0.08);">
    <h3 style="margin-top:0;">📋 Инструкция</h3>
    <p style="margin-bottom:8px;">Загрузите два файла для формирования отчета:</p>
    <ol style="margin:0 0 12px 0; padding-left:20px;">
        <li><b>Основной файл</b> — OLAP-отчет с пиццами, закусками и т.д.</li>
        <li><b>Файл комбо</b> — OLAP-отчет с комбо-наборами</li>
    </ol>
    <p style="margin:0;">💡 Названия файлов могут быть любыми — важна только структура данных внутри.</p>
</div>
""",
        unsafe_allow_html=True
    )

    # ==================== ЗАГРУЗКА ФАЙЛОВ ====================
    col1, col2 = st.columns(2)

    with col1:
        file_main = st.file_uploader(
            "📁 Основной файл",
            type=["xlsx"],
            key="prod_main"
        )

    with col2:
        file_combo = st.file_uploader(
            "📁 Файл комбо",
            type=["xlsx"],
            key="prod_combo"
        )

    # Обновляем состояние файлов
    files_state["main"] = file_main
    files_state["combo"] = file_combo

    # ==================== ГЕНЕРАЦИЯ ОТЧЁТА ====================
    if files_state.get("main") and files_state.get("combo"):
        st.success("✅ Оба файла загружены!")

        if st.button(
            "🚀 Сгенерировать отчет",
            type="primary",
            use_container_width=True
        ):
            with st.spinner("⏳ Формирую отчет..."):
                try:
                    # Сброс указателя файла перед передачей в логику
                    files_state["main"].seek(0)
                    files_state["combo"].seek(0)

                    # Вызов чистой бизнес-логики из report/prodykt.py
                    excel_buffer = generator_func(
                        files_state["main"],
                        files_state["combo"]
                    )

                    st.success("✅ Отчет сформирован!")

                    st.download_button(
                        label="📥 Скачать Итоговый_отчет.xlsx",
                        data=excel_buffer,
                        file_name="Итоговый_отчет_Продукт.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                except ValueError as ve:
                    st.error(f"❌ Ошибка данных: {ve}")

                except Exception as e:
                    st.error(f"❌ Системная ошибка: {e}")
                    with st.expander("Показать traceback"):
                        import traceback
                        st.code(traceback.format_exc())

    else:
        st.info("👆 Загрузите оба файла для начала работы")

    st.markdown("</div>", unsafe_allow_html=True)