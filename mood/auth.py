"""
Вход по паролю для mood-страницы

Пароль хранится в .streamlit/secrets.toml:
[mood]
password = "ваш_пароль"
"""

import streamlit as st
import random
from mood.config import GREETINGS, THEME


def _get_password() -> str:
    """Получить пароль из secrets. Если не задан — вернуть пустую строку."""
    try:
        return st.secrets.get("mood", {}).get("password", "")
    except Exception:
        return ""


def _is_authenticated() -> bool:
    """Проверить, аутентифицирован ли пользователь в текущей сессии."""
    return st.session_state.get("mood_authenticated", False)


def _authenticate(password_input: str) -> bool:
    """Проверить введённый пароль."""
    correct_password = _get_password()
    
    # Если пароль не задан в secrets — разрешаем доступ (режим разработки)
    if not correct_password:
        return True
    
    return password_input == correct_password


def render_auth_gate() -> bool:
    """
    Рендерит форму входа или приветствие.
    
    Returns:
        True если доступ разрешён, False если нужно показать форму входа
    """
    # Если уже аутентифицированы — показываем приветствие и возвращаем True
    if _is_authenticated():
        greeting = random.choice(GREETINGS)
        st.markdown(
            f"""
            <div class="mood-fade-in" style="text-align: center; margin-bottom: 2rem;">
                <div style="
                    font-family: 'Quicksand', sans-serif;
                    font-size: 1.3rem;
                    font-weight: 600;
                    color: {THEME['text_primary']};
                    background: {THEME['bg_card']};
                    backdrop-filter: blur(12px);
                    border: 1px solid {THEME['border']};
                    border-radius: 16px;
                    padding: 1rem 2rem;
                    display: inline-block;
                    box-shadow: {THEME['shadow']};
                ">
                    {greeting}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return True
    
    # Проверяем, задан ли пароль вообще
    correct_password = _get_password()
    if not correct_password:
        # Пароль не задан — разрешаем доступ, но показываем предупреждение
        st.warning(
            "⚠️ Пароль не задан в `.streamlit/secrets.toml`. "
            "Доступ разрешён без пароля (режим разработки).",
            icon="⚠️"
        )
        st.session_state["mood_authenticated"] = True
        return True
    
    # Показываем форму входа
    st.markdown(
        """
        <div class="mood-auth-container mood-fade-in">
            <div class="mood-auth-card">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🌿</div>
                <div class="mood-auth-title">Дневник эмоциональной погоды</div>
                <div style="
                    font-family: 'Nunito', sans-serif;
                    color: #8a7a6a;
                    font-size: 0.9rem;
                    margin-bottom: 1.5rem;
                ">
                    Это личное пространство. Введите пароль, чтобы войти.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Форма ввода пароля
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password_input = st.text_input(
            "Пароль",
            type="password",
            key="mood_password_input",
            label_visibility="collapsed",
            placeholder="Введите пароль..."
        )
        
        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
        
        if st.button("🔑 Войти", use_container_width=True, key="mood_login_btn"):
            if _authenticate(password_input):
                st.session_state["mood_authenticated"] = True
                st.rerun()
            else:
                st.error("Неверный пароль. Попробуйте ещё раз 🌸")
    
    return False


def logout():
    """Выйти из mood-страницы (сбросить аутентификацию)."""
    st.session_state["mood_authenticated"] = False
    st.rerun()