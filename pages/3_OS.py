import streamlit as st
import pandas as pd
import numpy as np
import re
import io
from datetime import datetime, timedelta, time
import xlsxwriter

# Импорты из вашего проекта (раскомментируйте при необходимости)
# from config.brand import BRAND_COLORS, FONT_FAMILY
# from components import render_header, render_footer

# --- НАСТРОЙКИ И КОНСТАНТЫ ---
st.set_page_config(page_title="ОС - Отчет", layout="wide", page_icon="💬")

# Заглушка для цветов, если config не подгружен
BRAND_COLORS = {
    "primary": "#2C3E50", "secondary": "#3498DB", "accent": "#F1C40F",
    "rating_bad": "#C0392B", "rating_good": "#27AE60",
    "bg_light": "#F8F9FA"
}

MSK_OFFSET = timedelta(hours=3)
WORK_START = 11  # 11:00 МСК
WORK_END = 23    # 23:00 МСК

# --- ФУНКЦИИ ОБРАБОТКИ ДАННЫХ ---

def parse_chat_times(chat_text, ticket_created_at):
    """
    Извлекает время первого ответа ЖИВОГО оператора после создания тикета.
    ticket_created_at - время создания тикета из колонки 'Дата отзыва'
    """
    if pd.isna(chat_text) or pd.isna(ticket_created_at):
        return None
    
    # Паттерн для поиска строк с ролями и временем
    # Формат: "Роль (2026-07-26 20:22:25): текст"
    role_pattern = re.compile(
        r'^([А-Яа-яA-Za-zЁё\s\d\-\(\)]+?)\s*\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\):',
        re.MULTILINE
    )
    
    matches = role_pattern.findall(str(chat_text))
    if not matches:
        return None
    
    # Роли, которые НЕ являются живыми операторами
    non_operator_roles = ['Бот', 'Системный пользователь', 'Системный']
    
    for role, time_str in matches:
        role_clean = role.strip()
        
        # Пропускаем не-операторов
        if any(non_op in role_clean for non_op in non_operator_roles):
            continue
        
        try:
            msg_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        except:
            continue
        
        # Ответ должен быть ПОСЛЕ создания тикета
        if msg_time > ticket_created_at:
            return msg_time
    
    return None


def categorize_complaint(text, reason):
    """Категоризация жалоб по ключевым словам."""
    text = str(text).lower() + " " + str(reason).lower()
    
    if any(w in text for w in ['опоздание', 'задержка', 'долго', 'где курьер', 'не везут', 'холодная', 'нарушение сроков']):
        return 'Опоздание / Логистика'
    if any(w in text for w in ['перепутали', 'не положили', 'забыли', 'не тот', 'недоложили', 'нет в заказе', 'не ту пиццу']):
        return 'Комплектация (Перепутали/Забыли)'
    if any(w in text for w in ['волос', 'проволока', 'мусор', 'сырое', 'отравлен', 'инородн', 'мутант']):
        return 'Качество / Инородные предметы'
    if any(w in text for w in ['груб', 'хам', 'невежл', 'хамили', 'не берут трубку', 'не отвечает']):
        return 'Сервис / Грубость'
    if any(w in text for w in ['промокод', 'бонус', 'акция', 'скидка', 'приложение', 'сайт', 'не работает', 'ошибка', 'день рождения', 'рассылк']):
        return 'IT / Сайт / Промокоды'
    if any(w in text for w in ['возврат', 'деньги', 'списал', 'не вернули']):
        return 'Возврат средств'
    if any(w in text for w in ['статус заказа', 'не попал в систему', 'не отображается']):
        return 'Статус заказа / IT'
    return 'Другое / Запрос'


