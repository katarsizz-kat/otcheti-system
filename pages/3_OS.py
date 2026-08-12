"""Страница отчёта ОС (Отдел Обратной Связи). Входная точка."""
import streamlit as st

# ВАЖНО: st.set_page_config должен быть ПЕРВЫМ вызовом!
st.set_page_config(page_title="😊😠 ОС", page_icon="📈", layout="wide")

import ui.pages.os_report as ui


def main():
    ui.render()


if __name__ == "__main__":
    main()