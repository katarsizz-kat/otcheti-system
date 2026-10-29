# pages/14_Аттестация_Гость.py
# Аттестация «Основы взаимодействия с Гостем»: 46 вопросов разных форматов.
# После каждого ответа — сигнал «верно» или правильный ответ, в конце — сколько верно из скольки.
import streamlit as st
from config.guest_attestation import TITLE, BLOCKS, TYPE_LABELS, QUESTIONS

st.set_page_config(page_title="Аттестация: Гость", page_icon="🍕", layout="wide")

TOTAL = len(QUESTIONS)

# --- Тема страницы: светлый фон, крупный читаемый текст (как на странице «Тест») ---
st.markdown("""
<style>
    html { font-size: 17px; }
    .stApp, section[data-testid="stAppViewContainer"], section.main, header[data-testid="stHeader"] { background-color: #ffffff !important; }
    body, p, li, ul, ol, span, label, h1, h2, h3, h4, h5 { color: #1a1a1a !important; }
    p, li, span, label { font-size: 1.1rem !important; line-height: 1.6 !important; }
    .ga-title { font-size: 2.5rem !important; color: #006837 !important; font-weight: 800; text-align: center; margin-bottom: 0.3rem; }
    .ga-subtitle { text-align: center; color: #444444 !important; font-size: 1.25rem !important; margin-bottom: 1.5rem; }
    .ga-badge { display: inline-block; color: #ffffff !important; padding: 5px 14px; border-radius: 20px; font-size: 0.95rem !important; font-weight: 700; margin-right: 8px; }
    .ga-badge.block { background: #006837; }
    .ga-badge.type { background: #1565c0; }
    .ga-question { background: #f5f5f5; padding: 1.4rem 1.6rem; border-radius: 12px; border-left: 8px solid #006837; margin: 1rem 0 1.2rem; font-size: 1.4rem !important; color: #111111 !important; font-weight: 600; }
    .ga-text { background: #fffde7; padding: 1rem 1.3rem; border-radius: 10px; font-size: 1.2rem !important; margin-bottom: 1rem; }
    .ga-progress { text-align: center; color: #333333 !important; font-size: 1.2rem !important; font-weight: 700; margin-bottom: 0.4rem; }
    .ga-score-line { text-align: center; color: #555555 !important; font-size: 1.05rem !important; margin-bottom: 0.8rem; }
    .ga-item { font-weight: 600; padding-top: 0.45rem; }
    .ga-right { background: #e8f5e9; border: 3px solid #2e7d32; border-radius: 14px; padding: 1.1rem 1.4rem; margin: 1rem 0; font-size: 1.5rem !important; font-weight: 800; color: #1b5e20 !important; animation: ga-pop 0.45s ease-out; }
    .ga-wrong { background: #ffebee; border: 3px solid #c62828; border-radius: 14px; padding: 1.1rem 1.4rem; margin: 1rem 0; animation: ga-shake 0.4s ease-in-out; }
    .ga-wrong .head { font-size: 1.4rem !important; font-weight: 800; color: #b71c1c !important; }
    .ga-wrong .answer { font-size: 1.2rem !important; margin-top: 0.5rem; color: #1a1a1a !important; }
    .ga-source { font-size: 0.95rem !important; color: #666666 !important; margin-top: 0.4rem; }
    .ga-card { background: #f5f5f5; padding: 1.8rem; border-radius: 15px; border: 3px solid #006837; margin-bottom: 1.5rem; }
    .ga-card h3 { color: #006837 !important; }
    .ga-result { background: #f5f5f5; padding: 2.2rem; border-radius: 20px; border: 4px solid #006837; text-align: center; margin: 1rem 0 1.5rem; }
    .ga-result .big { font-size: 4.2rem !important; font-weight: 900; color: #006837 !important; line-height: 1.1; }
    .ga-result .of { font-size: 1.6rem !important; font-weight: 700; color: #1a1a1a !important; }
    .ga-block-row { background: #f5f5f5; padding: 10px 16px; border-radius: 10px; margin: 6px 0; border-left: 5px solid #006837; }
    .ga-block-row.bad { border-left-color: #c62828; }
    div.stButton > button { background-color: #006837 !important; color: #ffffff !important; font-size: 1.2rem !important; font-weight: 700 !important; padding: 0.8rem 2rem !important; border-radius: 12px !important; border: none !important; }
    div.stButton > button p, div.stButton > button span, div.stButton > button div { color: #ffffff !important; font-size: 1.2rem !important; }
    div.stButton > button:hover { background-color: #004d2a !important; }
    div.stButton > button:disabled, div.stButton > button[disabled] { background-color: #bdbdbd !important; color: #f5f5f5 !important; }
    @keyframes ga-pop { 0% { transform: scale(0.85); opacity: 0; } 70% { transform: scale(1.03); opacity: 1; } 100% { transform: scale(1); } }
    @keyframes ga-shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-8px); } 75% { transform: translateX(8px); } }
</style>
""", unsafe_allow_html=True)