def analyze_bot_fails(df):
    """Поиск тикетов, где бот ответил невпопад или клиент требовал оператора."""
    bot_fails = []
    fail_keywords_bot = ['запуталась', 'не поняла', 'упс, кажется', 'пошло не так', 'не совсем поняла']
    client_demand = ['оператор', 'позови', 'соедини', 'живого', 'человек', 'позови оператора']
    
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
    st.markdown(
        f"<h1 style='text-align: center; color: {BRAND_COLORS['primary']}'>"
        f"💬 Отчет по работе Отдела Обратной Связи (ОС)</h1>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # 1. ЗАГРУЗКА ДАННЫХ
    st.sidebar.header("📂 Загрузка данных")
    uploaded_file = st.sidebar.file_uploader(
        "Загрузите выгрузку тикетов (Excel/CSV)",
        type=['xlsx', 'csv']
    )
    
    if not uploaded_file:
        st.info("👈 Пожалуйста, загрузите файл с выгрузкой обращений в боковой панели, чтобы начать анализ.")
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
    
    available_cities = df['Город'].dropna().unique().tolist() if 'Город' in df.columns else []
    default_cities = [c for c in ['Санкт-Петербург', 'Тюмень'] if c in available_cities]
    
    cities = st.sidebar.multiselect(
        "Выберите город/регион:",
        options=available_cities,
        default=default_cities if default_cities else available_cities[:3]
    )
    df_filtered = df[df['Город'].isin(cities)] if cities else df

    valid_dates = df_filtered['Дата отзыва'].dropna()
    if not valid_dates.empty:
        st.success(
            f"✅ Загружено тикетов: **{len(df_filtered)}** | "
            f"Период: **{valid_dates.min().date()}** - **{valid_dates.max().date()}**"
        )
    else:
        st.success(f"✅ Загружено тикетов: **{len(df_filtered)}**")

    # Вкладки
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 SLA и Операторы",
        "🍕 Жалобы и Рестораны",
        "🤖 Анализ Чат-бота",
        "📥 Экспорт в Excel"
    ])

    # ==========================================
    # ВКЛАДКА 1: SLA И ОПЕРАТОРЫ
    # ==========================================
    with tab1:
        st.subheader("Скорость ответа и загрузка операторов")
        st.caption(
            "⏱ Учитывается только рабочее время (11:00 - 23:00 МСК). "
            "Вы можете исключить тикеты из расчета, если задержка произошла не по вине ОС."
        )
        
        # Расчет SLA
        sla_data = []
        for idx, row in df_filtered.iterrows():
            ticket_time = row.get('Дата отзыва')
            if pd.isna(ticket_time):
                continue
            
            operator_time = parse_chat_times(
                row.get('Первичное сообщение'),
                ticket_time
            )
            
            if operator_time:
                # Проверяем, что тикет создан в рабочее время (МСК)
                ticket_hour_msk = (ticket_time + MSK_OFFSET).hour
                
                if WORK_START <= ticket_hour_msk < WORK_END:
                    diff_seconds = (operator_time - ticket_time).total_seconds()
                    diff_mins = diff_seconds / 60
                    
                    # Флаг подозрительного времени (< 1 минуты)
                    is_suspicious = diff_mins < 1
                    
                    sla_data.append({
                        '№ Тикета': row.get('Номер обращения'),
                        'Ресторан': row.get('Ресторан', ''),
                        'Исполнитель': row.get('Исполнитель'),
                        'Время создания': ticket_time.strftime('%H:%M:%S'),
                        'Время ответа': operator_time.strftime('%H:%M:%S'),
                        'Время ответа (мин)': round(diff_mins, 1),
                        'Превышение 30 мин': diff_mins > 30,
                        '⚠️ Подозрительный': is_suspicious,
                        'Исключить из SLA': is_suspicious  # автоисключение аномалий
                    })
        
        df_sla = pd.DataFrame(sla_data)
        
        if not df_sla.empty:
            # Интерактивная таблица для исключений
            st.markdown("##### Таблица времени ответа (отметьте галочками тикеты для исключения)")
            edited_sla = st.data_editor(
                df_sla,
                column_config={
                    "Исключить из SLA": st.column_config.CheckboxColumn(
                        "Исключить?",
                        help="Отметьте, если задержка не по вине оператора",
                        default=False
                    ),
                    "Время ответа (мин)": st.column_config.NumberColumn(format="%.1f")
                },
                disabled=["№ Тикета", "Ресторан", "Исполнитель", "Время создания",
                          "Время ответа", "Время ответа (мин)", "Превышение 30 мин", "⚠️ Подозрительный"],
                hide_index=True,
                use_container_width=True
            )
            
            # Пересчет метрик с учетом исключений
            valid_sla = edited_sla[~edited_sla['Исключить из SLA']]
            
            col1, col2, col3, col4 = st.columns(4)
            avg_time = valid_sla['Время ответа (мин)'].mean() if len(valid_sla) > 0 else 0
            sla_breach = (valid_sla['Превышение 30 мин'].sum() / len(valid_sla) * 100) if len(valid_sla) > 0 else 0
            
            col1.metric("Среднее время ответа", f"{avg_time:.1f} мин")
            col2.metric("Тикетов > 30 мин", f"{sla_breach:.1f}%",
                        delta=f"{int(valid_sla['Превышение 30 мин'].sum())} шт.")
            col3.metric("Исключено из SLA", f"{int(edited_sla['Исключить из SLA'].sum())} шт.")
            col4.metric("Подозрительных", f"{int(edited_sla['⚠️ Подозрительный'].sum())} шт.")
            
            st.markdown("##### Загрузка по операторам")
            if 'Исполнитель' in valid_sla.columns:
                op_stats = valid_sla.groupby('Исполнитель').agg(
                    Тикетов=('№ Тикета', 'count'),
                    Среднее_время=('Время ответа (мин)', 'mean')
                ).round(1).sort_values(by='Тикетов', ascending=False)
                st.bar_chart(op_stats['Тикетов'])
                
                st.dataframe(op_stats, use_container_width=True)
        else:
            st.warning(
                "Не удалось распарсить время ответа из логов. "
                "Проверьте формат столбца 'Первичное сообщение'."
            )

    # ==========================================
    # ВКЛАДКА 2: ЖАЛОБЫ И РЕСТОРАНЫ
    # ==========================================
    with tab2:
        st.subheader("Аналитика жалоб по категориям и ресторанам")
        
        # Категоризация
        df_filtered = df_filtered.copy()
        df_filtered['Категория жалобы'] = df_filtered.apply(
            lambda x: categorize_complaint(
                x.get('Первичное сообщение', ''),
                x.get('Причина обращения', '')
            ),
            axis=1
        )
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("##### Топ категорий жалоб")
            cat_counts = df_filtered['Категория жалобы'].value_counts()
            st.bar_chart(cat_counts)
            
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
        st.caption(
            "Тикеты, где бот ответил невпопад, зациклился "
            "или клиент сразу потребовал живого оператора."
        )
        
        bot_fails_df = analyze_bot_fails(df_filtered)
        
        if not bot_fails_df.empty:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("Всего сбоев бота", len(bot_fails_df))
                st.dataframe(
                    bot_fails_df['Тип ошибки бота'].value_counts(),
                    use_container_width=True
                )
            with col2:
                st.dataframe(bot_fails_df, use_container_width=True, hide_index=True)
        else:
            st.success("Критических сбоев бота не обнаружено (или формат логов отличается).")

    # ==========================================
    # ВКЛАДКА 4: ЭКСПОРТ В EXCEL
    # ==========================================
    with tab4:
        st.subheader("Генерация сводного Excel-отчета")
        st.info(
            "Отчет будет содержать 3 листа: SLA по операторам, "
            "Жалобы по ресторанам, Ошибки бота. С диаграммами!"
        )
        
        if st.button("📥 Сформировать и скачать Excel", type="primary"):
            with st.spinner("Формируем отчет..."):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    workbook = writer.book
                    
                    # Стили
                    header_fmt = workbook.add_format({
                        'bold': True, 'bg_color': '#2C3E50',
                        'font_color': 'white', 'border': 1
                    })
                    
                    # Лист 1: SLA
                    if not df_sla.empty:
                        df_sla.to_excel(writer, sheet_name='SLA Операторов', index=False)
                        ws1 = writer.sheets['SLA Операторов']
                        for col_num, value in enumerate(df_sla.columns.values):
                            ws1.write(0, col_num, value, header_fmt)
                        ws1.set_column('A:A', 15)
                        ws1.set_column('B:B', 25)
                        ws1.set_column('C:C', 25)
                        ws1.set_column('D:D', 15)
                        ws1.set_column('E:E', 15)
                        ws1.set_column('F:F', 18)
                    
                    # Лист 2: Жалобы
                    pivot_reset = pivot.reset_index()
                    pivot_reset.to_excel(writer, sheet_name='Жалобы по ресторанам', index=False)
                    ws2 = writer.sheets['Жалобы по ресторанам']
                    for col_num, value in enumerate(pivot_reset.columns.values):
                        ws2.write(0, col_num, value, header_fmt)
                    
                    # Диаграмма для Листа 2 (ИСПРАВЛЕННАЯ ВЕРСИЯ)
                    if len(pivot_reset) > 0 and len(pivot_reset.columns) > 1:
                        chart = workbook.add_chart({'type': 'bar stacked'})
                        
                        # Получаем названия колонок (кроме 'Ресторан' и 'ИТОГО')
                        cols = [c for c in pivot_reset.columns if c not in ['Ресторан', 'ИТОГО']]
                        
                        # Строим диаграмму
                        for i, col in enumerate(cols):
                            col_idx = list(pivot_reset.columns).index(col)
                            num_rows = len(pivot_reset)
                            
                            # Правильный формат ссылок для xlsxwriter
                            chart.add_series({
                                'name': str(col),
                                'categories': ['Жалобы по ресторанам', 1, 0, num_rows, 0],
                                'values': ['Жалобы по ресторанам', 1, col_idx, num_rows, col_idx],
                            })
                        
                        chart.set_title({'name': 'Структура жалоб по ресторанам'})
                        chart.set_x_axis({'name': 'Количество жалоб'})
                        chart.set_y_axis({'name': 'Ресторан'})
                        chart.set_size({'width': 720, 'height': 500})
                        ws2.insert_chart('H2', chart)

                    # Лист 3: Бот
                    if not bot_fails_df.empty:
                        bot_fails_df.to_excel(writer, sheet_name='Ошибки Бота', index=False)
                        ws3 = writer.sheets['Ошибки Бота']
                        for col_num, value in enumerate(bot_fails_df.columns.values):
                            ws3.write(0, col_num, value, header_fmt)
                        ws3.set_column('A:A', 15)
                        ws3.set_column('B:B', 20)
                        ws3.set_column('C:C', 25)
                        ws3.set_column('D:D', 50)  # Ширина столбца с сутью
                        ws3.set_column('E:E', 20)

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
