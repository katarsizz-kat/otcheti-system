import streamlit as st
from styles import apply_subtle_theme
from ui.pages.prodykt import render_prodykt_page
from report.prodykt import generate_product_report

# Применяем единую тему вместо хардкода CSS
apply_subtle_theme()

st.markdown("<h1 class='page-header'>🍕 Отчет Продукт</h1>", unsafe_allow_html=True)

# Состояние файлов хранится в session_state для передачи между модулями
if 'product_files' not in st.session_state:
    st.session_state.product_files = {'main': None, 'combo': None}

render_prodykt_page(st.session_state.product_files, generate_product_report)