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

st.set_page_config(page_title="Пиццамейкер", page_icon="🍕", layout="wide")

# --- CSS (анимации однострочные) ---
st.markdown("""
<style>
.ingredient-btn { width: 100%; height: 80px; font-size: 22px; font-weight: 800; border-radius: 12px; transition: all 0.1s; color: #111111; }
.ingredient-btn:hover { transform: scale(1.03); }
.ingredient-correct { background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); color: white !important; border: none; }
.ingredient-wrong { background: linear-gradient(135deg, #f44336 0%, #da190b 100%); color: white !important; border: none; }
.ingredient-neutral { background: linear-gradient(135deg, #ffffff 0%, #f0f0f0 100%); border: 2px solid #ccc; color: #111111 !important; }
.pizza-display { background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); padding: 30px; border-radius: 16px; text-align: center; border: 3px solid #ff9800; }
.pizza-display h2 { margin: 0; color: #e65100; }
.pizza-display-bonus { background: linear-gradient(135deg, #fff9c4 0%, #fff176 100%); padding: 30px; border-radius: 16px; text-align: center; border: 3px solid #fbc02d; }
.pizza-display-bonus h2 { margin: 0; color: #f57f17; }
.level-complete-banner { background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); padding: 30px; border-radius: 16px; text-align: center; border: 3px solid #2e7d32; margin-bottom: 20px; }
.level-complete-banner h2 { margin: 0; color: white; font-size: 32px; }
.level-complete-banner p { margin: 10px 0 0 0; color: white; font-size: 18px; }
.game-over-banner { background: linear-gradient(135deg, #f44336 0%, #da190b 100%); padding: 30px; border-radius: 16px; text-align: center; border: 3px solid #c62828; margin-bottom: 20px; }
.game-over-banner h2 { margin: 0; color: white; font-size: 32px; }
.game-over-banner p { margin: 10px 0 0 0; color: white; font-size: 18px; }
.life-bonus-banner { background: linear-gradient(135deg, #e91e63 0%, #c2185b 100%); padding: 25px; border-radius: 16px; text-align: center; border: 3px solid #880e4f; margin: 20px 0; }
.life-bonus-banner h3 { margin: 0; color: white; font-size: 28px; }
.life-bonus-banner p { margin: 10px 0 0 0; color: white; font-size: 20px; font-weight: bold; }
.stat-box { background: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center; border-left: 4px solid #ff9800; }
.stat-box h4 { margin: 0 0 5px 0; color: #666; font-size: 14px; }
.stat-box p { margin: 0; font-size: 28px; font-weight: bold; color: #333; }
.progress-container { background: #e0e0e0; border-radius: 10px; height: 30px; margin: 10px 0; overflow: hidden; }
.progress-bar { background: linear-gradient(90deg, #ff9800 0%, #f57c00 100%); height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; transition: width 0.3s; }
.level-badge { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin-bottom: 10px; }
.level-easy { background: #c8e6c9; color: #2e7d32; }
.level-hard { background: #ffcdd2; color: #c62828; }
</style>
""", unsafe_allow_html=True)

# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ---
if 'game_active' not in st.session_state: st.session_state.game_active = False
if 'current_level' not in st.session_state: st.session_state.current_level = None
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
if 'lost_lives' not in st.session_state: st.session_state.lost_lives = False
if 'time_expired' not in st.session_state: st.session_state.time_expired = False
if 'success_completed' not in st.session_state: st.session_state.success_completed = False

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_random_pizzas(category, count=4):
    if category == 'easy':
        all_pizzas = [p for p in PIZZAS_PAPA_JOHNS if len(PIZZAS_PAPA_JOHNS[p]) <= 6]
    else:
        all_pizzas = [p for p in PIZZAS_PAPA_JOHNS if len(PIZZAS_PAPA_JOHNS[p]) >= 5]
    return random.sample(all_pizzas, min(count, len(all_pizzas)))

def get_bonus_pizza_for_easy():
    candidates = [p for p in PIZZAS_PAPA_JOHNS if len(PIZZAS_PAPA_JOHNS[p]) >= 5]
    return random.choice(candidates) if candidates else None

