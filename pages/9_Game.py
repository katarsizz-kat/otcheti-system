import streamlit as st
import datetime
import random
import sys
import os

# Добавляем корневую директорию в путь для импорта config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.pizzas import PIZZAS_PAPA_JOHNS, ALL_INGREDIENTS_PJ

# --- ВРЕМЯ (UTC+3) ---
moscow_tz = datetime.timezone(datetime.timedelta(hours=3))
now_moscow = datetime.datetime.now(moscow_tz)

st.set_page_config(page_title="Пиццамейкер | Papa John's", page_icon="🍕", layout="wide")

# --- CSS (анимации однострочные) ---
st.markdown("""
<style>
.ingredient-btn { width: 100%; height: 80px; font-size: 16px; font-weight: bold; border-radius: 12px; transition: all 0.1s; }
.ingredient-btn:hover { transform: scale(1.03); }
.ingredient-correct { background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); color: white; border: none; }
.ingredient-wrong { background: linear-gradient(135deg, #f44336 0%, #da190b 100%); color: white; border: none; }
.ingredient-neutral { background: linear-gradient(135deg, #fff 0%, #f5f5f5 100%); border: 2px solid #ddd; color: #333; }
.pizza-display { background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); padding: 30px; border-radius: 16px; text-align: center; border: 3px solid #ff9800; }
.pizza-display h2 { margin: 0; color: #e65100; }
.pizza-display-bonus { background: linear-gradient(135deg, #fff9c4 0%, #fff176 100%); padding: 30px; border-radius: 16px; text-align: center; border: 3px solid #fbc02d; }
.pizza-display-bonus h2 { margin: 0; color: #f57f17; }
.stat-box { background: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center; border-left: 4px solid #ff9800; }
.stat-box h4 { margin: 0 0 5px 0; color: #666; font-size: 14px; }
.stat-box p { margin: 0; font-size: 28px; font-weight: bold; color: #333; }
.level-badge { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin-bottom: 10px; }
.level-easy { background: #c8e6c9; color: #2e7d32; }
.level-hard { background: #ffcdd2; color: #c62828; }
</style>
""", unsafe_allow_html=True)

# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ---
if 'game_active' not in st.session_state: st.session_state.game_active = False
if 'current_level' not in st.session_state: st.session_state.current_level = None  # 'easy' или 'hard'
if 'current_pizza' not in st.session_state: st.session_state.current_pizza = None
if 'pizza_index' not in st.session_state: st.session_state.pizza_index = 0
if 'pizza_list' not in st.session_state: st.session_state.pizza_list = []
if 'score' not in st.session_state: st.session_state.score = 0
if 'lives' not in st.session_state: st.session_state.lives = 3
if 'start_time' not in st.session_state: st.session_state.start_time = 0
if 'ingredients_shown' not in st.session_state: st.session_state.ingredients_shown = []
if 'current_ingredients' not in st.session_state: st.session_state.current_ingredients = []
if 'bonus_pizza' not in st.session_state: st.session_state.bonus_pizza = None
if 'bonus_completed' not in st.session_state: st.session_state.bonus_completed = False
if 'level_completed' not in st.session_state: st.session_state.level_completed = False

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_pizzas_by_difficulty():
    """Возвращает пиццы, отсортированные по количеству ингредиентов"""
    pizzas = list(PIZZAS_PAPA_JOHNS.keys())
    pizzas.sort(key=lambda p: len(PIZZAS_PAPA_JOHNS[p]))
    return pizzas

def get_easy_pizzas():
    """Лёгкие и средние пиццы (≤6 ингредиентов)"""
    return [p for p in get_pizzas_by_difficulty() if len(PIZZAS_PAPA_JOHNS[p]) <= 6]

def get_hard_pizzas():
    """Сложные пиццы (7+ ингредиентов)"""
    return [p for p in get_pizzas_by_difficulty() if len(PIZZAS_PAPA_JOHNS[p]) >= 7]

def get_bonus_pizza_for_easy():
    """Бонусная пицца для лёгкого уровня (средняя или сложная)"""
    candidates = [p for p in PIZZAS_PAPA_JOHNS if len(PIZZAS_PAPA_JOHNS[p]) >= 5]
    return random.choice(candidates) if candidates else None

def get_bonus_pizza_for_hard():
    """Бонусная пицца для сложного уровня (сложная)"""
    candidates = get_hard_pizzas()
    return random.choice(candidates) if candidates else None

# --- ЛОГИКА ИГРЫ ---
def start_game(level):
    st.session_state.game_active = True
    st.session_state.current_level = level
    st.session_state.score = 0
    st.session_state.lives = 3
    st.session_state.start_time = datetime.datetime.now().timestamp()
    st.session_state.bonus_completed = False
    st.session_state.level_completed = False
    
    if level == 'easy':
        st.session_state.pizza_list = get_pizzas_by_difficulty()  # Все пиццы
    else:  # hard
        st.session_state.pizza_list = get_easy_pizzas()  # Только лёгкие и средние
    
    st.session_state.pizza_index = 0
    st.session_state.current_pizza = st.session_state.pizza_list[0]
    st.session_state.ingredients_shown = []
    st.session_state.current_ingredients = generate_ingredients()
    st.rerun()

