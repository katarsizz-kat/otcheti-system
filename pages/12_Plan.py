"""Страница «План заказов». Входная точка."""
import streamlit as st

# ВАЖНО: st.set_page_config должен быть ПЕРВЫМ вызовом!
st.set_page_config(page_title="📈 План заказов", page_icon="📈", layout="wide")

import ui.pages.orders_plan as ui


def main():
    ui.render()


if __name__ == "__main__":
    main()
