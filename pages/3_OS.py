import streamlit as st
import pandas as pd
import numpy as np
import re
import io
from datetime import datetime, timedelta, time, date
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

# Фиксированный порядок ресторанов Тюмени
TYUMEN_ORDER = ['Тюмень №2 – Орджоникидзе', 'Тюмень №3 – Мельникайте']

# --- ФУНКЦИИ ОБРАБОТКИ ДАННЫХ ---

def extract_restaurant_number(restaurant_name):
    """Извлекает номер ресторана для сортировки."""
    if pd.isna(restaurant_name):
        return 9999
    
    match = re.search(r'№\s*(\d+)', str(restaurant_name))
    if match:
        return int(match.group(1))
    return 9999


def sort_restaurants(df, city_column='Город', restaurant_column='Ресторан'):
    """Сортирует рестораны: сначала СПб (по номеру), потом Тюмень (фиксированный порядок)."""
    df_sorted = df.copy()
    
    def get_sort_key(row):
        city = str(row.get(city_column, ''))
        restaurant = str(row.get(restaurant_column, ''))
        
        # Сначала Санкт-Петербург
        if 'Санкт-Петербург' in city:
            num = extract_restaurant_number(restaurant)
            return (0, num, restaurant)
        
        # Потом Тюмень
        elif 'Тюмень' in city:
            try:
                order_idx = TYUMEN_ORDER.index(restaurant)
                return (1, order_idx, restaurant)
            except ValueError:
                return (1, 9999, restaurant)
        
        # Остальные города
        else:
            num = extract_restaurant_number(restaurant)
            return (2, num, restaurant)
    
    df_sorted['_sort_key'] = df_sorted.apply(get_sort_key, axis=1)
    df_sorted = df_sorted.sort_values('_sort_key')
    df_sorted = df_sorted.drop('_sort_key', axis=1)
    return df_sorted


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
        date_val = row.get('Дата отзыва', '')
        
        is_bot_fail = any(k in text for k in fail_keywords_bot)
        is_demand = any(k in text for k in client_demand)
        
        if is_bot_fail or is_demand:
            client_msgs = re.findall(r'Клиент.*?:\s*(.*?)(?:\n|Бот|$)', str(row.get('Первичное сообщение', '')), re.DOTALL)
            summary = client_msgs[0].strip()[:100] if client_msgs else "Нет текста"
            
            bot_fails.append({
                '№ Обращения': ticket_id,
                'Дата': date_val,
                'Ресторан': row.get('Ресторан', ''),
                'Суть обращения': summary,
                'Тип ошибки бота': 'Требовал оператора' if is_demand else 'Бот не понял'
            })
    return pd.DataFrame(bot_fails)


def get_hour_interval(hour):
    """Возвращает строковое представление часового интервала."""
    intervals = [
        (0, 2, '00:00-02:00'),
        (2, 8, '02:00-08:00'),
        (8, 9, '08:00'),
        (9, 10, '09:00'),
        (10, 11, '10:00'),
        (11, 12, '11:00'),
        (12, 16, '12:00-16:00'),
        (16, 17, '16:00'),
        (17, 18, '17:00'),
        (18, 19, '18:00'),
        (19, 20, '19:00'),
        (20, 21, '20:00'),
        (21, 22, '21:00'),
        (22, 23, '22:00'),
        (23, 24, '23:00-00:00')
    ]
    
    for start, end, label in intervals:
        if start <= hour < end:
            return label
    return 'Другое'


def get_interval_hours(interval_label):
    """Возвращает количество часов в интервале."""
    if '-' in interval_label:
        parts = interval_label.split('-')
        start = int(parts[0].split(':')[0])
        end = int(parts[1].split(':')[0])
        if end == 0:  # 23:00-00:00
            return 1
        return end - start
    return 1


