import streamlit as st
import datetime
import random
import time

# --- ВРЕМЯ (UTC+3) ---
moscow_tz = datetime.timezone(datetime.timedelta(hours=3))
now_moscow = datetime.datetime.now(moscow_tz)

st.set_page_config(page_title="Пиццамейкер | Проверка ингредиентов", page_icon="🍕", layout="wide")

# --- CSS (анимации однострочные) ---
st.markdown("""
<style>
.ingredient-btn { width: 100%; height: 80px; font-size: 18px; font-weight: bold; border-radius: 12px; transition: all 0.2s; }
.ingredient-btn:hover { transform: scale(1.05); }
.ingredient-correct { background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); color: white; }
.ingredient-wrong { background: linear-gradient(135deg, #f44336 0%, #da190b 100%); color: white; }
.ingredient-neutral { background: linear-gradient(135deg, #fff 0%, #f5f5f5 100%); border: 2px solid #ddd; }
.pizza-display { background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); padding: 30px; border-radius: 16px; text-align: center; border: 3px solid #ff9800; }
.pizza-display h2 { margin: 0; color: #e65100; }
.stat-box { background: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center; border-left: 4px solid #ff9800; }
.stat-box h4 { margin: 0 0 5px 0; color: #666; font-size: 14px; }
.stat-box p { margin: 0; font-size: 28px; font-weight: bold; color: #333; }
@keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-5px); } 75% { transform: translateX(5px); } }
.shake { animation: shake 0.3s; }
</style>
""", unsafe_allow_html=True)

# --- БАЗА ПИЦЦ И ИНГРЕДИЕНТОВ ---
PIZZAS = {
    "Маргарита": ["Томатный соус", "Моцарелла", "Базилик", "Оливковое масло"],
    "Пепперони": ["Томатный соус", "Моцарелла", "Пепперони", "Орегано"],
    "4 сыра": ["Моцарелла", "Горгонзола", "Пармезан", "Чеддер", "Оливковое масло"],
    "Гавайская": ["Томатный соус", "Моцарелла", "Ветчина", "Ананасы"],
    "Мясная": ["Томатный соус", "Моцарелла", "Говядина", "Бекон", "Колбаса", "Лук"],
    "Вегетарианская": ["Томатный соус", "Моцарелла", "Грибы", "Перец", "Оливки", "Лук", "Томаты"],
    "Барбекю": ["Соус BBQ", "Моцарелла", "Курица", "Бекон", "Лук", "Перец"],
    "Морская": ["Томатный соус", "Моцарелла", "Креветки", "Мидии", "Кальмары", "Чеснок"]
}

ALL_INGREDIENTS = list(set([item for sublist in PIZZAS.values() for item in sublist]))

# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ---
if 'game_active' not in st.session_state: st.session_state.game_active = False
if 'current_pizza' not in st.session_state: st.session_state.current_pizza = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'lives' not in st.session_state: st.session_state.lives = 3
if 'time_left' not in st.session_state: st.session_state.time_left = 60
if 'ingredients_shown' not in st.session_state: st.session_state.ingredients_shown = []
if 'difficulty' not in st.session_state: st.session_state.difficulty = "normal"

# --- ЛОГИКА ИГРЫ ---
def start_game():
    st.session_state.game_active = True
    st.session_state.score = 0
    st.session_state.lives = 3
    st.session_state.time_left = 60
    st.session_state.current_pizza = random.choice(list(PIZZAS.keys()))
    st.session_state.ingredients_shown = []
    st.rerun()

def end_game():
    st.session_state.game_active = False
    st.session_state.current_pizza = None
    st.session_state.ingredients_shown = []
    st.rerun()

def check_ingredient(ingredient):
    if not st.session_state.game_active:
        return
    
    correct_ingredients = PIZZAS[st.session_state.current_pizza]
    
    if ingredient in correct_ingredients:
        if ingredient not in st.session_state.ingredients_shown:
            st.session_state.ingredients_shown.append(ingredient)
            st.session_state.score += 10
            
            # Проверка: все ли ингредиенты собраны
            if all(ing in st.session_state.ingredients_shown for ing in correct_ingredients):
                st.session_state.score += 50  # Бонус за полную пиццу
                st.session_state.current_pizza = random.choice(list(PIZZAS.keys()))
                st.session_state.ingredients_shown = []
    else:
        st.session_state.lives -= 1
        if st.session_state.lives <= 0:
            end_game()
    
    st.rerun()

