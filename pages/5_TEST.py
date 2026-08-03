# pages/5_🎯_Тест.py
import streamlit as st
import random
from datetime import datetime, timezone, timedelta
from config.quiz_data import QUESTIONS, MAX_SCORE, get_rank

# --- Константы ---
MOSCOW_TZ = timezone(timedelta(hours=3))
BRAND_GREEN = "#006837"
BRAND_GREEN_DARK = "#004d2a"
BRAND_RED = "#c62828"

st.set_page_config(page_title="Тест", page_icon="🎯", layout="wide")

# --- ЛОКАЛЬНАЯ ТЕМА СТРАНИЦЫ ТЕСТА: светлый фон, тёмный читаемый текст (база 17px) ---
st.markdown("""
<style>
    html { font-size: 17px; }
    .stApp, section[data-testid="stAppViewContainer"], section.main, header[data-testid="stHeader"] { background-color: #ffffff !important; }
    body, p, li, ul, ol, span, label, h1, h2, h3, h4, h5 { color: #1a1a1a !important; }
    p, li, span, label { font-size: 1.15rem !important; line-height: 1.65 !important; }
    .quiz-title { font-size: 2.7rem !important; color: #006837 !important; font-weight: 800; text-align: center; margin-bottom: 0.5rem; }
    .quiz-subtitle { text-align: center; color: #444444 !important; font-size: 1.3rem !important; margin-bottom: 2rem; }
    .question-box { background: #f5f5f5; padding: 1.6rem; border-radius: 12px; border-left: 8px solid #006837; margin: 1.5rem 0; font-size: 1.5rem !important; color: #111111 !important; font-weight: 600; animation: fadeIn 0.4s ease-out; }
    .category-badge { display: inline-block; background: #006837; color: #ffffff !important; padding: 6px 16px; border-radius: 20px; font-size: 1.05rem !important; font-weight: 700; }
    .points-badge { display: inline-block; background: #c62828; color: #ffffff !important; padding: 6px 16px; border-radius: 20px; font-size: 1.05rem !important; font-weight: 700; margin-left: 10px; }
    .mode-badge { display: inline-block; background: #1565c0; color: #ffffff !important; padding: 6px 16px; border-radius: 20px; font-size: 1.05rem !important; font-weight: 700; margin-left: 10px; }
    .progress-text { text-align: center; color: #333333 !important; font-size: 1.25rem !important; font-weight: 700; margin-bottom: 0.5rem; }
    .streak { text-align: center; background: #fff3e0; padding: 10px; border-radius: 10px; margin-bottom: 1rem; color: #e65100 !important; font-weight: 700; font-size: 1.25rem !important; }
    div[role="radiogroup"] label { cursor: pointer; margin-bottom: 0.5rem; }
    div[role="radiogroup"] label p, div[role="radiogroup"] label span, div[role="radiogroup"] div span { font-size: 1.3rem !important; color: #111111 !important; font-weight: 500 !important; }
    div.stButton > button { background-color: #006837 !important; color: #ffffff !important; font-size: 1.3rem !important; font-weight: 700 !important; padding: 0.9rem 2rem !important; border-radius: 12px !important; border: none !important; }
    div.stButton > button p, div.stButton > button span, div.stButton > button div { color: #ffffff !important; font-size: 1.3rem !important; }
    div.stButton > button:hover { background-color: #004d2a !important; }
    div.stButton > button:disabled, div.stButton > button[disabled] { background-color: #bdbdbd !important; color: #f5f5f5 !important; }
    div[data-testid="stAlert"] { font-size: 1.15rem !important; }
    .start-card { background: #f5f5f5; padding: 2rem; border-radius: 15px; border: 3px solid #006837; margin-bottom: 1.5rem; }
    .start-card h3 { color: #006837 !important; font-size: 1.6rem !important; }
    .start-card h4 { color: #c62828 !important; font-size: 1.4rem !important; }
    .start-card li { font-size: 1.2rem !important; }
    .mode-card { background: #f5f5f5; padding: 1.5rem; border-radius: 15px; border: 3px solid #1565c0; margin-bottom: 1rem; }
    .mode-card.green { border-color: #006837; }
    .mode-card h4 { font-size: 1.4rem !important; }
    .mode-card li { font-size: 1.1rem !important; }
    .result-card { background: #f5f5f5; padding: 2.5rem; border-radius: 20px; border: 4px solid #006837; text-align: center; margin-top: 2rem; }
    .score-big { font-size: 4.5rem !important; font-weight: 900; color: #006837 !important; margin: 1rem 0; }
    .rank-title { font-size: 2.1rem !important; font-weight: 800; margin: 1rem 0; padding: 1rem; border-radius: 12px; color: #ffffff !important; }
    .wrong-topic { background: #ffebee; padding: 12px 16px; border-radius: 10px; margin: 8px 0; border-left: 5px solid #c62828; font-size: 1.15rem !important; }
    .right-topic { background: #e8f5e9; padding: 12px 16px; border-radius: 10px; margin: 8px 0; border-left: 5px solid #006837; font-size: 1.15rem !important; }
    @media (max-width: 768px) { div[data-testid="stHorizontalBlock"] { flex-direction: column !important; } }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
""", unsafe_allow_html=True)