# --- Состояние ---
DEFAULT_STATE = {
    "ga_started": False,
    "ga_finished": False,
    "ga_index": 0,
    "ga_checked": False,
    "ga_results": {},   # id вопроса -> True/False
}
for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_attestation():
    for key in list(st.session_state.keys()):
        if key.startswith("ga_"):
            del st.session_state[key]


# --- Рендер вариантов ответа: возвращает (ответ, ответ заполнен полностью) ---
def option_label(q: dict, key: str) -> str:
    if q["type"] == "truefalse":
        return q["options"][key]
    if q["type"] == "error":
        return f"{key}. {q['options'][key]}"
    return f"{key} — {q['options'][key]}"


def render_answer(q: dict, disabled: bool):
    qid = q["id"]
    kind = q["type"]
    keys = list(q["options"].keys()) if "options" in q else []

    if kind in ("single", "truefalse", "error"):
        choice = st.radio(
            "Ответ", keys, format_func=lambda k: option_label(q, k),
            index=None, key=f"ga_q{qid}", disabled=disabled, label_visibility="collapsed",
        )
        return choice, choice is not None

    if kind == "multi":
        st.caption("Отметь все верные варианты")
        chosen = [k for k in keys
                  if st.checkbox(option_label(q, k), key=f"ga_q{qid}_{k}", disabled=disabled)]
        return sorted(chosen), bool(chosen)

    if kind == "order":
        st.caption("Выбери шаг для каждого места — каждый шаг используется один раз")
        order = []
        for i in range(len(keys)):
            order.append(st.selectbox(
                f"Шаг {i + 1}", keys, format_func=lambda k: option_label(q, k),
                index=None, placeholder="Выбери шаг…", key=f"ga_q{qid}_{i}", disabled=disabled,
            ))
        filled = None not in order
        if filled and len(set(order)) < len(order):
            st.warning("Один и тот же шаг выбран несколько раз")
            return order, False
        return order, filled

    if kind == "match":
        extra = len(keys) - len(q["left"])
        st.caption("Справа лишний вариант" if extra == 1 else f"Справа лишних вариантов: {extra}")
        pairs = {}
        for num, text in q["left"].items():
            col_l, col_r = st.columns([2, 3], gap="medium")
            with col_l:
                st.markdown(f'<div class="ga-item">{num}. {text}</div>', unsafe_allow_html=True)
            with col_r:
                pairs[num] = st.selectbox(
                    text, keys, format_func=lambda k: option_label(q, k),
                    index=None, placeholder="Выбери вариант…", key=f"ga_q{qid}_{num}",
                    disabled=disabled, label_visibility="collapsed",
                )
        return pairs, None not in pairs.values()

    if kind == "groups":
        groups = q["groups"]
        placed = {}
        for k in keys:
            placed[k] = st.radio(
                option_label(q, k), list(range(len(groups))), format_func=lambda g: groups[g],
                index=None, horizontal=True, key=f"ga_q{qid}_{k}", disabled=disabled,
            )
        return placed, None not in placed.values()

    if kind == "blanks":
        text = q["text"]
        for i in range(len(q["blanks"])):
            text = text.replace(f"[{i + 1}]", f"<b>____({i + 1})____</b>")
        st.markdown(f'<div class="ga-text">{text}</div>', unsafe_allow_html=True)
        cols = st.columns(len(q["blanks"]), gap="medium")
        filled = []
        for i, (col, variants) in enumerate(zip(cols, q["blanks"])):
            with col:
                filled.append(st.selectbox(
                    f"Пропуск {i + 1}", variants, index=None, placeholder="Выбери…",
                    key=f"ga_q{qid}_{i}", disabled=disabled,
                ))
        return filled, None not in filled

    raise ValueError(f"Неизвестный тип вопроса: {kind}")


def is_correct(q: dict, response) -> bool:
    if q["type"] == "multi":
        return sorted(response) == sorted(q["answer"])
    return response == q["answer"]