def generate_ingredients():
    """Генерирует 8 ингредиентов: некоторые из пиццы, некоторые нет"""
    if not st.session_state.current_pizza:
        return []
    
    correct = PIZZAS[st.session_state.current_pizza]
    wrong = [ing for ing in ALL_INGREDIENTS if ing not in correct]
    
    # Берём 4 правильных и 4 неправильных (или сколько есть)
    num_correct = min(4, len(correct))
    num_wrong = min(4, len(wrong))
    
    selected_correct = random.sample(correct, num_correct)
    selected_wrong = random.sample(wrong, num_wrong)
    
    ingredients = selected_correct + selected_wrong
    random.shuffle(ingredients)
    return ingredients

# --- ИНТЕРФЕЙС ---
st.title("🍕 Пиццамейкер: Проверка ингредиентов")
st.caption(f"Тренажёр знания рецептуры | Время МСК: {now_moscow.strftime('%H:%M:%S')}")

if not st.session_state.game_active:
    # --- ЭКРАН СТАРТА ---
    st.markdown("### 🎮 Правила игры:")
    st.info("""
    1. Вам показывается название пиццы
    2. Появляются ингредиенты по очереди
    3. Кликайте **ТОЛЬКО** на те, что есть в этой пицце
    4. Правильный клик: **+10 очков**
    5. Неправильный клик: **-1 жизнь**
    6. Соберите все ингредиенты: **+50 бонус**
    7. Игра идёт 60 секунд
    """)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### ⚡ Сложность")
        difficulty = st.selectbox("Выберите уровень", ["Лёгкий (8 ингредиентов)", "Нормальный (8 ингредиентов)", "Сложный (8 ингредиентов)"], key="diff_select")
        st.session_state.difficulty = "normal"  # Можно расширить логику
    
    with col2:
        st.markdown("#### 📊 Статистика")
        st.metric("Рекорд", "—")  # Можно сохранять в session_state
        st.metric("Игр сыграно", "0")
    
    with col3:
        st.markdown("#### 🎯 Цель")
        st.success("Набрать максимум очков за 60 секунд!")
        st.warning("Не теряйте жизни!")
    
    if st.button("🚀 НАЧАТЬ ИГРУ", use_container_width=True, type="primary"):
        start_game()

else:
    # --- ИГРОВОЙ ЭКРАН ---
    
    # Статистика сверху
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-box"><h4>💰 Очки</h4><p>{st.session_state.score}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-box"><h4>❤️ Жизни</h4><p>{"❤️" * st.session_state.lives}</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-box"><h4>⏱️ Время</h4><p>{st.session_state.time_left}с</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-box"><h4>🍕 Собрано</h4><p>{len(st.session_state.ingredients_shown)}/{len(PIZZAS[st.session_state.current_pizza])}</p></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Показ текущей пиццы
    st.markdown(f"""
    <div class="pizza-display">
        <h2>🍕 {st.session_state.current_pizza}</h2>
        <p style="font-size: 18px; margin: 10px 0;">Состав: {', '.join(PIZZAS[st.session_state.current_pizza])}</p>
        <p style="font-size: 14px; color: #666;">Кликайте на правильные ингредиенты ниже!</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🧂 Выберите ингредиенты:")
    
    # Генерация и показ ингредиентов
    ingredients = generate_ingredients()
    
    # Создаём сетку 4x2
    for row in range(2):
        cols = st.columns(4)
        for col_idx in range(4):
            ing_idx = row * 4 + col_idx
            if ing_idx < len(ingredients):
                ingredient = ingredients[ing_idx]
                
                # Определяем стиль кнопки
                if ingredient in st.session_state.ingredients_shown:
                    btn_type = "primary"
                    btn_class = "ingredient-correct"
                else:
                    btn_type = "secondary"
                    btn_class = "ingredient-neutral"
                
                with cols[col_idx]:
                    if st.button(
                        ingredient,
                        key=f"ing_{ing_idx}_{ingredient}",
                        use_container_width=True,
                        type=btn_type
                    ):
                        check_ingredient(ingredient)
    
    st.markdown("---")
    
    # Кнопка завершения
    if st.button("🏁 Завершить игру", use_container_width=True):
        end_game()
    
    # Авто-уменьшение таймера (эмуляция)
    if st.session_state.time_left > 0:
        st.session_state.time_left -= 1
        time.sleep(1)
        st.rerun()
    else:
        end_game()

# --- ЭКРАН РЕЗУЛЬТАТОВ ---
if not st.session_state.game_active and st.session_state.score > 0:
    st.markdown("---")
    st.markdown("## 🏆 Игра окончена!")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Итоговый счёт", st.session_state.score)
    with col2:
        st.metric("Осталось жизней", st.session_state.lives)
    with col3:
        if st.session_state.score >= 500:
            st.success("🌟 Отличный результат!")
        elif st.session_state.score >= 200:
            st.info("👍 Хорошая работа!")
        else:
            st.warning("💪 Тренируйтесь ещё!")
    
    if st.button("🔄 Играть снова", use_container_width=True, type="primary"):
        st.session_state.score = 0
        st.rerun()