def get_bonus_pizza_for_hard():
    candidates = [p for p in PIZZAS_PAPA_JOHNS if len(PIZZAS_PAPA_JOHNS[p]) >= 7]
    return random.choice(candidates) if candidates else None

# --- ЛОГИКА ИГРЫ ---
def start_game(level):
    """Полный сброс и начало уровня с нуля (3 жизни, 0 очков)"""
    st.session_state.game_active = True
    st.session_state.current_level = level
    st.session_state.score = 0
    st.session_state.lives = 3  
    st.session_state.start_time = datetime.datetime.now().timestamp()
    st.session_state.bonus_completed = False
    st.session_state.level_completed = False
    st.session_state.lost_lives = False
    st.session_state.time_expired = False
    st.session_state.success_completed = False
    
    st.session_state.pizza_list = get_random_pizzas(level, count=4)
    st.session_state.pizza_index = 0
    st.session_state.current_pizza = st.session_state.pizza_list[0]
    st.session_state.ingredients_shown = []
    st.session_state.current_ingredients = generate_ingredients()
    st.rerun()

def next_level():
    """Переход с Лёгкого на Сложный С СОХРАНЕНИЕМ очков и жизней"""
    st.session_state.game_active = True
    st.session_state.current_level = 'hard'
    st.session_state.start_time = datetime.datetime.now().timestamp()
    st.session_state.bonus_completed = False
    st.session_state.level_completed = False
    st.session_state.lost_lives = False
    st.session_state.time_expired = False
    st.session_state.success_completed = False
    
    st.session_state.pizza_list = get_random_pizzas('hard', count=4)
    st.session_state.pizza_index = 0
    st.session_state.current_pizza = st.session_state.pizza_list[0]
    st.session_state.ingredients_shown = []
    st.session_state.current_ingredients = generate_ingredients()
    st.rerun()

def end_game():
    """Завершение игры по времени"""
    st.session_state.game_active = False
    st.session_state.time_expired = True
    st.session_state.current_pizza = None
    st.session_state.ingredients_shown = []
    st.session_state.current_ingredients = []
    st.rerun()

def success_game():
    """Успешное завершение игры (бонусная пицца собрана)"""
    st.session_state.game_active = False
    st.session_state.success_completed = True
    st.session_state.current_pizza = None
    st.session_state.ingredients_shown = []
    st.session_state.current_ingredients = []
    st.rerun()

def game_over():
    """Проигрыш - жизни закончились"""
    st.session_state.game_active = False
    st.session_state.lost_lives = True
    st.session_state.current_pizza = None
    st.session_state.ingredients_shown = []
    st.session_state.current_ingredients = []
    st.rerun()

def next_pizza():
    st.session_state.pizza_index += 1
    if st.session_state.pizza_index >= len(st.session_state.pizza_list):
        st.session_state.level_completed = True
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
            
            if len(st.session_state.ingredients_shown) == len(correct_ingredients):
                if st.session_state.level_completed:
                    st.session_state.score += 30
                    st.session_state.lives = 4  # ИСПРАВЛЕНО: всегда 3 базовые + 1 бонусная = 4
                    st.session_state.bonus_completed = True
                    success_game()
                else:
                    st.session_state.score += 50
                    next_pizza()
    else:
        st.session_state.lives -= 1
        if st.session_state.lives <= 0:
            game_over()
            return
    st.rerun()

def generate_ingredients():
    if not st.session_state.current_pizza:
        return []
    correct = PIZZAS_PAPA_JOHNS[st.session_state.current_pizza]
    wrong = [ing for ing in ALL_INGREDIENTS_PJ if ing not in correct]
    
    selected_correct = list(correct)
    num_wrong_needed = max(0, 12 - len(selected_correct))
    num_wrong = min(num_wrong_needed, len(wrong))
    selected_wrong = random.sample(wrong, num_wrong) if num_wrong > 0 else []
    
    ingredients = selected_correct + selected_wrong
    random.shuffle(ingredients)
    return ingredients

