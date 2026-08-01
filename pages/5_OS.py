import streamlit as st
import pandas as pd
import numpy as np
import re
import io
from datetime import datetime, timedelta, time, date
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

# --- НАСТРОЙКИ И КОНСТАНТЫ ---
st.set_page_config(page_title="😊😠 ОС", page_icon="📈", layout="wide")

BRAND_COLORS = {
    "primary": "#2C3E50", "secondary": "#3498DB", "accent": "#F1C40F",
    "rating_bad": "#C0392B", "rating_good": "#27AE60",
    "bg_light": "#F8F9FA"
}

MSK_OFFSET = timedelta(hours=3)
TYUMEN_ORDER = ['Тюмень №2 – Орджоникидзе', 'Тюмень №3 – Мельникайте']
EXCLUDED_OPERATORS = ['Marketing SPB']

# ============================================================
# КАТЕГОРИИ ЖАЛОБ
# ============================================================

CATEGORY_MAPPING = {
    'Отравление':                          'Критические инциденты',
    'Инородный предмет в блюде':            'Критические инциденты',
    'Опоздания':                            'Опоздания',
    'Не доставили заказ':                   'Перепутанная/недовезённая позиция',
    'Холодная пицца':                       'Жалоба на блюдо',
    'Разлит / Повреждение упаковки':        'Жалоба на блюдо',
    'Забыли позицию':                       'Перепутанная/недовезённая позиция',
    'Перепутали позицию':                   'Перепутанная/недовезённая позиция',
    'Невкусно':                             'Жалоба на блюдо',
    'Некачественно':                        'Жалоба на блюдо',
    'Приложение / Сайт / IT-сбои':          'Сайт и IT-сбои',
    'Проблема с бонусами или промокодом':   'Программа лояльности',
    'Скидка на День Рождения':              'Программа лояльности',
    'Возврат ДС':                           'Возврат ДС',
    'Слишком дорого':                       'Жалоба на сервис',
    'Жалоба на сервис':                     'Жалоба на сервис',
    'Не дозвониться':                       'Жалоба на сервис',
    'Управление аккаунтом':                 'Аккаунт',
}

AGG_ORDER = [
    'Опоздания', 'Перепутанная/недовезённая позиция', 'Жалоба на блюдо',
    'Сайт и IT-сбои', 'Программа лояльности', 'Возврат ДС',
    'Жалоба на сервис', 'Аккаунт', 'Критические инциденты'
]