def next_level():
    """Переход к следующему уровню"""
    if st.session_state.current_level == 'easy':
        start_game('hard')
    else:
        # Игра завершена после сложного уровня
        st.session_state.game_active = False
        st.rerun()

def end_game():
    st.session_state.game_active = False
    st.session_state.current_pizza = None
    st.session_state.ingredients_shown = []
    st.session_state.current_ingredients = []
    st.rerun()

def next_pizza():
    """Переход к следующей пицце"""
    st.session_state.pizza_index += 1
    
    if st.session_state.pizza_index >= len(st.session_state.pizza_list):
        # Все пиццы уровня пройдены
        st.session_state.level_completed = True
        
        # Назначаем бонусную пиццу
        if st.session_state.current_level == 'easy':
            st.session_state.bonus_pizza = get_bonus_pizza_for_easy()
        else:
            st.session_state.bonus_pizza = get_bonus_pizza_for_hard()
        
        st.session_state.current_pizza = st.session_state.bonus_pizza
        st.session_state.ingredients_shown = []
        st.session_state.current_ingredients = generate_ingredients()
    else:
        st.session_state.current_pizza = st.session_state.pizza_list[st.session_state.pizza_index]
        st.session_state.ingredients_shown = []
        st.session_state.current_ingredients = generate_ingredients()
    
    st.rerun()

def check_ingredient(ingredient):
    if not st.session_state.game_active:
        return
    
    correct_ingredients = PIZZAS_PAPA_JOHNS[st.session_state.current_pizza]
    
    if ingredient in correct_ingredients:
        if ingredient not in st.session_state.ingredients_shown:
            st.session_state.ingredients_shown.append(ingredient)
            st.session_state.score += 10
            
            # Проверка: все ли ингредиенты собраны
            if len(st.session_state.ingredients_shown) == len(correct_ingredients):
                if st.session_state.level_completed:
                    # Это бонусная пицца
                    st.session_state.score += 30
                    st.session_state.lives += 1
                    st.session_state.bonus_completed = True
                    end_game()
                else:
                    # Обычная пицца
                    st.session_state.score += 50
                    next_pizza()
    else:
        st.session_state.lives -= 1
        if st.session_state.lives <= 0:
            end_game()
            return
            
    st.rerun()

def generate_ingredients():
    """Генерирует карточки: ВСЕ правильные + случайные неправильные до 8 штук"""
    if not st.session_state.current_pizza:
        return []
    
    correct = PIZZAS_PAPA_JOHNS[st.session_state.current_pizza]
    wrong = [ing for ing in ALL_INGREDIENTS_PJ if ing not in correct]
    
    selected_correct = list(correct)
    num_wrong_needed = max(0, 8 - len(selected_correct))
    num_wrong = min(num_wrong_needed, len(wrong))
    
    selected_wrong = random.sample(wrong, num_wrong) if num_wrong > 0 else []
    
    ingredients = selected_correct + selected_wrong
    random.shuffle(ingredients)
    return ingredients

# --- ИНТЕРФЕЙС ---
st.title("🍕 Пиццамейкер: Papa John's")
st.caption(f"Тренажёр знания меню | Время МСК: {now_moscow.strftime('%H:%M:%S')}")

