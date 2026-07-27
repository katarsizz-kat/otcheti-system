import streamlit as st
import pandas as pd
import numpy as np
import re
import io
from datetime import datetime, timedelta, time, date
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

# --- НАСТРОЙКИ И КОНСТАНТЫ ---
st.set_page_config(page_title="ОС - Отчет", layout="wide", page_icon="💬")

BRAND_COLORS = {
    "primary": "#2C3E50", "secondary": "#3498DB", "accent": "#F1C40F",
    "rating_bad": "#C0392B", "rating_good": "#27AE60",
    "bg_light": "#F8F9FA"
}

MSK_OFFSET = timedelta(hours=3)
TYUMEN_ORDER = ['Тюмень №2 – Орджоникидзе', 'Тюмень №3 – Мельникайте']

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def extract_restaurant_number(restaurant_name):
    if pd.isna(restaurant_name):
        return 9999
    match = re.search(r'№\s*(\d+)', str(restaurant_name))
    if match:
        return int(match.group(1))
    return 9999


def get_restaurant_sort_key(restaurant_name, city_name=''):
    """Возвращает кортеж для сортировки: (приоритет_города, номер/индекс, имя)."""
    city = str(city_name)
    name = str(restaurant_name)

    if 'Санкт-Петербург' in city or 'Санкт-Петербург' in name:
        return (0, extract_restaurant_number(name), name)
    elif 'Тюмень' in city or 'Тюмень' in name:
        try:
            return (1, TYUMEN_ORDER.index(name), name)
        except ValueError:
            return (1, 9999, name)
    else:
        return (2, extract_restaurant_number(name), name)


def categorize_complaint(text, reason):
    text = str(text).lower() + " " + str(reason).lower()
    if any(w in text for w in ['опоздание', 'задержка', 'долго', 'где курьер', 'не везут', 'холодная', 'нарушение сроков']):
        return 'Опоздание / Логистика'
    if any(w in text for w in ['перепутали', 'не положили', 'забыли', 'не тот', 'недоложили', 'нет в заказе', 'не ту пиццу']):
        return 'Комплектация (Перепутали/Забыли)'
    if any(w in text for w in ['волос', 'проволока', 'мусор', 'сырое', 'отравлен', 'инородн', 'мутант', 'плесень']):
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
    bot_fails = []
    fail_keywords_bot = ['запуталась', 'не поняла', 'упс, кажется', 'пошло не так', 'не совсем поняла']
    client_demand = ['оператор', 'позови', 'соедини', 'живого', 'человек']

    for idx, row in df.iterrows():
        text = str(row.get('Первичное сообщение', '')).lower()
        is_bot_fail = any(k in text for k in fail_keywords_bot)
        is_demand = any(k in text for k in client_demand)

        if is_bot_fail or is_demand:
            client_msgs = re.findall(
                r'Клиент\s*\([^)]+\):\s*(.*?)(?:\n|$)',
                str(row.get('Первичное сообщение', '')),
                re.DOTALL
            )
            summary = client_msgs[0].strip()[:120] if client_msgs else "Нет текста"
            bot_fails.append({
                '№ Обращения': row.get('Номер обращения', ''),
                'Дата': row.get('Дата отзыва', ''),
                'Ресторан': row.get('Ресторан', ''),
                'Суть обращения': summary,
                'Тип ошибки бота': 'Требовал оператора' if is_demand else 'Бот не понял'
            })
    return pd.DataFrame(bot_fails)


def get_hour_interval(hour):
    intervals = [
        (0, 2, '00:00-02:00'), (2, 8, '02:00-08:00'),
        (8, 9, '08:00'), (9, 10, '09:00'), (10, 11, '10:00'), (11, 12, '11:00'),
        (12, 16, '12:00-16:00'),
        (16, 17, '16:00'), (17, 18, '17:00'), (18, 19, '18:00'),
        (19, 20, '19:00'), (20, 21, '20:00'), (21, 22, '21:00'),
        (22, 23, '22:00'), (23, 24, '23:00-00:00')
    ]
    for start, end, label in intervals:
        if start <= hour < end:
            return label
    return 'Другое'


def get_interval_hours(interval_label):
    if '-' in interval_label:
        parts = interval_label.split('-')
        start = int(parts[0].split(':')[0])
        end = int(parts[1].split(':')[0])
        return 1 if end == 0 else end - start
    return 1


def get_weekday_name(d):
    return ['Понедельник', 'Вторник', 'Среда', 'Четверг',
            'Пятница', 'Суббота', 'Воскресенье'][d.weekday()]


INTERVAL_ORDER = [
    '00:00-02:00', '02:00-08:00', '08:00', '09:00', '10:00', '11:00',
    '12:00-16:00', '16:00', '17:00', '18:00', '19:00', '20:00',
    '21:00', '22:00', '23:00-00:00'
]


