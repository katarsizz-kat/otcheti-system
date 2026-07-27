import streamlit as st
import pandas as pd
import numpy as np
import re
import io
from datetime import datetime, timedelta, time
import xlsxwriter

# Импорты из вашего проекта (раскомментируйте, когда будете запускать в среде)
# from config.brand import BRAND_COLORS, FONT_FAMILY
# from components import render_header, render_footer

# --- НАСТРОЙКИ И КОНСТАНТЫ ---
st.set_page_config(page_title="ОС - Отчет", layout="wide", page_icon="💬")

# Заглушка для цветов, если config не подгружен
BRAND_COLORS = {
    "primary": "#2C3E50", "secondary": "#3498DB", "accent": "#F1C40F",
    "rating_bad": "#C0392B", "rating_good": "#27AE60"
}

MSK_OFFSET = timedelta(hours=3)
WORK_START = 11 # 11:00
WORK_END = 23   # 23:00

# --- ФУНКЦИИ ОБРАБОТКИ ДАННЫХ ---

def parse_chat_times(chat_text):
    """Извлекает время первого сообщения клиента и первого ответа оператора из лога."""
    if pd.isna(chat_text): return None, None
    
    # Ищем все таймстампы в формате YYYY-MM-DD HH:MM:SS
    timestamps = re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', str(chat_text))
    if not timestamps: return None, None
    
    client_time = None
    operator_time = None
    
    lines = str(chat_text).split('\n')
    for line in lines:
        ts_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if ts_match:
            dt = datetime.strptime(ts_match.group(1), '%Y-%m-%d %H:%M:%S')
            if 'Клиент' in line and client_time is None:
                client_time = dt
            elif ('Бот' not in line and 'Системный' not in line and operator_time is None and client_time is not None):
                operator_time = dt
                break
                
    return client_time, operator_time

def categorize_complaint(text, reason):
    """Категоризация жалоб по ключевым словам."""
    text = str(text).lower() + " " + str(reason).lower()
    
    if any(w in text for w in ['опоздание', 'задержка', 'долго', 'где курьер', 'не везут', 'холодная']):
        return 'Опоздание / Логистика'
    if any(w in text for w in ['перепутали', 'не положили', 'забыли', 'не тот', 'недоложили', 'нет в заказе']):
        return 'Комплектация (Перепутали/Забыли)'
    if any(w in text for w in ['волос', 'проволока', 'мусор', 'сырое', 'отравлен', 'инородн']):
        return 'Качество / Инородные предметы'
    if any(w in text for w in ['груб', 'хам', 'невежл', 'хамили']):
        return 'Сервис / Грубость'
    if any(w in text for w in ['промокод', 'бонус', 'акция', 'скидка', 'приложение', 'сайт', 'не работает', 'ошибка']):
        return 'IT / Сайт / Промокоды'
    if any(w in text for w in ['возврат', 'деньги']):
        return 'Возврат средств'
    return 'Другое / Запрос'

def analyze_bot_fails(df):
    """Поиск тикетов, где бот ответил невпопад или клиент требовал оператора."""
    bot_fails = []
    fail_keywords_bot = ['запуталась', 'не поняла', 'упс, кажется', 'пошло не так']
    client_demand = ['оператор', 'позови', 'соедини', 'живого', 'человек']
    
    for idx, row in df.iterrows():
        text = str(row.get('Первичное сообщение', '')).lower()
        ticket_id = row.get('Номер обращения', '')
        date = row.get('Дата отзыва', '')
        
        # Если бот тупил ИЛИ клиент сразу просит оператора
        is_bot_fail = any(k in text for k in fail_keywords_bot)
        is_demand = any(k in text for k in client_demand)
        
        if is_bot_fail or is_demand:
            # Краткая суть (первые 100 символов сообщения клиента)
            client_msgs = re.findall(r'Клиент.*?:\s*(.*?)(?:\n|Бот|$)', str(row.get('Первичное сообщение', '')), re.DOTALL)
            summary = client_msgs[0].strip()[:100] if client_msgs else "Нет текста"
            
            bot_fails.append({
                '№ Обращения': ticket_id,
                'Дата': date,
                'Ресторан': row.get('Ресторан', ''),
                'Суть обращения': summary,
                'Тип ошибки бота': 'Требовал оператора' if is_demand else 'Бот не понял'
            })
    return pd.DataFrame(bot_fails)

# --- UI СТРАНИЦЫ ---