# --- ИНТЕРФЕЙС ---
st.title("🍕 Пиццамейкер")
st.caption(f"Тренажёр знания меню | Время МСК: {now_moscow.strftime('%H:%M:%S')}")

# Определяем, где мы находимся: главное меню или экран результатов
is_main_menu = not st.session_state.game_active and st.session_state.current_level is None

if is_main_menu:
    # --- ГЛАВНОЕ МЕНЮ ---
    st.markdown("### 🎮 Выберите режим игры:")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="level-badge level-easy">🟢 ЛЁГКИЙ УРОВЕНЬ</div>', unsafe_allow_html=True)
        st.markdown("**4 случайные пиццы** (до 6 ингредиентов)\n🎁 Бонусная пицца в конце\n🎁 +30 очков, +1 жизнь за бонус")
        if st.button("🚀 НАЧАТЬ ЛЁГКИЙ", use_container_width=True, type="primary"):
            start_game('easy')
            
    with col2:
        st.markdown('<div class="level-badge level-hard">🔴 СЛОЖНЫЙ УРОВЕНЬ</div>', unsafe_allow_html=True)
        st.markdown("**4 случайные пиццы** (5+ ингредиентов)\n🎁 Бонусная пицца в конце\n🎁 +30 очков, +1 жизнь за бонус")
        if st.button("🔥 НАЧАТЬ СЛОЖНЫЙ", use_container_width=True, type="primary"):
            start_game('hard')
            
    st.markdown("---")
    st.markdown("###  Правила:")
    st.info("1. В каждом уровне **4 случайные пиццы**.\n2. Угадывайте ингредиенты по памяти.\n3. Правильный клик: **+10 очков**, неправильный: **-1 жизнь**.\n4. Собрали все: **+50 бонус** и следующая пицца.\n5. Пройдя 4 пиццы → **бонусная пицца** (+30 очков, +1 жизнь).\n6. У вас **60 секунд** на уровень.\n7. Жизни обновляются при старте уровня (начинаете с 3❤️).")