def categorize_complaint_detailed(text, reason):
    """Таблица 1: Детальная категоризация."""
    t = (str(text) + " " + str(reason)).lower()

    if any(w in t for w in ['отравл', 'тошнит', 'тошнило', 'диарея', 'рвота',
                             'плохо стало', 'заболел', 'заболели']):
        return 'Отравление'
    if any(w in t for w in ['волос', 'проволока', 'инородн', 'предмет',
                             'стекло', 'металл', 'мусор', 'плесень', 'жук',
                             'таракан', 'гвоздь', 'щепка']):
        return 'Инородный предмет в блюде'
    if any(w in t for w in ['опозд', 'задержк', 'долго', 'где курьер',
                             'не везут', 'нарушение сроков', 'отодвигается',
                             'сдвинули время', 'принудительн', 'изменили время',
                             'праздник не вышло', 'ждали на праздник',
                             'срыв', 'не привезли вовремя', 'не в заявленное',
                             'час задержк', 'два часа', 'больше часа',
                             'более чем на час', 'на 40 минут', 'на 50 минут',
                             'на 30 минут', 'на полтора', 'статус не меняется',
                             'курьер не едет', 'не выехал']):
        return 'Опоздания'
    if any(w in t for w in ['не привезли заказ', 'не доставили заказ',
                             'нет моего заказа', 'заказ не привезли',
                             'не получил заказ', 'заказ так и не',
                             'отменили заказ', 'заказ не попал']):
        return 'Не доставили заказ'
    if any(w in t for w in ['холодн', 'остывш', 'ледян', 'не горяч',
                             'еле тепл', 'тепленьк']):
        return 'Холодная пицца'
    if any(w in t for w in ['разлит', 'вылит', 'растаяло', 'растаявш',
                             'пострадал десерт', 'повреждение упаковк',
                             'мятая', 'смята', 'прилипла', 'перевёрнут',
                             'перевернут', 'соус в пакет', 'соус в картошк',
                             'раздавлен', 'протекает', 'коробка вся']):
        return 'Разлит / Повреждение упаковки'
    if any(w in t for w in ['забыли', 'не положили', 'не доложили',
                             'отсутствует', 'нет в заказе', 'не хватает',
                             'не привезли соус', 'не привезли перец',
                             'не привезли фри', 'не привезли крылья',
                             'не привезли подарочн', 'недовоз',
                             'не положили один', 'не положили два',
                             'не было соуса', 'нет соуса', 'без соуса',
                             'без перца', 'без бортиков', 'без курицы',
                             'без картошки', 'некомплектн', 'не полный заказ',
                             'не разрезана', 'не порезана']):
        return 'Забыли позицию'
    if any(w in t for w in ['перепутали', 'не тот', 'не ту', 'другой заказ',
                             'вместо', 'привезли одинаковые', 'не то тесто',
                             'не тот борт', 'сырный борт а не колбасный',
                             'колбасный а не сырный', 'другую пиццу',
                             'не та пицца', 'не те', 'ошибк в заказ',
                             'привезли не то', 'пришла не та',
                             '20 см вместо', '30 см вместо',
                             'не тот размер']):
        return 'Перепутали позицию'
    if any(w in t for w in ['невкусно', 'ужасн вкус', 'резин', 'сухая',
                             'без начинки', 'мало начинки', 'горелые',
                             'горелая', 'пережарен', 'пересушен',
                             'никакая на вкус', 'отвратительн вкус']):
        return 'Невкусно'
    if any(w in t for w in ['некачествен', 'сырое', 'сырая', 'непропечен',
                             'недожарен', 'контроль качества',
                             'не соответствует', 'ужасно приготовлен',
                             'начинка размазан', 'тесто не пропеклос',
                             'слипшаяся', 'качество доставленн']):
        return 'Некачественно'
    if any(w in t for w in ['не работает', 'ошибка', 'глючит', 'глючная',
                             'не оформляется', 'зависает', 'корзина пуст',
                             'внутренняя ошибка', 'не тот адрес',
                             'не отображается', 'пропали заказ',
                             'не могу оформить', 'сложность в оформлен',
                             'не прошла оплат', 'оплату не засчитал',
                             'не могу применить', 'сброс', 'не загружается',
                             'не предлагает оплатить', 'приложение у меня',
                             'указало этот адрес', 'некорректная работа',
                             'не могу сделать заказ', 'не могу зарегистрир',
                             'не приходят сообщен', 'не отображается истор',
                             'статус заказа в приложени']):
        return 'Приложение / Сайт / IT-сбои'
    if any(w in t for w in ['промокод', 'бонус', 'папа бонус', 'балл',
                             'не начислили', 'списали', 'не применился',
                             'не сработал', 'начислен', 'баллы за',
                             'не приходят бонусн', 'автоматом спиш',
                             'не дали списать', 'не дает списать']):
        return 'Проблема с бонусами или промокодом'
    if any(w in t for w in ['день рождения', 'день рождени', 'др',
                             'скидка на др', 'промокод на день',
                             'подарок на др', 'на днях был др',
                             'дню рождения', 'днем рождения',
                             'не пришёл промокод', 'не присылают']):
        return 'Скидка на День Рождения'
    if any(w in t for w in ['возврат', 'верните деньги', 'верните средств',
                             'вернуть деньги', 'вернуть средств',
                             'двойное списан', 'два раза оплатил',
                             'списались за оба', 'компенсац',
                             'возмещен', 'когда вернутся',
                             'возврат денежн', 'частичную компенс']):
        return 'Возврат ДС'
    if any(w in t for w in ['слишком дорог', 'очень дорог', 'завышен',
                             'содрать', 'платная доставка',
                             'стоимость доставк', 'цена завыш',
                             'неприемлем', 'заплатила очень много']):
        return 'Слишком дорого'
    if any(w in t for w in ['груб', 'хам', 'невежл', 'хамили',
                             'наказать', 'конфликт', 'перекладывание вины',
                             'не умеете работать', 'отвратительн сервис',
                             'курьер грубил', 'смеялся', 'не отдал заказ',
                             'без термосумки', 'без терминала',
                             'не русского', 'отказалась принять',
                             'не приняли заказ', 'отказ принять']):
        return 'Жалоба на сервис'
    if any(w in t for w in ['не берут трубку', 'не отвечает', 'сбрасывает',
                             'недозвон', 'телефон недоступен',
                             'не дозвониться', 'номер занят',
                             'не подходит', 'никто не взял',
                             'не отвечает на звонки', 'оператор не отвечает',
                             'поддержка не отвечает', 'горячую линию',
                             'никто не подходит', 'сброс звонка',
                             'идет сброс']):
        return 'Не дозвониться'
    if any(w in t for w in ['удалите профиль', 'удаление аккаунта',
                             'восстановить аккаунт', 'объединить',
                             'уведомления', 'спам', 'рассылк',
                             'отключите', 'изменился номер',
                             'объединение аккаунт', 'не могу зарегистрир',
                             'случайно удалила', 'удалил аккаунт']):
        return 'Управление аккаунтом'

    return 'Другое / Запрос'


