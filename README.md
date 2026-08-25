# otcheti

Отчёты — система отчётности на Streamlit: календарь, KR, OS, продукты, foodcost,
жалобы (VOC), презентации и другие модули для работы с отчётами ресторанов.

## Запуск

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Структура

- `app.py` — главная страница приложения
- `pages/` — отдельные модули (календарь, жалобы, foodcost и т.д.)
- `components.py`, `styles.py` — общие UI-компоненты и стили
- `utils/` — вспомогательные функции
- `config/` — конфигурация
- `report/` — генерация отчётов