def get_weekday_name(date_obj):
    """Возвращает название дня недели."""
    weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    return weekdays[date_obj.weekday()]


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
    
    # Фильтр по городам
    available_cities = df['Город'].dropna().unique().tolist() if 'Город' in df.columns else []
    default_cities = [c for c in ['Санкт-Петербург', 'Тюмень'] if c in available_cities]
    
    cities = st.sidebar.multiselect(
        "Выберите город/регион:",
        options=available_cities,
        default=default_cities if default_cities else available_cities[:3]
    )
    df_filtered = df[df['Город'].isin(cities)] if cities else df
    
    # Фильтр по датам
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Фильтр по датам")
    
    date_filter_type = st.sidebar.radio(
        "Тип фильтра:",
        ["Интервал дат", "Отдельные даты"],
        index=0
    )
    
    valid_dates = df_filtered['Дата отзыва'].dropna()
    
    if date_filter_type == "Интервал дат":
        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
            
            date_range = st.sidebar.date_input(
                "Выберите период:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                df_filtered = df_filtered[
                    (df_filtered['Дата отзыва'].dt.date >= start_date) &
                    (df_filtered['Дата отзыва'].dt.date <= end_date)
                ]
    else:  # Отдельные даты
        if not valid_dates.empty:
            unique_dates = sorted(valid_dates.dt.date.unique(), reverse=True)
            selected_dates = st.sidebar.multiselect(
                "Выберите даты:",
                options=unique_dates,
                default=unique_dates[:5] if len(unique_dates) >= 5 else unique_dates
            )
            
            if selected_dates:
                df_filtered = df_filtered[
                    df_filtered['Дата отзыва'].dt.date.isin(selected_dates)
                ]

    # Обновляем информацию о периоде
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
        "📊 Статистика операторов",
        "🍕 Жалобы и Рестораны",
        "🤖 Анализ Чат-бота",
        "📥 Экспорт в Excel"
    ])

    # ==========================================
    # ВКЛАДКА 1: СТАТИСТИКА ОПЕРАТОРОВ
    # ==========================================
    with tab1:
        st.subheader("Загрузка операторов и распределение по часам")
        st.caption("⏱ Учитываются только живые операторы (исключён 'Системный пользователь'). Время переведено в МСК (+3 часа).")
        
        # Исключаем системного пользователя
        df_operators = df_filtered[df_filtered['Исполнитель'] != 'Системный пользователь'].copy()
        df_operators = df_operators[df_operators['Исполнитель'].notna()]
        
        if not df_operators.empty:
            # Добавляем МСК время
            df_operators['Дата_МСК'] = df_operators['Дата отзыва'] + MSK_OFFSET
            df_operators['Дата_только'] = df_operators['Дата_МСК'].dt.date
            df_operators['Час_МСК'] = df_operators['Дата_МСК'].dt.hour
            
            # Таблица 1: Статистика по операторам
            st.markdown("##### 📋 Статистика по операторам")
            
            operator_stats = []
            for operator in df_operators['Исполнитель'].unique():
                op_df = df_operators[df_operators['Исполнитель'] == operator]
                total_tickets = len(op_df)
                # Используем дату создания обращения для подсчёта рабочих дней
                unique_days = op_df['Дата_только'].nunique()
                avg_per_day = total_tickets / unique_days if unique_days > 0 else 0
                
                operator_stats.append({
                    'Оператор': operator,
                    'Всего обращений': total_tickets,
                    'Рабочих дней': unique_days,
                    'Среднее в день': round(avg_per_day, 2)
                })
            
            df_operator_stats = pd.DataFrame(operator_stats)
            df_operator_stats = df_operator_stats.sort_values('Всего обращений', ascending=False)
            
            st.dataframe(df_operator_stats, use_container_width=True, hide_index=True)
            
            # Проверка совместной работы операторов
            st.markdown("##### 👥 Совместная работа операторов")
            st.caption("Дни, когда обращения обрабатывали несколько операторов одновременно")
            
            day_operators = df_operators.groupby('Дата_только')['Исполнитель'].apply(lambda x: list(set(x))).reset_index()
            day_operators['Количество операторов'] = day_operators['Исполнитель'].apply(len)
            multi_op_days = day_operators[day_operators['Количество операторов'] > 1]
            
            if not multi_op_days.empty:
                multi_op_display = multi_op_days.copy()
                multi_op_display['Операторы'] = multi_op_display['Исполнитель'].apply(lambda x: ', '.join(sorted(x)))
                multi_op_display = multi_op_display[['Дата_только', 'Количество операторов', 'Операторы']]
                multi_op_display = multi_op_display.sort_values('Дата_только', ascending=False)
                st.dataframe(multi_op_display, use_container_width=True, hide_index=True)
            else:
                st.info("Каждый день обращения обрабатывал только один оператор.")
            
            # Таблица 2: Распределение по часовым интервалам
            st.markdown("##### 🕐 Распределение обращений по часам (МСК)")
            
            df_operators['Часовой интервал'] = df_operators['Час_МСК'].apply(get_hour_interval)
            
            interval_order = [
                '00:00-02:00', '02:00-08:00', '08:00', '09:00', '10:00', '11:00',
                '12:00-16:00', '16:00', '17:00', '18:00', '19:00', '20:00',
                '21:00', '22:00', '23:00-00:00'
            ]
            
            hour_stats = df_operators.groupby('Часовой интервал').size().reset_index(name='Обращений')
            hour_stats['Обращений в час'] = hour_stats.apply(
                lambda row: round(row['Обращений'] / get_interval_hours(row['Часовой интервал']), 2),
                axis=1
            )
            
            hour_stats['_sort'] = hour_stats['Часовой интервал'].apply(lambda x: interval_order.index(x) if x in interval_order else 999)
            hour_stats = hour_stats.sort_values('_sort').drop('_sort', axis=1)
            
            st.dataframe(hour_stats, use_container_width=True, hide_index=True)
            
            st.markdown("##### 📈 Визуализация нагрузки по часам")
            chart_data = hour_stats.set_index('Часовой интервал')[['Обращений в час']]
            st.bar_chart(chart_data)
        else:
            st.warning("Нет данных по операторам (все тикеты обработаны системным пользователем или не распределены).")

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
            
            # Сортировка: сначала СПб, потом Тюмень
            pivot = sort_restaurants(pivot.reset_index(), 'Город' if 'Город' in pivot.columns else 'Ресторан', 'Ресторан')
            pivot = pivot.set_index('Ресторан')
            
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
            "Отчет будет содержать 5 листов: Статистика операторов, Часовая нагрузка, "
            "Статистика по дням, Жалобы по ресторанам, Ошибки бота. С диаграммами!"
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
                    
                    # Лист 1: Статистика операторов
                    if not df_operators.empty:
                        df_operator_stats.to_excel(writer, sheet_name='Статистика операторов', index=False)
                        ws1 = writer.sheets['Статистика операторов']
                        for col_num, value in enumerate(df_operator_stats.columns.values):
                            ws1.write(0, col_num, value, header_fmt)
                        ws1.set_column('A:A', 30)
                        ws1.set_column('B:D', 18)
                    
                    # Лист 2: Часовая нагрузка
                    if not df_operators.empty:
                        hour_stats.to_excel(writer, sheet_name='Часовая нагрузка', index=False)
                        ws2 = writer.sheets['Часовая нагрузка']
                        for col_num, value in enumerate(hour_stats.columns.values):
                            ws2.write(0, col_num, value, header_fmt)
                        ws2.set_column('A:A', 15)
                        ws2.set_column('B:C', 18)
                        
                        # Диаграмма по часам
                        chart = workbook.add_chart({'type': 'column'})
                        chart.add_series({
                            'name': 'Обращений в час',
                            'categories': ['Часовая нагрузка', 1, 0, len(hour_stats), 0],
                            'values': ['Часовая нагрузка', 1, 2, len(hour_stats), 2],
                        })
                        chart.set_title({'name': 'Нагрузка по часам (МСК)'})
                        chart.set_x_axis({'name': 'Часовой интервал'})
                        chart.set_y_axis({'name': 'Обращений в час'})
                        chart.set_size({'width': 720, 'height': 400})
                        ws2.insert_chart('E2', chart)
                    
                    # Лист 3: Статистика по дням (НОВЫЙ ЛИСТ)
                    if not df_operators.empty:
                        # Добавляем день недели
                        df_operators['День_недели'] = df_operators['Дата_МСК'].dt.date.apply(get_weekday_name)
                        
                        # Статистика по календарным дням
                        day_stats = df_operators.groupby('Дата_только').size().reset_index(name='Обращений')
                        day_stats = day_stats.sort_values('Обращений', ascending=False)
                        day_stats['День_недели'] = day_stats['Дата_только'].apply(get_weekday_name)
                        
                        # Статистика по дням недели
                        weekday_stats = df_operators.groupby('День_недели').size().reset_index(name='Обращений')
                        weekday_order = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
                        weekday_stats['_sort'] = weekday_stats['День_недели'].apply(lambda x: weekday_order.index(x) if x in weekday_order else 999)
                        weekday_stats = weekday_stats.sort_values('_sort').drop('_sort', axis=1)
                        
                        # Записываем оба блока на один лист
                        day_stats.to_excel(writer, sheet_name='Статистика по дням', index=False, startrow=1)
                        ws3 = writer.sheets['Статистика по дням']
                        
                        ws3.write(0, 0, 'Топ загруженных календарных дней:', workbook.add_format({'bold': True, 'font_size': 14}))
                        for col_num, value in enumerate(day_stats.columns.values):
                            ws3.write(1, col_num, value, header_fmt)
                        ws3.set_column('A:A', 15)
                        ws3.set_column('B:B', 15)
                        ws3.set_column('C:C', 15)
                        
                        start_row = len(day_stats) + 4
                        ws3.write(start_row, 0, 'Статистика по дням недели:', workbook.add_format({'bold': True, 'font_size': 14}))
                        weekday_stats.to_excel(writer, sheet_name='Статистика по дням', index=False, startrow=start_row + 1)
                        
                        for col_num, value in enumerate(weekday_stats.columns.values):
                            ws3.write(start_row + 1, col_num, value, header_fmt)
                    
                    # Лист 4: Жалобы
                    pivot_reset = pivot.reset_index()
                    pivot_reset.to_excel(writer, sheet_name='Жалобы по ресторанам', index=False)
                    ws4 = writer.sheets['Жалобы по ресторанам']
                    for col_num, value in enumerate(pivot_reset.columns.values):
                        ws4.write(0, col_num, value, header_fmt)
                    
                    # Диаграмма для Листа 4 (ИСПРАВЛЕННАЯ ВЕРСИЯ)
                    if len(pivot_reset) > 0 and len(pivot_reset.columns) > 1:
                        cols = [c for c in pivot_reset.columns if c not in ['Ресторан', 'ИТОГО']]
                        
                        if len(cols) > 0:  # Проверка, что есть категории для диаграммы
                            chart = workbook.add_chart({'type': 'bar stacked'})
                            
                            for i, col in enumerate(cols):
                                col_idx = list(pivot_reset.columns).index(col)
                                num_rows = len(pivot_reset)
                                
                                chart.add_series({
                                    'name': str(col),
                                    'categories': ['Жалобы по ресторанам', 1, 0, num_rows, 0],
                                    'values': ['Жалобы по ресторанам', 1, col_idx, num_rows, col_idx],
                                })
                            
                            chart.set_title({'name': 'Структура жалоб по ресторанам'})
                            chart.set_x_axis({'name': 'Количество жалоб'})
                            chart.set_y_axis({'name': 'Ресторан'})
                            chart.set_size({'width': 720, 'height': 500})
                            ws4.insert_chart('H2', chart)

                    # Лист 5: Бот
                    if not bot_fails_df.empty:
                        bot_fails_df.to_excel(writer, sheet_name='Ошибки Бота', index=False)
                        ws5 = writer.sheets['Ошибки Бота']
                        for col_num, value in enumerate(bot_fails_df.columns.values):
                            ws5.write(0, col_num, value, header_fmt)
                        ws5.set_column('A:A', 15)
                        ws5.set_column('B:B', 20)
                        ws5.set_column('C:C', 25)
                        ws5.set_column('D:D', 50)
                        ws5.set_column('E:E', 20)

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