# --- Инициализация session state ---
DEFAULT_STATE = {
    "quiz_started": False,
    "quiz_finished": False,
    "quiz_mode": None,            # "training" или "exam"
    "current_index": 0,
    "score": 0,
    "streak": 0,
    "max_streak": 0,
    "wrong_topics": [],
    "right_topics": [],
    "shuffled_questions": [],
    "shuffled_options": {},
    "selected_answers": {},
    "answer_checked": False,
    "last_correct": False,
}
for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def plural_points(n: int) -> str:
    if n == 1:
        return "1 балл"
    if n in (2, 3, 4):
        return f"{n} балла"
    return f"{n} баллов"


def init_quiz(mode: str):
    """Инициализирует новую попытку теста со случайным порядком"""
    q_list = list(QUESTIONS)
    random.shuffle(q_list)
    st.session_state.shuffled_questions = q_list
    st.session_state.shuffled_options = {}
    for q in q_list:
        keys = list(q["options"].keys())
        random.shuffle(keys)
        st.session_state.shuffled_options[q["id"]] = keys
    st.session_state.quiz_mode = mode
    st.session_state.quiz_started = True
    st.session_state.quiz_finished = False
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.streak = 0
    st.session_state.max_streak = 0
    st.session_state.wrong_topics = []
    st.session_state.right_topics = []
    st.session_state.selected_answers = {}
    st.session_state.answer_checked = False
    st.session_state.last_correct = False


def submit_answer(q: dict, selected_key: str) -> bool:
    """Фиксирует ответ и обновляет статистику (защита от двойного начисления)"""
    if q["id"] in st.session_state.selected_answers:
        return st.session_state.selected_answers[q["id"]] == q["correct_id"]
    st.session_state.selected_answers[q["id"]] = selected_key
    correct = selected_key == q["correct_id"]
    if correct:
        st.session_state.score += q["points"]
        st.session_state.streak += 1
        st.session_state.max_streak = max(st.session_state.max_streak, st.session_state.streak)
        st.session_state.right_topics.append(q["category"])
    else:
        st.session_state.streak = 0
        st.session_state.wrong_topics.append(f"{q['category']} — вопрос №{q['id']}")
    return correct


def finish_quiz():
    st.session_state.quiz_finished = True
    st.session_state.quiz_started = False


# --- Главный рендер ---
st.markdown('<div class="quiz-title">🎯 Аттестация </div>', unsafe_allow_html=True)
st.markdown('<div class="quiz-subtitle">Проверь свои знания и получи звание!</div>', unsafe_allow_html=True)