def main():
    # render_header("Отчет по работе Отдела Обратной Связи", "💬")
    st.markdown(f"<h1 style='text-align: center; color: {BRAND_COLORS['primary']}'>💬 Отчет по работе Отдела Обратной Связи (ОС)</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # 1. ЗАГРУЗКА ДАННЫХ
    st.sidebar.header("📂 Загрузка данных")
    uploaded_file = st.sidebar.file_uploader("Загрузите выгрузку тикетов (Excel/CSV)", type=['xlsx', 'csv'])
    
    if not uploaded_file:
        st.info("👈 Пожалуйста, загрузите файл с выгрузкой обращений в боковой панели, чтобы начать анализ.")
        st.image("https://media.tenor.com/8c68Xz-0_8YAAAAi/papa-johns-pizza.gif", width=300) # Заглушка
        return

    # Чтение файла
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Ошибка чтения файла: {e}")
        return

    # Базовая очистка
    df['Дата отзыва'] = pd.to_datetime(df['Дата отзыва'], errors='coerce')
    
    # Фильтры
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Фильтры")
    cities = st.sidebar.multiselect("Выберите город/регион:", options=df['Город'].dropna().unique(), default=['Санкт-Петербург', 'Тюмень'])
    df_filtered = df[df['Город'].isin(cities)] if cities else df

    st.success(f"✅ Загружено тикетов: **{len(df_filtered)}** | Период: **{df_filtered['Дата отзыва'].min().date()}** - **{df_filtered['Дата отзыва'].max().date()}**")

    # Вкладки
    tab1, tab2, tab3, tab4 = st.tabs(["📊 SLA и Операторы", "🍕 Жалобы и Рестораны", "🤖 Анализ Чат-бота", "📥 Экспорт в Excel"])

    # ==========================================
    # ВКЛАДКА 1: SLA И ОПЕРАТОРЫ
    # ==========================================
    with tab1:
        st.subheader("Скорость ответа и загрузка операторов")
        st.caption("⏱ Учитывается только рабочее время (11:00 - 23:00 МСК). Вы можете исключить тикеты из расчета, если задержка произошла не по вине ОС.")
        
        # Расчет SLA
        sla_data = []
        for idx, row in df_filtered.iterrows():
            c_time, o_time = parse_chat_times(row.get('Первичное сообщение'))
            if c_time and o_time:
                # Переводим в МСК для проверки рабочего времени
                c_time_msk = c_time + MSK_OFFSET
                if WORK_START <= c_time_msk.hour < WORK_END:
                    diff_mins = (o_time - c_time).total_seconds() / 60
                    sla_data.append({
                        '№ Тикета': row.get('Номер обращения'),
                        'Исполнитель': row.get('Исполнитель'),
                        'Время ответа (мин)': round(diff_mins, 1),
                        'Превышение 30 мин': diff_mins > 30,
                        'Исключить из SLA': False # По умолчанию False
                    })
        
        df_sla = pd.DataFrame(sla_data)
        
        if not df_sla.empty:
            # Интерактивная таблица для исключений
            st.markdown("##### Таблица времени ответа (отметьте галочками тикеты для исключения)")
            edited_sla = st.data_editor(
                df_sla,
                column_config={
                    "Исключить из SLA": st.column_config.CheckboxColumn("Исключить?", help="Отметьте, если задержка не по вине оператора", default=False),
                    "Время ответа (мин)": st.column_config.NumberColumn(format="%.1f")
                },
                disabled=["№ Тикета", "Исполнитель", "Время ответа (мин)", "Превышение 30 мин"],
                hide_index=True,
                use_container_width=True
            )
            
            # Пересчет метрик с учетом исключений
            valid_sla = edited_sla[~edited_sla['Исключить из SLA']]
            
            col1, col2, col3 = st.columns(3)
            avg_time = valid_sla['Время ответа (мин)'].mean()
            sla_breach = (valid_sla['Превышение 30 мин'].sum() / len(valid_sla)) * 100 if len(valid_sla) > 0 else 0
            
            col1.metric("Среднее время ответа", f"{avg_time:.1f} мин")
            col2.metric("Тикетов > 30 мин", f"{sla_breach:.1f}%", delta=f"{valid_sla['Превышение 30 мин'].sum()} шт.")
            col3.metric("Исключено из SLA", f"{edited_sla['Исключить из SLA'].sum()} шт.")
            
            st.markdown("##### Загрузка по операторам")
            op_stats = valid_sla.groupby('Исполнитель').agg(
                Тикетов=('№ Тикета', 'count'),
                Среднее_время=('Время ответа (мин)', 'mean')
            ).round(1).sort_values(by='Тикетов', ascending=False)
            st.bar_chart(op_stats['Тикетов'])
        else:
            st.warning("Не удалось распарсить время ответа из логов. Проверьте формат столбца 'Первичное сообщение'.")

    # ==========================================
    # ВКЛАДКА 2: ЖАЛОБЫ И РЕСТОРАНЫ
    # ==========================================
    with tab2:
        st.subheader("Аналитика жалоб по категориям и ресторанам")
        
        # Категоризация
        df_filtered['Категория жалобы'] = df_filtered.apply(lambda x: categorize_complaint(x.get('Первичное сообщение', ''), x.get('Причина обращения', '')), axis=1)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("##### Топ категорий жалоб")
            cat_counts = df_filtered['Категория жалобы'].value_counts()
            st.bar_chart(cat_counts, color=BRAND_COLORS['rating_bad'])
            
        with col2:
            st.markdown("##### Сводная таблица: Ресторан × Категория")
            pivot = pd.pivot_table(
                df_filtered, 
                index='Ресторан', 
                columns='Категория жалобы', 
                aggfunc='size', 
                fill_value=0
            )
            pivot['ИТОГО'] = pivot.sum(axis=1)
            pivot = pivot.sort_values(by='ИТОГО', ascending=False)
            st.dataframe(pivot, use_container_width=True)

    # ==========================================
    # ВКЛАДКА 3: АНАЛИЗ ЧАТ-БОТА
    # ==========================================
    with tab3:
        st.subheader("Ошибки чат-бота и запросы оператора")
        st.caption("Тикеты, где бот ответил невпопад, зациклился или клиент сразу потребовал живого оператора.")
        
        bot_fails_df = analyze_bot_fails(df_filtered)
        
        if not bot_fails_df.empty:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("Всего сбоев бота", len(bot_fails_df))
                st.dataframe(bot_fails_df['Тип ошибки бота'].value_counts(), use_container_width=True)
            with col2:
                st.dataframe(bot_fails_df, use_container_width=True, hide_index=True)
        else:
            st.success("Критических сбоев бота не обнаружено (или формат логов отличается).")

    # ==========================================
    # ВКЛАДКА 4: ЭКСПОРТ В EXCEL
    # ==========================================
    with tab4:
        st.subheader("Генерация сводного Excel-отчета")
        st.info("Отчет будет содержать 3 листа: SLA по операторам, Жалобы по ресторанам, Ошибки бота. С диаграммами!")
        
        if st.button("📥 Сформировать и скачать Excel", type="primary"):
            with st.spinner("Формируем отчет..."):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    workbook = writer.book
                    
                    # Стили
                    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#2C3E50', 'font_color': 'white', 'border': 1})
                    
                    # Лист 1: SLA
                    if not df_sla.empty:
                        df_sla.to_excel(writer, sheet_name='SLA Операторов', index=False)
                        ws1 = writer.sheets['SLA Операторов']
                        for col_num, value in enumerate(df_sla.columns.values):
                            ws1.write(0, col_num, value, header_fmt)
                    
                    # Лист 2: Жалобы
                    pivot.reset_index().to_excel(writer, sheet_name='Жалобы по ресторанам', index=False)
                    ws2 = writer.sheets['Жалобы по ресторанам']
                    for col_num, value in enumerate(pivot.reset_index().columns.values):
                        ws2.write(0, col_num, value, header_fmt)
                        
                    # Диаграмма для Листа 2
                    if len(pivot) > 0:
                        chart = workbook.add_chart({'type': 'bar stacked'})
                        cols = [c for c in pivot.columns if c != 'ИТОГО']
                        for i, col in enumerate(cols):
                            chart.add_series({
                                'name': col,
                                'categories': ['Жалобы по ресторанам', 1, 0, len(pivot), 0],
                                'values': ['Жалобы по ресторанам', 1, i+1, len(pivot), i+1],
                            })
                        chart.set_title({'name': 'Структура жалоб по ресторанам'})
                        ws2.insert_chart('H2', chart)

                    # Лист 3: Бот
                    if not bot_fails_df.empty:
                        bot_fails_df.to_excel(writer, sheet_name='Ошибки Бота', index=False)
                        ws3 = writer.sheets['Ошибки Бота']
                        for col_num, value in enumerate(bot_fails_df.columns.values):
                            ws3.write(0, col_num, value, header_fmt)
                        ws3.set_column('D:D', 50) # Ширина столбца с сутью

                output.seek(0)
                st.download_button(
                    label="💾 Скачать готовый отчет (.xlsx)",
                    data=output,
                    file_name="OS_Report_Analytics.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.balloons()

if __name__ == "__main__":
    main()