def get_aggregated_category(detailed_cat):
    return CATEGORY_MAPPING.get(detailed_cat, 'Другое')


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def extract_restaurant_number(restaurant_name):
    if pd.isna(restaurant_name):
        return 9999
    match = re.search(r'№\s*(\d+)', str(restaurant_name))
    return int(match.group(1)) if match else 9999


def get_restaurant_sort_key(restaurant_name, city_name=''):
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


def analyze_bot_fails(df):
    bot_fails = []
    fail_kw = ['запуталась', 'не поняла', 'упс, кажется', 'пошло не так', 'не совсем поняла']
    demand_kw = ['оператор', 'позови', 'соедини', 'живого', 'человек']
    for _, row in df.iterrows():
        text = str(row.get('Первичное сообщение', '')).lower()
        is_fail = any(k in text for k in fail_kw)
        is_demand = any(k in text for k in demand_kw)
        if is_fail or is_demand:
            msgs = re.findall(r'Клиент\s*\([^)]+\):\s*(.*?)(?:\n|$)',
                              str(row.get('Первичное сообщение', '')), re.DOTALL)
            summary = msgs[0].strip()[:120] if msgs else "Нет текста"
            bot_fails.append({
                '№ Обращения': row.get('Номер обращения', ''),
                'Дата': row.get('Дата отзыва', ''),
                'Ресторан': row.get('Ресторан', ''),
                'Суть обращения': summary,
                'Тип ошибки бота': 'Требовал оператора' if is_demand else 'Бот не понял'
            })
    return pd.DataFrame(bot_fails)


def get_hour_interval(hour):
    """Возвращает часовой интервал. Все по 1 часу, кроме 02:00-08:00."""
    if hour == 0:
        return '00:00-01:00'
    elif hour == 1:
        return '01:00-02:00'
    elif 2 <= hour < 8:
        return '02:00-08:00'
    else:
        next_hour = (hour + 1) % 24
        return f"{hour:02d}:00-{next_hour:02d}:00"


INTERVAL_ORDER = [
    '00:00-01:00', '01:00-02:00', '02:00-08:00',
    '08:00-09:00', '09:00-10:00', '10:00-11:00', '11:00-12:00',
    '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00',
    '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00',
    '20:00-21:00', '21:00-22:00', '22:00-23:00', '23:00-00:00'
]


def get_interval_hours(label):
    """Возвращает количество часов в интервале."""
    if label == '02:00-08:00':
        return 6
    return 1