if not st.session_state.game_active:
    # --- ЭКРАН СТАРТА ---
    st.markdown("### 🎮 Выберите уровень сложности:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="level-badge level-easy">🟢 ЛЁГКИЙ УРОВЕНЬ</div>
        """, unsafe_allow_html=True)
        st.markdown("""
        **Все пиццы** от простых к сложным  
        ✅ Ингредиенты показаны  
        ✅ Бонусная пицца по памяти  
        🎁 +30 очков, +1 жизнь за бонус
        """)
        if st.button("🚀 НАЧАТЬ ЛЁГКИЙ", use_container_width=True, type="primary"):
            start_game('easy')
    
    with col2:
        st.markdown("""
        <div class="level-badge level-hard">🔴 СЛОЖНЫЙ УРОВЕНЬ</div>
        """, unsafe_allow_html=True)
        st.markdown("""
        **Лёгкие и средние пиццы**  
        ❌ Ингредиенты НЕ показаны  
        ✅ Бонусная сложная пицца  
        🎁 +30 очков, +1 жизнь за бонус
        """)
        if st.button("🔥 НАЧАТЬ СЛОЖНЫЙ", use_container_width=True, type="primary"):
            start_game('hard')
    
    st.markdown("---")
    st.markdown("### 📜 Правила:")
    st.info("""
    1. Угадывайте ингредиенты пицц по порядку (от простых к сложным)
    2. Правильный клик: **+10 очков**, неправильный: **-1 жизнь**
    3. Собрали все ингредиенты: **+50 бонус** и следующая пицца
    4. Пройдя все пиццы уровня → **бонусная пицца** (только название, угадывайте по памяти)
    5. Бонусная пицца: **+30 очков, +1 жизнь**
    6. У вас **60 секунд** на уровень
    7. Жизни обновляются каждый уровень (начинаете с 3❤️)
    """)

else:
    # --- ИГРОВОЙ ЭКРАН ---
    
    # Расчет времени
    elapsed = int(datetime.datetime.now().timestamp() - st.session_state.start_time)
    time_left = max(0, 30 - elapsed)
    
    if time_left == 0 and st.session_state.game_active:
        end_game()
    
    # Статистика сверху
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-box"><h4>💰 Очки</h4><p>{st.session_state.score}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-box"><h4>❤️ Жизни</h4><p>{"❤️" * st.session_state.lives}</p></div>', unsafe_allow_html=True)
    with col3:
        time_color = "#f44336" if time_left < 15 else "#333"
        st.markdown(f'<div class="stat-box"><h4>⏱️ Время</h4><p style="color:{time_color}">{time_left}с</p></div>', unsafe_allow_html=True)
    with col4:
        if st.session_state.level_completed:
            st.markdown(f'<div class="stat-box"><h4>🎁 БОНУС</h4><p>🌟</p></div>', unsafe_allow_html=True)
        else:
            total = len(st.session_state.pizza_list)
            current = st.session_state.pizza_index + 1
            st.markdown(f'<div class="stat-box"><h4>🍕 Пицца</h4><p>{current}/{total}</p></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Показ текущей пиццы
    is_bonus = st.session_state.level_completed
    is_hard_level = st.session_state.current_level == 'hard'
    show_ingredients_hint = not (is_bonus or is_hard_level)
    
    if is_bonus:
        display_class = "pizza-display-bonus"
        title_prefix = "🎁 БОНУСНАЯ ПИЦЦА"
    else:
        display_class = "pizza-display"
        title_prefix = "🍕"
    
    correct_ingredients_list = PIZZAS_PAPA_JOHNS[st.session_state.current_pizza]
    
    if show_ingredients_hint:
        # Показываем состав
        st.markdown(f"""
        <div class="{display_class}">
            <h2>{title_prefix} {st.session_state.current_pizza}</h2>
            <p style="font-size: 14px; color: #666; margin-top: 10px;">
                Найдите все {len(correct_ingredients_list)} ингредиентов среди карточек ниже!
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Только название (бонус или сложный уровень)
        st.markdown(f"""
        <div class="{display_class}">
            <h2>{title_prefix} {st.session_state.current_pizza}</h2>
            <p style="font-size: 16px; color: #f57f17; margin-top: 10px; font-weight: bold;">
                ⚠️ Угадайте ингредиенты по памяти!
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("### 🧂 Выберите ингредиенты:")
    
    ingredients = st.session_state.current_ingredients
    
    # Динамическая сетка
    num_rows = (len(ingredients) + 3) // 4
    for row in range(num_rows):
        cols = st.columns(4)
        for col_idx in range(4):
            ing_idx = row * 4 + col_idx
            if ing_idx < len(ingredients):
                ingredient = ingredients[ing_idx]
                
                if ingredient in st.session_state.ingredients_shown:
                    btn_type = "primary"
                else:
                    btn_type = "secondary"
                
                with cols[col_idx]:
                    if st.button(
                        ingredient,
                        key=f"ing_{ing_idx}_{ingredient}_{st.session_state.current_pizza}",
                        use_container_width=True,
                        type=btn_type
                    ):
                        check_ingredient(ingredient)
    
    st.markdown("---")
    
    if st.button("🏁 Завершить игру досрочно", use_container_width=True):
        end_game()

# --- ЭКРАН РЕЗУЛЬТАТОВ ---
if not st.session_state.game_active and st.session_state.score > 0:
    st.markdown("---")
    st.markdown("## 🏆 Уровень завершён!")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Итоговый счёт", st.session_state.score)
    with col2:
        st.metric("Осталось жизней", st.session_state.lives)
    with col3:
        if st.session_state.bonus_completed:
            st.success("🌟 Бонусная пицца собрана!")
        elif st.session_state.level_completed:
            st.info("👍 Уровень пройден!")
        else:
            st.warning("💪 Попробуйте ещё раз!")
    
    if st.session_state.current_level == 'easy' and not st.session_state.bonus_completed:
        if st.button("➡️ ПЕРЕХОД К СЛОЖНОМУ УРОВНЮ", use_container_width=True, type="primary"):
            next_level()
    else:
        if st.button("🔄 Играть снова", use_container_width=True, type="primary"):
            st.session_state.score = 0
            st.rerun()