def plural_answers(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "ответ"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "ответа"
    return "ответов"


# --- Главный рендер ---
st.markdown('<div class="ga-title">🍕 Аттестация</div>', unsafe_allow_html=True)
st.markdown(f'<div class="ga-subtitle">{TITLE}</div>', unsafe_allow_html=True)

with st.sidebar:
    if st.session_state.ga_started or st.session_state.ga_finished:
        if st.button("↺ Начать аттестацию заново", use_container_width=True):
            reset_attestation()
            st.rerun()

# === ЭКРАН 1: Приветствие ===
if not st.session_state.ga_started and not st.session_state.ga_finished:
    blocks_html = "".join(f"<li>Блок {n} · {name}</li>" for n, name in BLOCKS.items())
    st.markdown(f"""
    <div class="ga-card">
        <h3>📋 Как проходить</h3>
        <ul>
            <li><b>{TOTAL}</b> вопросов по 6 блокам курса</li>
            <li>Форматы: один ответ, несколько ответов, верно / неверно, соответствие,
                последовательность, распредели по группам, вставь пропущенное, найди ошибку</li>
            <li>После каждого ответа нажми «Проверить» — сразу увидишь, верно ли, а при ошибке — правильный ответ</li>
            <li>Варианты похожи и отличаются деталями — цифрами, сроками, названиями чатов и кнопок. Дочитывай до конца</li>
        </ul>
        <h3>📚 Блоки</h3>
        <ul>{blocks_html}</ul>
    </div>
    """, unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if st.button("Начать аттестацию →", use_container_width=True):
            st.session_state.ga_started = True
            st.rerun()

# === ЭКРАН 2: Вопросы ===
elif st.session_state.ga_started and not st.session_state.ga_finished:
    idx = st.session_state.ga_index
    q = QUESTIONS[idx]
    checked = st.session_state.ga_checked
    is_last = idx == TOTAL - 1
    results = st.session_state.ga_results

    st.markdown(f'<div class="ga-progress">Вопрос {idx + 1} из {TOTAL}</div>', unsafe_allow_html=True)
    st.progress(idx / TOTAL)
    if results:
        right = sum(results.values())
        st.markdown(
            f'<div class="ga-score-line">Пока верно: <b>{right}</b> из {len(results)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown(f"""
        <span class="ga-badge block">Блок {q['block']} · {BLOCKS[q['block']]}</span>
        <span class="ga-badge type">{TYPE_LABELS[q['type']]}</span>
    """, unsafe_allow_html=True)
    st.markdown(f'<div class="ga-question">{q["question"]}</div>', unsafe_allow_html=True)

    response, complete = render_answer(q, disabled=checked)

    if checked:
        if results[q["id"]]:
            st.markdown('<div class="ga-right">✅ Верно! Так держать 🎉</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="ga-wrong">
                <div class="head">❌ Неверно</div>
                <div class="answer">💡 <b>Правильный ответ:</b> {q['explain']}</div>
                <div class="ga-source">📖 Где в курсе: {q['source']}</div>
            </div>
            """, unsafe_allow_html=True)

        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            if st.button("Показать результат 🏁" if is_last else "Следующий вопрос →",
                         use_container_width=True, key=f"ga_next_{q['id']}"):
                st.session_state.ga_checked = False
                if is_last:
                    st.session_state.ga_finished = True
                    st.session_state.ga_started = False
                else:
                    st.session_state.ga_index += 1
                st.rerun()
    else:
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            if st.button("✔️ Проверить ответ", use_container_width=True,
                         disabled=not complete, key=f"ga_check_{q['id']}"):
                correct = is_correct(q, response)
                results[q["id"]] = correct
                st.session_state.ga_checked = True
                if correct:
                    st.toast("Верно! ✅")
                st.rerun()
        if not complete:
            st.info("⬆️ Ответь на вопрос — тогда кнопка «Проверить ответ» станет активной")

# === ЭКРАН 3: Итог ===
else:
    results = st.session_state.ga_results
    right = sum(results.values())
    percent = round(right / TOTAL * 100)
    if percent >= 90:
        verdict = "Отлично! Ты отлично знаешь стандарты сервиса 🏆"
        st.balloons()
    elif percent >= 70:
        verdict = "Хороший результат! Повтори темы с ошибками 👍"
    else:
        verdict = "Стоит ещё раз пройти курс и повторить ошибки 📚"

    st.markdown(f"""
    <div class="ga-result">
        <div style="font-size:1.3rem;">Аттестация завершена!</div>
        <div class="big">{right} из {TOTAL}</div>
        <div class="of">{plural_answers(right)} верно · {percent}%</div>
        <div style="margin-top:1rem; font-size:1.3rem;">{verdict}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📊 По блокам")
    for num, name in BLOCKS.items():
        block_q = [q for q in QUESTIONS if q["block"] == num]
        block_right = sum(results.get(q["id"], False) for q in block_q)
        bad = " bad" if block_right < len(block_q) else ""
        st.markdown(
            f'<div class="ga-block-row{bad}">Блок {num} · {name} — <b>{block_right} из {len(block_q)}</b></div>',
            unsafe_allow_html=True,
        )

    wrong = [q for q in QUESTIONS if not results.get(q["id"], False)]
    if wrong:
        st.markdown(f"### ❌ Ошибки ({len(wrong)})")
        for q in wrong:
            with st.expander(f"Вопрос {q['id']}. {q['question']}"):
                st.markdown(f"💡 **Правильный ответ:** {q['explain']}")
                st.caption(f"📖 Где в курсе: {q['source']}")
    else:
        st.success("🎉 Ни одной ошибки — идеальный результат!")

    st.markdown("---")
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if st.button("🔄 Пройти аттестацию заново", use_container_width=True):
            reset_attestation()
            st.rerun()