# --- ГЛАВНАЯ ФУНКЦИЯ ---

def main():
    st.markdown(
        f"<h1 style='text-align:center;color:{BRAND_COLORS['primary']}'>"
        f"💬 Отчет по работе Отдела Обратной Связи (ОС)</h1>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ──────────── ЗАГРУЗКА ────────────
    st.sidebar.header("📂 Загрузка данных")
    uploaded_file = st.sidebar.file_uploader(
        "Загрузите выгрузку тикетов (Excel/CSV)", type=['xlsx', 'csv']
    )
    if not uploaded_file:
        st.info("👈 Загрузите файл с выгрузкой обращений в боковой панели.")
        return

    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Ошибка чтения файла: {e}")
        return

    df['Дата отзыва'] = pd.to_datetime(df['Дата отзыва'], errors='coerce')

    # ──────────── ФИЛЬТРЫ ────────────
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Фильтры")

    available_cities = df['Город'].dropna().unique().tolist() if 'Город' in df.columns else []
    default_cities = [c for c in ['Санкт-Петербург', 'Тюмень'] if c in available_cities]
    cities = st.sidebar.multiselect("Город/регион:", options=available_cities,
                                     default=default_cities or available_cities[:3])
    df_filtered = df[df['Город'].isin(cities)] if cities else df.copy()

    # Фильтр по датам
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Период")
    date_filter_type = st.sidebar.radio("Тип фильтра:", ["Интервал дат", "Отдельные даты"], index=0)

    valid_dates = df_filtered['Дата отзыва'].dropna()
    if not valid_dates.empty:
        min_d, max_d = valid_dates.min().date(), valid_dates.max().date()
        if date_filter_type == "Интервал дат":
            date_range = st.sidebar.date_input("Период:", value=(min_d, max_d),
                                                min_value=min_d, max_value=max_d)
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                s, e = date_range
                df_filtered = df_filtered[(df_filtered['Дата отзыва'].dt.date >= s) &
                                          (df_filtered['Дата отзыва'].dt.date <= e)]
        else:
            unique_dates = sorted(valid_dates.dt.date.unique(), reverse=True)
            sel = st.sidebar.multiselect("Даты:", options=unique_dates,
                                          default=unique_dates[:7] if len(unique_dates) >= 7 else unique_dates)
            if sel:
                df_filtered = df_filtered[df_filtered['Дата отзыва'].dt.date.isin(sel)]

    valid_dates = df_filtered['Дата отзыва'].dropna()
    if not valid_dates.empty:
        st.success(f"✅ Тикетов: **{len(df_filtered)}** | "
                   f"**{valid_dates.min().date()}** — **{valid_dates.max().date()}**")
    else:
        st.success(f"✅ Тикетов: **{len(df_filtered)}**")

    # ──────────── ВКЛАДКИ ────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Статистика операторов", "🍕 Жалобы и Рестораны",
        "🤖 Анализ Чат-бота", "📥 Экспорт в Excel"
    ])

    # =============================================
    # ВКЛАДКА 1: СТАТИСТИКА ОПЕРАТОРОВ
    # =============================================
    with tab1:
        st.subheader("Загрузка операторов и распределение по часам")
        st.caption("⏱ Только живые операторы. Время МСК (+3 ч). Обращения до 02:00 считаются за предыдущий день.")

        df_op = df_filtered[
            (df_filtered['Исполнитель'].notna()) &
            (df_filtered['Исполнитель'] != 'Системный пользователь')
        ].copy()

        if df_op.empty:
            st.warning("Нет данных по живым операторам.")
        else:
            df_op['Дата_МСК'] = df_op['Дата отзыва'] + MSK_OFFSET
            df_op['Час_МСК'] = df_op['Дата_МСК'].dt.hour
            # Ночные тикеты (до 02:00) → предыдущий день
            df_op['Дата_рабочая'] = df_op.apply(
                lambda r: (r['Дата_МСК'] - timedelta(days=1)).date() if r['Час_МСК'] < 2 else r['Дата_МСК'].date(),
                axis=1
            )

            # --- Таблица операторов ---
            st.markdown("##### 📋 Статистика по операторам")
            op_rows = []
            for op in df_op['Исполнитель'].unique():
                sub = df_op[df_op['Исполнитель'] == op]
                days = sub['Дата_рабочая'].nunique()
                total = len(sub)
                op_rows.append({
                    'Оператор': op,
                    'Всего обращений': total,
                    'Рабочих дней': days,
                    'Среднее в день': round(total / days, 2) if days else 0
                })
            df_op_stats = pd.DataFrame(op_rows).sort_values('Всего обращений', ascending=False)
            st.dataframe(df_op_stats, use_container_width=True, hide_index=True)

            # --- Совместная работа ---
            st.markdown("##### 👥 Совместная работа операторов")
            day_ops = df_op.groupby('Дата_рабочая')['Исполнитель'].apply(lambda x: sorted(set(x))).reset_index()
            day_ops['Кол-во'] = day_ops['Исполнитель'].apply(len)
            multi = day_ops[day_ops['Кол-во'] > 1].copy()
            if not multi.empty:
                multi['Операторы'] = multi['Исполнитель'].apply(', '.join)
                st.dataframe(multi[['Дата_рабочая', 'Кол-во', 'Операторы']].sort_values('Дата_рабочая', ascending=False),
                             use_container_width=True, hide_index=True)
            else:
                st.info("Каждый день работал только один оператор.")

            # --- Часовые интервалы ---
            st.markdown("##### 🕐 Распределение по часам (МСК)")
            df_op['Интервал'] = df_op['Час_МСК'].apply(get_hour_interval)
            h_stats = df_op.groupby('Интервал').size().reset_index(name='Обращений')
            h_stats['Обращений/час'] = h_stats.apply(
                lambda r: round(r['Обращений'] / get_interval_hours(r['Интервал']), 2), axis=1
            )
            h_stats['_s'] = h_stats['Интервал'].apply(lambda x: INTERVAL_ORDER.index(x) if x in INTERVAL_ORDER else 99)
            h_stats = h_stats.sort_values('_s').drop('_s', axis=1)
            st.dataframe(h_stats, use_container_width=True, hide_index=True)
            st.bar_chart(h_stats.set_index('Интервал')[['Обращений/час']])

    # =============================================
    # ВКЛАДКА 2: ЖАЛОБЫ И РЕСТОРАНЫ
    # =============================================
    with tab2:
        st.subheader("Аналитика жалоб по категориям и ресторанам")

        df_f = df_filtered.copy()
        df_f['Категория'] = df_f.apply(
            lambda r: categorize_complaint(r.get('Первичное сообщение', ''), r.get('Причина обращения', '')), axis=1
        )

        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("##### Топ категорий")
            st.bar_chart(df_f['Категория'].value_counts())

        with col2:
            st.markdown("##### Ресторан × Категория")
            pivot = pd.pivot_table(df_f, index='Ресторан', columns='Категория', aggfunc='size', fill_value=0)
            pivot['ИТОГО'] = pivot.sum(axis=1)
            pivot_reset = pivot.reset_index()

            # Добавляем город для сортировки
            city_map = df_f.drop_duplicates('Ресторан').set_index('Ресторан')['Город'].to_dict()
            pivot_reset['Город'] = pivot_reset['Ресторан'].map(city_map).fillna('')
            pivot_reset['_sk'] = pivot_reset.apply(lambda r: get_restaurant_sort_key(r['Ресторан'], r['Город']), axis=1)
            pivot_reset = pivot_reset.sort_values('_sk').drop(['Город', '_sk'], axis=1)
            pivot_sorted = pivot_reset.set_index('Ресторан')

            st.dataframe(pivot_sorted, use_container_width=True)

    # =============================================
    # ВКЛАДКА 3: АНАЛИЗ ЧАТ-БОТА
    # =============================================
    with tab3:
        st.subheader("Ошибки чат-бота и запросы оператора")
        bot_df = analyze_bot_fails(df_filtered)
        if not bot_df.empty:
            c1, c2 = st.columns([1, 3])
            with c1:
                st.metric("Сбоев бота", len(bot_df))
                st.dataframe(bot_df['Тип ошибки бота'].value_counts(), use_container_width=True)
            with c2:
                st.dataframe(bot_df, use_container_width=True, hide_index=True)
        else:
            st.success("Сбоев бота не обнаружено.")

    # =============================================
    # ВКЛАДКА 4: ЭКСПОРТ
    # =============================================
    with tab4:
        st.subheader("Генерация Excel-отчёта")
        st.info("5 листов: Операторы · Часы · Дни · Жалобы · Бот. С диаграммами!")

        if st.button("📥 Сформировать и скачать Excel", type="primary"):
            with st.spinner("Формируем..."):
                buf = io.BytesIO()
                try:
                    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                        wb = writer.book
                        hdr = wb.add_format({'bold': True, 'bg_color': '#2C3E50',
                                             'font_color': 'white', 'border': 1})
                        title_fmt = wb.add_format({'bold': True, 'font_size': 13})

                        # ── Лист 1: Операторы ──
                        if not df_op.empty:
                            df_op_stats.to_excel(writer, sheet_name='Операторы', index=False)
                            ws = writer.sheets['Операторы']
                            for c, v in enumerate(df_op_stats.columns):
                                ws.write(0, c, v, hdr)
                            ws.set_column('A:A', 30)
                            ws.set_column('B:D', 18)

                        # ── Лист 2: Часовая нагрузка ──
                        if not df_op.empty:
                            h_stats.to_excel(writer, sheet_name='Часы', index=False)
                            ws2 = writer.sheets['Часы']
                            for c, v in enumerate(h_stats.columns):
                                ws2.write(0, c, v, hdr)
                            ws2.set_column('A:A', 15)
                            ws2.set_column('B:C', 18)

                            try:
                                n = len(h_stats)
                                ch = wb.add_chart({'type': 'column'})
                                ch.add_series({
                                    'name': 'Обращений/час',
                                    'categories': f"'Часы'!$A$2:$A${n + 1}",
                                    'values': f"'Часы'!$C$2:$C${n + 1}",
                                })
                                ch.set_title({'name': 'Нагрузка по часам (МСК)'})
                                ch.set_size({'width': 720, 'height': 400})
                                ws2.insert_chart('E2', ch)
                            except Exception:
                                pass

                        # ── Лист 3: Дни ──
                        if not df_op.empty:
                            day_stats = df_op.groupby('Дата_рабочая').size().reset_index(name='Обращений')
                            day_stats = day_stats.sort_values('Обращений', ascending=False)
                            day_stats['День недели'] = day_stats['Дата_рабочая'].apply(get_weekday_name)

                            wd_order = ['Понедельник', 'Вторник', 'Среда', 'Четверг',
                                        'Пятница', 'Суббота', 'Воскресенье']
                            wd_stats = df_op.groupby(df_op['Дата_рабочая'].apply(get_weekday_name)).size().reset_index(name='Обращений')
                            wd_stats.columns = ['День недели', 'Обращений']
                            wd_stats['_s'] = wd_stats['День недели'].apply(lambda x: wd_order.index(x) if x in wd_order else 99)
                            wd_stats = wd_stats.sort_values('_s').drop('_s', axis=1)

                            day_stats.to_excel(writer, sheet_name='Дни', index=False, startrow=1)
                            ws3 = writer.sheets['Дни']
                            ws3.write(0, 0, 'Топ загруженных дней', title_fmt)
                            for c, v in enumerate(day_stats.columns):
                                ws3.write(1, c, v, hdr)
                            ws3.set_column('A:A', 14)
                            ws3.set_column('B:C', 16)

                            sr = len(day_stats) + 4
                            ws3.write(sr, 0, 'По дням недели', title_fmt)
                            wd_stats.to_excel(writer, sheet_name='Дни', index=False, startrow=sr + 1)
                            for c, v in enumerate(wd_stats.columns):
                                ws3.write(sr + 1, c, v, hdr)

                        # ── Лист 4: Жалобы по ресторанам ──
                        pivot_reset.to_excel(writer, sheet_name='Жалобы', index=False)
                        ws4 = writer.sheets['Жалобы']
                        for c, v in enumerate(pivot_reset.columns):
                            ws4.write(0, c, v, hdr)
                        ws4.set_column('A:A', 35)

                        # Диаграмма жалоб
                        try:
                            cols_chart = [c for c in pivot_reset.columns if c not in ('Ресторан', 'ИТОГО')]
                            n_rows = len(pivot_reset)
                            if cols_chart and n_rows > 0:
                                ch2 = wb.add_chart({'type': 'bar', 'subtype': 'stacked'})
                                for ci, cname in enumerate(cols_chart):
                                    real_idx = list(pivot_reset.columns).index(cname)
                                    col_letter = xl_col_to_name(real_idx)
                                    ch2.add_series({
                                        'name': str(cname),
                                        'categories': f"'Жалобы'!$A$2:$A${n_rows + 1}",
                                        'values': f"'Жалобы'!${col_letter}$2:${col_letter}${n_rows + 1}",
                                    })
                                ch2.set_title({'name': 'Структура жалоб по ресторанам'})
                                ch2.set_size({'width': 800, 'height': 500})
                                ws4.insert_chart('H2', ch2)
                        except Exception:
                            pass

                        # ── Лист 5: Ошибки бота ──
                        if not bot_df.empty:
                            bot_df.to_excel(writer, sheet_name='Бот', index=False)
                            ws5 = writer.sheets['Бот']
                            for c, v in enumerate(bot_df.columns):
                                ws5.write(0, c, v, hdr)
                            ws5.set_column('A:A', 15)
                            ws5.set_column('B:B', 20)
                            ws5.set_column('C:C', 30)
                            ws5.set_column('D:D', 60)
                            ws5.set_column('E:E', 22)

                except Exception as e:
                    st.error(f"Ошибка при формировании Excel: {e}")
                    return

                buf.seek(0)
                st.download_button(
                    label="💾 Скачать отчёт (.xlsx)",
                    data=buf,
                    file_name="OS_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.balloons()


if __name__ == "__main__":
    main()