def get_weekday_name(d):
    return ['Понедельник', 'Вторник', 'Среда', 'Четверг',
            'Пятница', 'Суббота', 'Воскресенье'][d.weekday()]


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def main():
    st.markdown(
        f"<h1 style='text-align:center;color:{BRAND_COLORS['primary']}'>"
        f"💬 Отчет по работе Отдела Обратной Связи (ОС)</h1>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── ЗАГРУЗКА ──
    st.sidebar.header("📂 Загрузка данных")
    uploaded_file = st.sidebar.file_uploader(
        "Загрузите выгрузку тикетов (Excel/CSV)", type=['xlsx', 'csv'])
    if not uploaded_file:
        st.info("👈 Загрузите файл с выгрузкой обращений в боковой панели.")
        return

    try:
        df = (pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv')
              else pd.read_excel(uploaded_file))
    except Exception as e:
        st.error(f"Ошибка чтения файла: {e}")
        return

    df['Дата отзыва'] = pd.to_datetime(df['Дата отзыва'], errors='coerce')

    # ── ФИЛЬТРЫ ──
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Фильтры")
    available_cities = df['Город'].dropna().unique().tolist() if 'Город' in df.columns else []
    default_cities = [c for c in ['Санкт-Петербург', 'Тюмень'] if c in available_cities]
    cities = st.sidebar.multiselect("Город/регион:", options=available_cities,
                                     default=default_cities or available_cities[:3])
    df_filtered = df[df['Город'].isin(cities)] if cities else df.copy()

    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Период")
    date_type = st.sidebar.radio("Тип фильтра:", ["Интервал дат", "Отдельные даты"])
    valid_dates = df_filtered['Дата отзыва'].dropna()

    if not valid_dates.empty:
        min_d, max_d = valid_dates.min().date(), valid_dates.max().date()
        if date_type == "Интервал дат":
            dr = st.sidebar.date_input("Период:", value=(min_d, max_d),
                                        min_value=min_d, max_value=max_d)
            if isinstance(dr, (list, tuple)) and len(dr) == 2:
                df_filtered = df_filtered[
                    (df_filtered['Дата отзыва'].dt.date >= dr[0]) &
                    (df_filtered['Дата отзыва'].dt.date <= dr[1])]
        else:
            ud = sorted(valid_dates.dt.date.unique(), reverse=True)
            sel = st.sidebar.multiselect("Даты:", options=ud,
                                          default=ud[:7] if len(ud) >= 7 else ud)
            if sel:
                df_filtered = df_filtered[df_filtered['Дата отзыва'].dt.date.isin(sel)]

    valid_dates = df_filtered['Дата отзыва'].dropna()
    if not valid_dates.empty:
        st.success(f"✅ Тикетов: **{len(df_filtered)}** | "
                   f"**{valid_dates.min().date()}** — **{valid_dates.max().date()}**")
    else:
        st.success(f"✅ Тикетов: **{len(df_filtered)}**")

    # ── ВКЛАДКИ ──
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Статистика операторов", "🍕 Жалобы и Рестораны",
        "🤖 Анализ Чат-бота", "📥 Экспорт в Excel"])

    # =============================================
    # ВКЛАДКА 1: СТАТИСТИКА ОПЕРАТОРОВ
    # =============================================
    with tab1:
        st.subheader("Загрузка операторов и распределение по часам")
        st.caption("⏱ Только живые операторы. МСК (+3 ч). До 02:00 = предыдущий день.")

        df_op = df_filtered[
            (df_filtered['Исполнитель'].notna()) &
            (df_filtered['Исполнитель'] != 'Системный пользователь')
        ].copy()

        if df_op.empty:
            st.warning("Нет данных по живым операторам.")
        else:
            df_op['Дата_МСК'] = df_op['Дата отзыва'] + MSK_OFFSET
            df_op['Час_МСК'] = df_op['Дата_МСК'].dt.hour
            df_op['Дата_рабочая'] = df_op.apply(
                lambda r: (r['Дата_МСК'] - timedelta(days=1)).date()
                if r['Час_МСК'] < 2 else r['Дата_МСК'].date(), axis=1)

            # --- Таблица операторов ---
            st.markdown("##### 📋 Статистика по операторам")
            op_rows = []
            for op in df_op['Исполнитель'].unique():
                sub = df_op[df_op['Исполнитель'] == op]
                days = sub['Дата_рабочая'].nunique()
                total = len(sub)
                op_rows.append({
                    'Оператор': op, 'Всего обращений': total,
                    'Рабочих дней': days,
                    'Среднее в день': round(total / days, 2) if days else 0})
            df_op_stats = pd.DataFrame(op_rows).sort_values('Всего обращений', ascending=False)
            st.dataframe(df_op_stats, use_container_width=True, hide_index=True)

            # --- Совместная работа (БЕЗ Marketing SPB) ---
            st.markdown("##### 👥 Совместная работа операторов")
            st.caption(f"Дни, когда обращения обрабатывали несколько операторов одновременно. "
                       f"Исключены: {', '.join(EXCLUDED_OPERATORS)}")

            df_op_joint = df_op[~df_op['Исполнитель'].isin(EXCLUDED_OPERATORS)].copy()
            day_ops = df_op_joint.groupby('Дата_рабочая')['Исполнитель'].apply(
                lambda x: sorted(set(x))).reset_index()
            day_ops['Кол-во'] = day_ops['Исполнитель'].apply(len)
            multi = day_ops[day_ops['Кол-во'] > 1].copy()

            if not multi.empty:
                multi['Операторы'] = multi['Исполнитель'].apply(', '.join)
                st.dataframe(
                    multi[['Дата_рабочая', 'Кол-во', 'Операторы']]
                    .sort_values('Дата_рабочая', ascending=False),
                    use_container_width=True, hide_index=True)
            else:
                st.info(f"Каждый день работал только один оператор (без учёта {', '.join(EXCLUDED_OPERATORS)}).")

            # --- Часовые интервалы ---
            st.markdown("##### 🕐 Распределение по часам (МСК)")
            
            # Количество дней в периоде
            total_days = df_op['Дата_рабочая'].nunique()
            
            df_op['Интервал'] = df_op['Час_МСК'].apply(get_hour_interval)
            h_stats = df_op.groupby('Интервал').size().reset_index(name='Обращений')
            h_stats['Обращений/час'] = h_stats.apply(
                lambda r: round(r['Обращений'] / get_interval_hours(r['Интервал']), 2), axis=1)
            h_stats['Обращений/час/день'] = h_stats.apply(
                lambda r: round(r['Обращений'] / get_interval_hours(r['Интервал']) / total_days, 2) 
                if total_days > 0 else 0, axis=1)
            
            h_stats['_s'] = h_stats['Интервал'].apply(
                lambda x: INTERVAL_ORDER.index(x) if x in INTERVAL_ORDER else 99)
            h_stats = h_stats.sort_values('_s').drop('_s', axis=1)

            # Добавляем пропущенные интервалы
            all_intervals_df = pd.DataFrame({'Интервал': INTERVAL_ORDER})
            h_stats = all_intervals_df.merge(h_stats, on='Интервал', how='left').fillna(0)
            h_stats['Обращений'] = h_stats['Обращений'].astype(int)
            h_stats['Обращений/час'] = h_stats['Обращений/час'].astype(float)
            h_stats['Обращений/час/день'] = h_stats['Обращений/час/день'].astype(float)

            st.caption(f"📊 Период: **{total_days} дней**")
            st.dataframe(h_stats, use_container_width=True, hide_index=True)
            st.bar_chart(h_stats.set_index('Интервал')[['Обращений/час', 'Обращений/час/день']])

    # =============================================
    # ВКЛАДКА 2: ЖАЛОБЫ И РЕСТОРАНЫ
    # =============================================
    with tab2:
        st.subheader("Аналитика жалоб по категориям и ресторанам")

        df_f = df_filtered.copy()
        df_f['Категория'] = df_f.apply(
            lambda r: categorize_complaint_detailed(
                r.get('Первичное сообщение', ''), r.get('Причина обращения', '')), axis=1)
        df_f['Категория_укрупн'] = df_f['Категория'].apply(get_aggregated_category)

        # --- ТАБЛИЦА 1: Детальная ---
        st.markdown("##### 📋 Таблица 1: Детальные категории жалоб")
        col1, col2 = st.columns([1, 2])
        with col1:
            cat_counts = df_f['Категория'].value_counts()
            st.bar_chart(cat_counts)
        with col2:
            pivot1 = pd.pivot_table(df_f, index='Ресторан', columns='Категория',
                                     aggfunc='size', fill_value=0)
            pivot1['ИТОГО'] = pivot1.sum(axis=1)
            p1_reset = pivot1.reset_index()
            city_map = df_f.drop_duplicates('Ресторан').set_index('Ресторан')['Город'].to_dict()
            p1_reset['Город'] = p1_reset['Ресторан'].map(city_map).fillna('')
            p1_reset['_sk'] = p1_reset.apply(
                lambda r: get_restaurant_sort_key(r['Ресторан'], r['Город']), axis=1)
            p1_reset = p1_reset.sort_values('_sk').drop(['Город', '_sk'], axis=1)
            pivot1_sorted = p1_reset.set_index('Ресторан')
            st.dataframe(pivot1_sorted, use_container_width=True)

        st.markdown("---")

        # --- ТАБЛИЦА 2: Укрупнённая ---
        st.markdown("##### 📋 Таблица 2: Укрупнённые категории жалоб")
        col3, col4 = st.columns([1, 2])
        with col3:
            agg_counts = df_f['Категория_укрупн'].value_counts()
            agg_sorted = pd.Series({k: agg_counts.get(k, 0) for k in AGG_ORDER
                                    if agg_counts.get(k, 0) > 0})
            st.bar_chart(agg_sorted)
        with col4:
            pivot2 = pd.pivot_table(df_f, index='Ресторан', columns='Категория_укрупн',
                                     aggfunc='size', fill_value=0)
            pivot2['ИТОГО'] = pivot2.sum(axis=1)
            p2_reset = pivot2.reset_index()
            p2_reset['Город'] = p2_reset['Ресторан'].map(city_map).fillna('')
            p2_reset['_sk'] = p2_reset.apply(
                lambda r: get_restaurant_sort_key(r['Ресторан'], r['Город']), axis=1)
            p2_reset = p2_reset.sort_values('_sk').drop(['Город', '_sk'], axis=1)
            pivot2_sorted = p2_reset.set_index('Ресторан')
            st.dataframe(pivot2_sorted, use_container_width=True)

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
                st.dataframe(bot_df['Тип ошибки бота'].value_counts(),
                             use_container_width=True)
            with c2:
                st.dataframe(bot_df, use_container_width=True, hide_index=True)
        else:
            st.success("Сбоев бота не обнаружено.")

    # =============================================
    # ВКЛАДКА 4: ЭКСПОРТ
    # =============================================
    with tab4:
        st.subheader("Генерация Excel-отчёта")
        st.info("7 листов: Операторы · Часы · Дни · Жалобы (деталь) · "
                "Жалобы (укрупн) · Бот. С диаграммами!")

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

                        # ── Лист 2: Часы ──
                        if not df_op.empty:
                            h_stats.to_excel(writer, sheet_name='Часы', index=False)
                            ws2 = writer.sheets['Часы']
                            for c, v in enumerate(h_stats.columns):
                                ws2.write(0, c, v, hdr)
                            ws2.set_column('A:A', 15)
                            ws2.set_column('B:D', 20)
                            try:
                                n = len(h_stats)
                                ch = wb.add_chart({'type': 'column'})
                                ch.add_series({
                                    'name': 'Обращений/час',
                                    'categories': f"'Часы'!$A$2:$A${n+1}",
                                    'values': f"'Часы'!$C$2:$C${n+1}",
                                })
                                ch.add_series({
                                    'name': 'Обращений/час/день',
                                    'categories': f"'Часы'!$A$2:$A${n+1}",
                                    'values': f"'Часы'!$D$2:$D${n+1}",
                                })
                                ch.set_title({'name': 'Нагрузка по часам (МСК)'})
                                ch.set_size({'width': 900, 'height': 450})
                                ws2.insert_chart('F2', ch)
                            except Exception:
                                pass

                        # ── Лист 3: Дни ──
                        if not df_op.empty:
                            day_stats = df_op.groupby('Дата_рабочая').size().reset_index(name='Обращений')
                            day_stats = day_stats.sort_values('Обращений', ascending=False)
                            day_stats['День недели'] = day_stats['Дата_рабочая'].apply(get_weekday_name)
                            wd_order = ['Понедельник', 'Вторник', 'Среда', 'Четверг',
                                        'Пятница', 'Суббота', 'Воскресенье']
                            wd_stats = df_op.groupby(
                                df_op['Дата_рабочая'].apply(get_weekday_name)
                            ).size().reset_index(name='Обращений')
                            wd_stats.columns = ['День недели', 'Обращений']
                            wd_stats['_s'] = wd_stats['День недели'].apply(
                                lambda x: wd_order.index(x) if x in wd_order else 99)
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
                            wd_stats.to_excel(writer, sheet_name='Дни', index=False, startrow=sr+1)
                            for c, v in enumerate(wd_stats.columns):
                                ws3.write(sr+1, c, v, hdr)

                        # ── Лист 4: Жалобы детальные ──
                        p1_reset.to_excel(writer, sheet_name='Жалобы детальные', index=False)
                        ws4 = writer.sheets['Жалобы детальные']
                        for c, v in enumerate(p1_reset.columns):
                            ws4.write(0, c, v, hdr)
                        ws4.set_column('A:A', 35)
                        try:
                            cols_c = [c for c in p1_reset.columns if c not in ('Ресторан', 'ИТОГО')]
                            nr = len(p1_reset)
                            if cols_c and nr > 0:
                                ch2 = wb.add_chart({'type': 'bar', 'subtype': 'stacked'})
                                for ci, cn in enumerate(cols_c):
                                    ri = list(p1_reset.columns).index(cn)
                                    cl = xl_col_to_name(ri)
                                    ch2.add_series({
                                        'name': str(cn),
                                        'categories': f"'Жалобы детальные'!$A$2:$A${nr+1}",
                                        'values': f"'Жалобы детальные'!${cl}$2:${cl}${nr+1}",
                                    })
                                ch2.set_title({'name': 'Детальные жалобы по ресторанам'})
                                ch2.set_size({'width': 900, 'height': 600})
                                ws4.insert_chart('H2', ch2)
                        except Exception:
                            pass

                        # ── Лист 5: Жалобы укрупнённые ──
                        p2_reset.to_excel(writer, sheet_name='Жалобы укрупнённые', index=False)
                        ws5 = writer.sheets['Жалобы укрупнённые']
                        for c, v in enumerate(p2_reset.columns):
                            ws5.write(0, c, v, hdr)
                        ws5.set_column('A:A', 35)
                        try:
                            cols_c2 = [c for c in p2_reset.columns if c not in ('Ресторан', 'ИТОГО')]
                            nr2 = len(p2_reset)
                            if cols_c2 and nr2 > 0:
                                ch3 = wb.add_chart({'type': 'bar', 'subtype': 'stacked'})
                                for ci, cn in enumerate(cols_c2):
                                    ri = list(p2_reset.columns).index(cn)
                                    cl = xl_col_to_name(ri)
                                    ch3.add_series({
                                        'name': str(cn),
                                        'categories': f"'Жалобы укрупнённые'!$A$2:$A${nr2+1}",
                                        'values': f"'Жалобы укрупнённые'!${cl}$2:${cl}${nr2+1}",
                                    })
                                ch3.set_title({'name': 'Укрупнённые жалобы по ресторанам'})
                                ch3.set_size({'width': 800, 'height': 500})
                                ws5.insert_chart('H2', ch3)
                        except Exception:
                            pass

                        # ── Лист 6: Бот ──
                        if not bot_df.empty:
                            bot_df.to_excel(writer, sheet_name='Бот', index=False)
                            ws6 = writer.sheets['Бот']
                            for c, v in enumerate(bot_df.columns):
                                ws6.write(0, c, v, hdr)
                            ws6.set_column('A:A', 15)
                            ws6.set_column('B:B', 20)
                            ws6.set_column('C:C', 30)
                            ws6.set_column('D:D', 60)
                            ws6.set_column('E:E', 22)

                except Exception as e:
                    st.error(f"Ошибка при формировании Excel: {e}")
                    return

                buf.seek(0)
                st.download_button(
                    label="💾 Скачать отчёт (.xlsx)",
                    data=buf,
                    file_name="OS_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                st.balloons()


if __name__ == "__main__":
    main()