elif not st.session_state.game_active:
    # --- ЭКРАН РЕЗУЛЬТАТОВ ---
    is_fail = st.session_state.lost_lives or st.session_state.time_expired
    is_success = st.session_state.success_completed
    is_easy_success = st.session_state.current_level == 'easy' and is_success
    is_hard_finish = st.session_state.current_level == 'hard' and is_success

    if is_fail:
        banner = '<div class="game-over-banner"><h2>💀 УРОВЕНЬ ПРОВАЛЕН!</h2><p>Жизни или время закончились.</p></div>'
    elif is_easy_success:
        banner = '<div class="level-complete-banner"><h2> ЛЁГКИЙ УРОВЕНЬ ПРОЙДЕН!</h2><p>Вы собрали бонусную пиццу!</p></div>'
    elif is_hard_finish:
        banner = '<div class="level-complete-banner"><h2>🏆 ПОЗДРАВЛЯЕМ!</h2><p>Вы прошли оба уровня!</p></div>'
    else:
        banner = '<div class="level-complete-banner"><h2>🎉 УРОВЕНЬ ЗАВЕРШЁН!</h2><p>Отличная работа!</p></div>'

    st.markdown(banner, unsafe_allow_html=True)

    # Показываем добавление жизни для успешного прохождения лёгкого уровня
    if is_easy_success:
        st.markdown(f"""
        <div class="life-bonus-banner">
            <h3>❤️ +1 БОНУСНАЯ ЖИЗНЬ ДОБАВЛЕНА!</h3>
            <p>3 базовые + 1 бонусная = {'❤️' * st.session_state.lives} жизней для сложного уровня!</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📊 Результаты:")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Итоговый счёт", st.session_state.score)
    with col2:
        st.metric("Жизни для следующего уровня", f"{'❤️' * st.session_state.lives}")
    with col3:
        st.metric("Этап", "Лёгкий" if st.session_state.current_level == 'easy' else "Сложный")

    st.markdown("---")

    # Кнопки управления в зависимости от ситуации
    if is_fail:
        level_to_retry = st.session_state.current_level
        if st.button(f"🔄 Попробовать {level_to_retry} уровень снова", use_container_width=True, type="primary"):
            start_game(level_to_retry)
            
    elif is_easy_success:
        st.markdown(f"### ➡️ Переход на сложный уровень с **{st.session_state.lives} жизнями** (3 базовые + 1 бонусная)!")
        if st.button("➡️ ПЕРЕЙТИ К СЛОЖНОМУ УРОВНЮ", use_container_width=True, type="primary"):
            next_level()
            
    elif is_hard_finish:
        if st.button("🔄 Играть с самого начала", use_container_width=True, type="primary"):
            st.session_state.score = 0
            st.session_state.current_level = None
            st.session_state.game_active = False
            st.session_state.lost_lives = False
            st.session_state.time_expired = False
            st.session_state.bonus_completed = False
            st.session_state.level_completed = False
            st.session_state.success_completed = False
            st.rerun()
    else:
        if st.button("🔄 Играть снова", use_container_width=True, type="primary"):
            st.session_state.score = 0
            st.session_state.current_level = None
            st.session_state.game_active = False
            st.session_state.lost_lives = False
            st.session_state.time_expired = False
            st.session_state.bonus_completed = False
            st.session_state.level_completed = False
            st.session_state.success_completed = False
            st.rerun()

else:
    # --- ИГРОВОЙ ЭКРАН ---
    elapsed = int(datetime.datetime.now().timestamp() - st.session_state.start_time)
    time_left = max(0, 100 - elapsed)
    
    if time_left == 0 and st.session_state.game_active:
        end_game()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-box"><h4>💰 Очки</h4><p>{st.session_state.score}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-box"><h4>❤️ Жизни</h4><p>{"❤️" * st.session_state.lives}</p></div>', unsafe_allow_html=True)
    with col3:
        time_color = "#f44336" if time_left < 10 else "#333"
        st.markdown(f'<div class="stat-box"><h4>⏱️ Время</h4><p style="color:{time_color}">{time_left}с</p></div>', unsafe_allow_html=True)
    with col4:
        if st.session_state.level_completed:
            st.markdown(f'<div class="stat-box"><h4>🎁 БОНУС</h4><p></p></div>', unsafe_allow_html=True)
        else:
            total = len(st.session_state.pizza_list)
            current = st.session_state.pizza_index + 1
            st.markdown(f'<div class="stat-box"><h4>🍕 Пиццы</h4><p>{current}/{total}</p></div>', unsafe_allow_html=True)
    
    if not st.session_state.level_completed:
        total_pizzas = len(st.session_state.pizza_list)
        completed_pizzas = st.session_state.pizza_index
        progress_percent = (completed_pizzas / total_pizzas) * 100
        st.markdown(f"""
        <div class="progress-container">
            <div class="progress-bar" style="width: {progress_percent}%;">
                {completed_pizzas} из {total_pizzas} пицц
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.session_state.level_completed:
        st.markdown("""
        <div class="level-complete-banner">
            <h2>🎉 УРОВЕНЬ ПРОЙДЕН!</h2>
            <p>Отличная работа! Теперь бонусная пицца по памяти</p>
        </div>
        """, unsafe_allow_html=True)
    
    is_bonus = st.session_state.level_completed
    display_class = "pizza-display-bonus" if is_bonus else "pizza-display"
    title_prefix = "🎁 БОНУСНАЯ ПИЦЦА" if is_bonus else "🍕"
    
    st.markdown(f"""
    <div class="{display_class}">
        <h2>{title_prefix} {st.session_state.current_pizza}</h2>
        <p style="font-size: 16px; color: #666; margin-top: 10px;">
            Угадайте все ингредиенты этой пиццы!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🧂 Выберите ингредиенты:")
    ingredients = st.session_state.current_ingredients
    num_rows = (len(ingredients) + 3) // 4
    
    for row in range(num_rows):
        cols = st.columns(4)
        for col_idx in range(4):
            ing_idx = row * 4 + col_idx
            if ing_idx < len(ingredients):
                ingredient = ingredients[ing_idx]
                btn_type = "primary" if ingredient in st.session_state.ingredients_shown else "secondary"
                
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