# === ЭКРАН 1: Приветствие и ВЫБОР РЕЖИМА (полная ширина, без вложенных узких колонок) ===
if not st.session_state.quiz_started and not st.session_state.quiz_finished:
    st.markdown(f"""
    <div class="start-card">
        <h3>📋 Что вас ждёт:</h3>
        <ul>
            <li><b>{len(QUESTIONS)}</b> вопросов из разных тем (задаются все)</li>
            <li>Максимальный балл: <b>{MAX_SCORE}</b></li>
            <li>Случайный порядок вопросов и ответов — списать невозможно</li>
            <li>Игровая механика: серии правильных ответов и звания</li>
        </ul>
        <h4>🏆 Звания:</h4>
        <ul>
            <li>56–{MAX_SCORE} баллов — <b>Мастер 👑</b></li>
            <li>46–55 баллов — <b>Эксперт смены ⭐</b></li>
            <li>31–45 баллов — <b>Сотрудник зала 🍕</b></li>
            <li>0–30 баллов — <b>Стажёр 🌱</b></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Выберите режим:")

    # Карточки режимов — каждая на половину ПОЛНОЙ ширины
    col_t, col_e = st.columns(2, gap="large")
    with col_t:
        st.markdown("""
        <div class="mode-card green">
            <h4>🎓 Тренировка</h4>
            <ul>
                <li>Кнопки «Проверить ответ» и «Следующий вопрос» рядом</li>
                <li>После проверки виден правильный вариант</li>
                <li>В конце — результат и темы для повторения</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col_e:
        st.markdown("""
        <div class="mode-card">
            <h4>📝 Экзамен</h4>
            <ul>
                <li>Без подсказок во время прохождения</li>
                <li>Результат и звание — только в конце</li>
                <li>Правильные ответы НЕ раскрываются — только темы</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # Кнопки — отдельным рядом, всегда на одной линии
    col_bt, col_be = st.columns(2, gap="large")
    with col_bt:
        if st.button("🎓 Начать тренировку", use_container_width=True):
            init_quiz("training")
            st.rerun()
    with col_be:
        if st.button("📝 Начать экзамен", use_container_width=True):
            init_quiz("exam")
            st.rerun()

# === ЭКРАН 2: Вопросы ===
elif st.session_state.quiz_started and not st.session_state.quiz_finished:
    total = len(st.session_state.shuffled_questions)
    idx = st.session_state.current_index
    q = st.session_state.shuffled_questions[idx]
    is_training = st.session_state.quiz_mode == "training"
    is_last = idx == total - 1

    progress = idx / total
    st.markdown(f'<div class="progress-text">Вопрос {idx + 1} из {total}</div>', unsafe_allow_html=True)
    st.progress(progress)

    if st.session_state.streak >= 2:
        st.markdown(f'<div class="streak">🔥 Серия правильных ответов: {st.session_state.streak}!</div>', unsafe_allow_html=True)

    mode_label = "🎓 Тренировка" if is_training else "📝 Экзамен"
    st.markdown(f"""
        <span class="category-badge">{q['category']}</span>
        <span class="points-badge">{plural_points(q['points'])}</span>
        <span class="mode-badge">{mode_label}</span>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="question-box">{q["question"]}</div>', unsafe_allow_html=True)

    radio_key = f"q_{q['id']}_{hash(tuple(st.session_state.shuffled_options[q['id']]))}"
    shuffled_keys = st.session_state.shuffled_options[q["id"]]

    selected = st.radio(
        "Выберите ответ:",
        options=shuffled_keys,
        format_func=lambda k: q["options"][k],
        key=radio_key,
        index=None,
        label_visibility="collapsed",
        disabled=st.session_state.answer_checked
    )

    if is_training:
        # --- ТРЕНИРОВКА: проверка по желанию, кнопки рядом ---
        if st.session_state.answer_checked:
            if st.session_state.last_correct:
                st.success(f"✅ Верно! +{plural_points(q['points'])}")
            else:
                st.error("❌ Неверно.")
                st.info(f"💡 Правильный ответ: {q['options'][q['correct_id']]}")

        col_check, col_next = st.columns(2, gap="small")
        with col_check:
            check_clicked = st.button(
                "✔️ Проверить ответ",
                use_container_width=True,
                disabled=(selected is None) or st.session_state.answer_checked,
                key=f"check_{q['id']}"
            )
        with col_next:
            next_clicked = st.button(
                "Завершить тест 🏁" if is_last else "Следующий вопрос →",
                use_container_width=True,
                disabled=selected is None,
                key=f"next_{q['id']}"
            )

        if selected is None:
            st.info("⬆️ Выберите один из вариантов ответа выше — тогда кнопки станут активными")

        if check_clicked:
            st.session_state.last_correct = submit_answer(q, selected)
            st.session_state.answer_checked = True
            st.rerun()
        if next_clicked:
            submit_answer(q, selected)   # если уже проверено — защитит от двойного начисления
            st.session_state.answer_checked = False
            if is_last:
                finish_quiz()
            else:
                st.session_state.current_index += 1
            st.rerun()
    else:
        # --- ЭКЗАМЕН: без проверки, сразу следующий вопрос ---
        if selected:
            btn_text = "Завершить тест 🏁" if is_last else "Следующий вопрос →"
            if st.button(btn_text, use_container_width=True):
                submit_answer(q, selected)
                if is_last:
                    finish_quiz()
                else:
                    st.session_state.current_index += 1
                st.rerun()
        else:
            st.info("⬆️ Выберите один из вариантов ответа выше")

# === ЭКРАН 3: Результат (одинаковый для обоих режимов, без раскрытия правильных ответов) ===
elif st.session_state.quiz_finished:
    score = st.session_state.score
    percentage = round(score / MAX_SCORE * 100, 1)
    rank_title, rank_color = get_rank(score)
    finished_at = datetime.now(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M (МСК)")
    mode_label = "🎓 Тренировка" if st.session_state.quiz_mode == "training" else "📝 Экзамен"

    st.markdown(f"""
    <div class="result-card">
        <div style="font-size:1.3rem; color:#444444;">Тест завершён! Режим: {mode_label}</div>
        <div style="font-size:1.1rem; color:#666666; margin-top:5px;">{finished_at}</div>
        <div class="score-big">{score} / {MAX_SCORE}</div>
        <div style="font-size:1.6rem; color:#1a1a1a; font-weight:700;">{percentage}% правильных ответов</div>
        <div class="rank-title" style="background:{rank_color};">{rank_title}</div>
        <div style="margin-top:1rem; font-size:1.3rem;">🔥 Максимальная серия: <b>{st.session_state.max_streak}</b></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ✅ Темы без ошибок")
        if st.session_state.right_topics:
            for topic in sorted(set(st.session_state.right_topics)):
                count = st.session_state.right_topics.count(topic)
                st.markdown(f'<div class="right-topic"><b>{topic}</b> — {count} правильных</div>', unsafe_allow_html=True)
        else:
            st.info("Пока нет правильных ответов")
    with col2:
        st.markdown("### ❌ Темы для повторения")
        if st.session_state.wrong_topics:
            for topic in sorted(set(st.session_state.wrong_topics)):
                st.markdown(f'<div class="wrong-topic">{topic}</div>', unsafe_allow_html=True)
        else:
            st.success("🎉 Ошибок нет! Идеальный результат!")

    st.markdown("---")
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if st.button("🔄 Пройти тест заново (с новым порядком вопросов)", use_container_width=True):
            for key in list(DEFAULT_STATE.keys()):
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    st.info("💡 Результат сохранён и не исчезнет, пока вы не нажмёте кнопку 'Пройти тест заново'. Можете спокойно переключаться между страницами приложения.")