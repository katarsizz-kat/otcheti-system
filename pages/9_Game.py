import streamlit as st
import datetime
import random
import time
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
.ingredient-btn { width: 100%; height: 80px; font-size: 16px; font-weight: bold; border-radius: 12px; transition: all 0.2s; }
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

# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ---
if 'game_active' not in st.session_state: st.session_state.game_active = False
if 'current_pizza' not in st.session_state: st.session_state.current_pizza = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'lives' not in st.session_state: st.session_state.lives = 3
if 'time_left' not in st.session_state: st.session_state.time_left = 60
if 'ingredients_shown' not in st.session_state: st.session_state.ingredients_shown = []
if 'current_ingredients' not in st.session_state: st.session_state.current_ingredients = []

# --- ЛОГИКА ИГРЫ ---
def start_game():
    st.session_state.game_active = True
    st.session_state.score = 0
    st.session_state.lives = 3
    st.session_state.time_left = 60
    st.session_state.current_pizza = random.choice(list(PIZZAS_PAPA_JOHNS.keys()))
    st.session_state.ingredients_shown = []
    st.session_state.current_ingredients = generate_ingredients()
    st.rerun()

def end_game():
    st.session_state.game_active = False
    st.session_state.current_pizza = None
    st.session_state.ingredients_shown = []
    st.session_state.current_ingredients = []
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
                st.session_state.score += 50  # Бонус за полную пиццу
                st.session_state.current_pizza = random.choice(list(PIZZAS_PAPA_JOHNS.keys()))
                st.session_state.ingredients_shown = []
                st.session_state.current_ingredients = generate_ingredients()
    else:
        st.session_state.lives -= 1
        if st.session_state.lives <= 0:
            end_game()
    
    st.rerun()

def generate_ingredients():
    """Генерирует карточки: ВСЕ правильные ингредиенты + случайные неправильные до 8 штук"""
    if not st.session_state.current_pizza:
        return []
    
    correct = PIZZAS_PAPA_JOHNS[st.session_state.current_pizza]
    wrong = [ing for ing in ALL_INGREDIENTS_PJ if ing not in correct]
    
    # Берем все правильные ингредиенты
    selected_correct = list(correct)
    
    # Дополняем неправильными до 8 штук (или сколько есть в наличии)
    num_wrong_needed = max(0, 8 - len(selected_correct))
    num_wrong = min(num_wrong_needed, len(wrong))
    
    selected_wrong = random.sample(wrong, num_wrong)
    
    ingredients = selected_correct + selected_wrong
    random.shuffle(ingredients)
    return ingredients

# --- ИНТЕРФЕЙС ---
st.title("🍕 Пиццамейкер: Papa John's")
st.caption(f"Тренажёр знания реального состава | Время МСК: {now_moscow.strftime('%H:%M:%S')}")

if not st.session_state.game_active:
    # --- ЭКРАН СТАРТА ---
    st.markdown("### 🎮 Правила игры:")
    st.info("""
    1. Вам показывается название пиццы из реального меню
    2. На экране появляются карточки с ингредиентами
    3. Кликайте **ТОЛЬКО** на те, что реально есть в этой пицце
    4. Правильный клик: **+10 очков**
    5. Неправильный клик: **-1 жизнь**
    6. Собрали все правильные ингредиенты: **+50 бонус** и новая пицца
    7. Игра идёт 60 секунд
    """)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 📊 База знаний")
        st.metric("Всего пицц", len(PIZZAS_PAPA_JOHNS))
        st.metric("Уникальных ингредиентов", len(ALL_INGREDIENTS_PJ))
    
    with col2:
        st.markdown("#### 🍕 Примеры из меню")
        for pizza_name in list(PIZZAS_PAPA_JOHNS.keys())[:5]:
            st.write(f"• {pizza_name}")
    
    with col3:
        st.markdown("#### 🎯 Цель")
        st.success("Набрать максимум очков за 60 секунд!")
        st.warning("Внимательно читайте состав!")
    
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
        total_ingredients = len(PIZZAS_PAPA_JOHNS[st.session_state.current_pizza])
        st.markdown(f'<div class="stat-box"><h4>🍕 Собрано</h4><p>{len(st.session_state.ingredients_shown)}/{total_ingredients}</p></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Показ текущей пиццы
    correct_ingredients_list = PIZZAS_PAPA_JOHNS[st.session_state.current_pizza]
    st.markdown(f"""
    <div class="pizza-display">
        <h2>🍕 {st.session_state.current_pizza}</h2>
        <p style="font-size: 14px; color: #666; margin-top: 10px;">
            Найдите все {len(correct_ingredients_list)} ингредиентов этой пиццы среди карточек ниже!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🧂 Выберите ингредиенты:")
    
    # Используем зафиксированные ингредиенты для текущей пиццы
    ingredients = st.session_state.current_ingredients
    
    # Создаём динамическую сетку (до 8 элементов, по 4 в ряд)
    num_rows = (len(ingredients) + 3) // 4
    for row in range(num_rows):
        cols = st.columns(4)
        for col_idx in range(4):
            ing_idx = row * 4 + col_idx
            if ing_idx < len(ingredients):
                ingredient = ingredients[ing_idx]
                
                # Определяем стиль кнопки
                if ingredient in st.session_state.ingredients_shown:
                    btn_type = "primary"
                else:
                    btn_type = "secondary"
                
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
    if st.button("🏁 Завершить игру досрочно", use_container_width=True):
        end_game()
    
    # Авто-уменьшение таймера (3 секунды между обновлениями)
    if st.session_state.time_left > 0:
        st.session_state.time_left -= 1
        time.sleep(3)
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
            st.success("🌟 Отличный результат! Вы знаток меню!")
        elif st.session_state.score >= 200:
            st.info("👍 Хорошая работа! Знаете состав хорошо.")
        else:
            st.warning("💪 Тренируйтесь ещё! Загляните в меню.")
    
    if st.button("🔄 Играть снова", use_container_width=True, type="primary"):
        st.session_state.score = 0
        st.rerun()