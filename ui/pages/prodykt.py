"""Чистый UI слой страницы Продукт.
Не содержит openpyxl, pandas, бизнес-логику.

v2.0 (дизайн-система Sage & Sandstone):
- инструкция и текст — на CSS-переменных (убран хардкод rgba(255,255,255,0.75));
- локальный fadeIn-стиль удалён (в базовом styles.py уже есть .fade-in);
- celebrate_report_success() после успешной генерации — пастельные шарики;
- render_theme_controls() — блок "Оформление" в сайдбаре (футера нет).
"""
import streamlit as st
from typing import Dict, Any, Callable

# ==========================================================
# ИМПОРТ UI-ДОПОЛНЕНИЙ (шарики успеха + блок "Оформление")
# ==========================================================
try:
    from config.effects import celebrate_report_success
except Exception:
    celebrate_report_success = None

try:
    from components import render_theme_controls
except Exception:
    render_theme_controls = None


def render_prodykt_page(files_state: Dict[str, Any], generator_func: Callable):
    """
    Чистый UI слой страницы Продукт.
    """
    # Блок "Оформление" в сайдбаре (тема + праздничные эффекты)
    if render_theme_controls is not None:
        try:
            render_theme_controls()
        except Exception:
            pass

    st.markdown("<div class='fade-in'>", unsafe_allow_html=True)

    # ==================== ИНСТРУКЦИЯ ====================
    st.markdown(
        """
        <div style="background: var(--card-bg, #FFFFFF); padding: 20px;
            border-radius: 15px; margin-bottom: 20px;
            border: 1px solid var(--card-border, #D9D4CB);">
            <h3 style="margin-top:0; color: var(--text-primary, #2D3A2E);">📋 Инструкция</h3>
            <p style="margin-bottom:8px; color: var(--text-primary, #2D3A2E);">
                Загрузите два файла для формирования отчета:</p>
            <ol style="margin:0 0 12px 0; padding-left:20px; color: var(--text-primary, #2D3A2E);">
                <li><b>Основной файл</b> — OLAP-отчет с пиццами, закусками и т.д.</li>
                <li><b>Файл комбо</b> — OLAP-отчет с комбо-наборами</li>
            </ol>
            <p style="margin:0; color: var(--text-secondary, #5D6A5C);">
                💡 Названия файлов могут быть любыми — важна только структура данных внутри.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ==================== ЗАГРУЗКА ФАЙЛОВ ====================
    col1, col2 = st.columns(2)
    with col1:
        file_main = st.file_uploader(
            "📁 Основной файл",
            type=["xlsx"],
            key="prod_main",
        )
    with col2:
        file_combo = st.file_uploader(
            "📁 Файл комбо",
            type=["xlsx"],
            key="prod_combo",
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
            use_container_width=True,
        ):
            with st.spinner("⏳ Формирую отчет..."):
                try:
                    # Сброс указателя файла перед передачей в логику
                    files_state["main"].seek(0)
                    files_state["combo"].seek(0)

                    # Вызов чистой бизнес-логики из report/prodykt.py
                    excel_buffer = generator_func(
                        files_state["main"],
                        files_state["combo"],
                    )
                    st.success("✅ Отчет сформирован!")

                    # 🎈 Пастельные шарики при следующем рендере
                    if celebrate_report_success is not None:
                        celebrate_report_success()

                    st.download_button(
                        label="📥 Скачать Итоговый_отчет.xlsx",
                        data=excel_buffer,
                        file_name="Итоговый_отчет_Продукт.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
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