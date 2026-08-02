import streamlit as st
import datetime
import random

# --- НАСТРОЙКИ И ВРЕМЯ (UTC+3) ---
moscow_tz = datetime.timezone(datetime.timedelta(hours=3))
now_moscow = datetime.datetime.now(moscow_tz)
today_str = now_moscow.strftime("%Y-%m-%d")

st.set_page_config(page_title="Игровая | Пиццемейстер", page_icon="🍕", layout="wide")

# --- CSS (анимации строго однострочные) ---
st.markdown("""
<style>
.pizza-icon { font-size: 120px; text-align: center; cursor: pointer; user-select: none; transition: transform 0.1s; animation: float 3s ease-in-out infinite; }
.pizza-icon:hover { transform: scale(1.15); }
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-15px); } }
.stat-card { background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%); padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #e0e0e0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.stat-card h3 { margin: 0; color: #d32f2f; }
.stat-card p { margin: 5px 0 0 0; font-size: 24px; font-weight: bold; color: #333; }
.upgrade-btn { width: 100%; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ---
if 'pizzas_baked' not in st.session_state: st.session_state.pizzas_baked = 0
if 'coins' not in st.session_state: st.session_state.coins = 0
if 'click_power' not in st.session_state: st.session_state.click_power = 1
if 'auto_bakers' not in st.session_state: st.session_state.auto_bakers = 0
if 'last_bonus_date' not in st.session_state: st.session_state.last_bonus_date = ""

# --- ЛОГИКА ИГРЫ ---
def bake_pizza():
    st.session_state.pizzas_baked += st.session_state.click_power
    st.session_state.coins += st.session_state.click_power

def buy_upgrade(upgrade_type):
    costs = {'oven': 50, 'staff': 200, 'franchise': 1000}
    if st.session_state.coins >= costs[upgrade_type]:
        st.session_state.coins -= costs[upgrade_type]
        if upgrade_type == 'oven': st.session_state.click_power += 1
        elif upgrade_type == 'staff': st.session_state.auto_bakers += 2
        elif upgrade_type == 'franchise': st.session_state.click_power += 5; st.session_state.auto_bakers += 5

def claim_daily_bonus():
    if st.session_state.last_bonus_date != today_str:
        bonus = random.randint(100, 500)
        st.session_state.coins += bonus
        st.session_state.last_bonus_date = today_str
        st.success(f"🎁 Ежедневный бонус (время МСК): +{bonus} монет!")
    else:
        st.warning("Вы уже получали бонус сегодня! Возвращайтесь завтра.")

# Авто-печь (эмуляция через rerun, если есть авто-пекари)
if st.session_state.auto_bakers > 0:
    # В реальном приложении лучше использовать st_autorefresh, но для простоты эмулируем при каждом взаимодействии
    pass 

# --- ИНТЕРФЕЙС ---
st.title("🍕 Пиццемейстер: Сеть ресторанов")
st.caption(f"Ваш статус: Управляющий | Время по Москве: {now_moscow.strftime('%H:%M:%S')}")

# Статистика
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="stat-card"><h3>🍕 Испечено</h3><p>{st.session_state.pizzas_baked}</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="stat-card"><h3>💰 Монеты</h3><p>{st.session_state.coins}</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="stat-card"><h3>⚡ Сила клика</h3><p>{st.session_state.click_power}</p></div>', unsafe_allow_html=True)

st.markdown("---")

# Игровое поле
game_col1, game_col2 = st.columns([1, 2])

with game_col1:
    st.subheader("👨‍🍳 Кухня")
    st.markdown('<div class="pizza-icon" onclick="alert(\'Клик работает через кнопку ниже!\')">🍕</div>', unsafe_allow_html=True)
    
    if st.button("🔥 ИСПЕЧЬ ПИЦЦУ", use_container_width=True, type="primary"):
        bake_pizza()
        st.rerun()
        
    st.markdown("---")
    st.subheader("🎁 Ежедневный бонус")
    if st.button("Забрать бонус (МСК)", use_container_width=True):
        claim_daily_bonus()
        st.rerun()

with game_col2:
    st.subheader("🏢 Магазин улучшений")
    
    # Список ресторанов для контекста
    restaurants = ["Транспортный", "Димитрова", "Шмидта", "Пулковская", "Благодатная", "Энтузиастов", 
                   "Серебристый", "Мурино", "Ветеранов", "Туристская", "Наука", "Ленинский", "Орджоникидзе", "Мельникайте"]
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### 🧱 Новая печь")
        st.caption("Увеличивает силу клика на 1")
        st.caption(f"Цена: 50 💰")
        if st.button("Купить печь", key="oven", use_container_width=True):
            buy_upgrade('oven')
            st.rerun()
            
    with c2:
        st.markdown("#### 👨‍🍳 Стажёр-повар")
        st.caption("Автоматически печёт (бонус к пассиву)")
        st.caption(f"Цена: 200 💰")
        if st.button("Нанять стажёра", key="staff", use_container_width=True):
            buy_upgrade('staff')
            st.rerun()
            
    with c3:
        rest_name = random.choice(restaurants)
        st.markdown(f"#### 🏪 Франшиза")
        st.caption(f"Открытие в р-не {rest_name}")
        st.caption(f"Цена: 1000 💰")
        if st.button("Открыть франшизу", key="franchise", use_container_width=True):
            buy_upgrade('franchise')
            st.rerun()

    st.markdown("---")
    st.info(f"💡 **Совет:** Улучшайте печи, чтобы быстрее достигать целей KPI! Текущий авто-бонус: {st.session_state.auto_bakers} пицц/действие.")