# tests/test_complaints_control.py

"""
Тесты проверки внесения жалоб (действующие правила, ред. 18.11.2026).

Запуск: python tests/test_complaints_control.py

Данные синтетические: реальные выгрузки и отчёты в репозиторий не попадают.
"""

from __future__ import annotations

import io
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from openpyxl import Workbook, load_workbook

from report.complaints_control import constants as c
from report.complaints_control.builder import build_complaints_control_report
from report.complaints_control.classify import classify_message
from report.complaints_control.data import group_messages, load_chat_messages
from report.complaints_control.matching import (
    build_main_index,
    match_complaint,
    format_guest_phone,
)
from report.complaints_control.models import (
    ControlReportRequest,
    ControlSettings,
    ControlSourceFiles,
)
from report.complaints_control.phone import find_orders_in_text, parse_key_cell


# ==========================================================
# КЛАССИФИКАЦИЯ
# ==========================================================
def test_classify_delay_promo_rule() -> None:
    # Уточнение 17.11.2026: промокод за опоздание/ожидание — уже жалоба.
    r = classify_message("tyumen-2-58550619-iP +79957722525 прошу отправить промокод за опоздание")
    assert r.is_complaint and r.reason_label == "delay_promo" and r.category == c.CAT_DELAY

    r = classify_message("прошу выслать промокод за долгое ожидание гостю")
    assert r.is_complaint and r.category == c.CAT_DELAY

    # Обычные бонусы за задержку — не запрос промокода, но задержка — жалоба.
    r = classify_message("прошу начислить бонусы за задержку гостю")
    assert r.is_complaint and r.reason_label != "delay_promo" and r.category == c.CAT_DELAY

    # День рождения и лояльность — не жалобы.
    r = classify_message("+79138444342 прошу выслать промокод ко дню рождения")
    assert not r.is_complaint and r.reason_label == "birthday"
    r = classify_message("прошу выслать промокод на скидку")
    assert not r.is_complaint

    # Задержка без промокода — жалоба «Опоздания».
    r = classify_message("заказ опоздал на час, где заказ")
    assert r.is_complaint and r.category == c.CAT_DELAY


def test_classify_user_corrections_19_11() -> None:
    # Уточнение 19.11.2026: дать что-то «в качестве лояльности» — жалоба.
    r = classify_message("отправьте промокод в качестве лояльности +79006666666")
    assert r.is_complaint and r.reason_label == "compensation"
    r = classify_message("прошу начислить бонусы в качестве лояльности гостю")
    assert r.is_complaint
    r = classify_message("дайте что-то в качестве лояльности, гость расстроен")
    assert r.is_complaint
    # Вопросы гостей про бонусную программу — по-прежнему не жалобы.
    r = classify_message("как списать бонусы при заказе")
    assert not r.is_complaint and r.reason_label == "loyalty"
    r = classify_message("не пришёл промокод на день рождения")
    assert not r.is_complaint

    # Уточнение 19.11.2026: недовоз заказа целиком — не жалоба.
    for text in (
        "+79007777777 заказ не доставлен",
        "не привезли заказ, гость ждёт",
        "курьер не довез заказ",
    ):
        r = classify_message(text)
        assert not r.is_complaint and r.reason_label == "not_delivered", text
    # «Не доставлен вовремя» — опоздание, а не недовоз.
    r = classify_message("заказ не доставлен вовремя, опоздание на час")
    assert r.is_complaint and r.category == c.CAT_DELAY
    # Жалоба на позицию остаётся жалобой даже рядом с недовозом.
    r = classify_message("заказ не доставлен, а в привезённой пицце забыли соус")
    assert r.is_complaint and r.category == c.CAT_MISSING


def test_classify_categories_and_attention() -> None:
    assert classify_message("забыли томатный соус").category == c.CAT_MISSING
    assert classify_message("привезли вместо цыпленка рэнч пепперони").category == c.CAT_MISSING
    assert classify_message("пицца сырая, тесто не пропеклось").category == c.CAT_COOKING
    assert classify_message("курьер нахамил гостю").category == c.CAT_SERVICE
    assert classify_message("пицца холодная, остыла").category == c.CAT_PRODUCT

    # Технические сбои — «Требует внимания», не невнесённые жалобы.
    for text in (
        "заказ не попал в систему, свяжитесь с гостем",
        "статус доставлен раньше времени",
        "не дозвониться, телефон недоступен",
    ):
        r = classify_message(text)
        assert not r.is_complaint and r.reason_label == "attention", text

    # Изменения текущего заказа — не жалобы.
    r = classify_message("поменяйте адрес доставки, домофон 64")
    assert not r.is_complaint and r.reason_label == "logistics"

    # Самостоятельная жалоба остаётся жалобой даже рядом с лояльностью.
    r = classify_message("гость спрашивал про бонусы, а ещё привезли холодную пиццу")
    assert r.is_complaint and r.category == c.CAT_PRODUCT


# ==========================================================
# КЛЮЧИ: ТЕЛЕФОНЫ И ЗАКАЗЫ
# ==========================================================
def test_parse_key_cell() -> None:
    assert parse_key_cell("15-43250550-APD") == {"phone": "", "order_id": "43250550", "rest": 15}
    assert parse_key_cell(79991234567.0)["phone"] == "79991234567"
    assert parse_key_cell("9667872986")["phone"] == "79667872986"
    assert parse_key_cell(" 8 8-43322343")["order_id"] == "43322343"
    assert parse_key_cell("-4-43405884-iP")["order_id"] == "43405884"
    assert parse_key_cell("из отзывов гео") == {"phone": "", "order_id": "", "rest": None}


def test_find_orders_in_text() -> None:
    orders = find_orders_in_text(
        "tyumen-3-58419236-APD и sankt-peterburg-20-58383418-APD"
    )
    by_id = {o["order_id"]: o for o in orders}
    assert by_id["58419236"]["city"] == "Тюмень" and by_id["58419236"]["rest"] == 3
    assert by_id["58383418"]["city"] == "Санкт-Петербург" and by_id["58383418"]["rest"] == 20


# ==========================================================
# ГРУППИРОВКА
# ==========================================================
def _messages(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Дата", "Автор", "Текст", "Источник"])


def test_group_messages_order_phone_series() -> None:
    # Заказ, телефон и суть — три реплики подряд; повтор заказа на след. день.
    msgs = _messages([
        (pd.Timestamp("2026-10-05 12:00:00"), "Евгений", "tyumen-2-58550619-iP", "Гости ОС Тюмень"),
        (pd.Timestamp("2026-10-05 12:01:00"), "Евгений", "+79957722525 не положили томатный соус", "Гости ОС Тюмень"),
        (pd.Timestamp("2026-10-06 09:00:00"), "Евгений", "tyumen-2-58550619-iP гость всё ещё ждёт соус", "Гости ОС Тюмень"),
        (pd.Timestamp("2026-10-06 10:00:00"), "Руслана", "просто текст без ключей", "Гости ОС Тюмень"),
    ])
    grouped, no_keys = group_messages(msgs)
    assert len(grouped) == 1, grouped
    g = grouped.iloc[0]
    assert g["Телефон"] == "79957722525"
    assert g["Заказ"] == "58550619"
    assert g["Кол-во сообщений"] == 3
    assert g["Дата"] == date(2026, 10, 5)
    assert len(no_keys) == 1


def test_group_messages_different_questions_not_merged() -> None:
    # Разные телефоны в один день — разные жалобы, не объединять.
    msgs = _messages([
        (pd.Timestamp("2026-10-05 12:00:00"), "А", "+79991111111 забыли соус", "Гости ОС Тюмень"),
        (pd.Timestamp("2026-10-05 18:00:00"), "Б", "+79992222222 холодная пицца", "Гости ОС Тюмень"),
    ])
    grouped, _ = group_messages(msgs)
    assert len(grouped) == 2


def test_meta_messages_filtered() -> None:
    # Уведомления Битрикс о создании задачи цитируют жалобу — не задваивать.
    df = pd.DataFrame([
        ("2026-10-05 12:00:00", "Евгений", "+79991111111 забыли соус"),
        ("2026-10-05 12:01:00", "id0", "------ Евгений [сегодня в 12:00] +79991111111 забыли соус "
                                      "[USER=1 REPLACE]Евгений[/USER] создал задачу на основании сообщения"),
        ("2026-10-05 12:02:00", "Система", "служебное"),
    ], columns=["Дата", "Автор", "Текст сообщения"])
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    buf.seek(0)
    messages = load_chat_messages(buf, "Гости ОС Тюмень")
    assert len(messages) == 1
    assert messages.iloc[0]["Автор"] == "Евгений"


# ==========================================================
# СОПОСТАВЛЕНИЕ
# ==========================================================
def _main_row(phone="", order="", rest=None, d=None, cat=""):
    return {
        "Дата": d, "Телефон": phone, "Заказ": order, "Город": "Санкт-Петербург",
        "Ресторан": f"№{rest}" if rest else "", "Номер ресторана": rest,
        "Вид жалобы": cat, "Категория": cat, "Сотрудник": "Тест",
    }


def test_match_levels() -> None:
    d = date(2026, 10, 5)
    main = pd.DataFrame([
        _main_row(order="58383418", rest=15, d=date(2023, 7, 1), cat=c.CAT_PRODUCT),
        _main_row(phone="79991234567", rest=15, d=d, cat=c.CAT_DELAY),
        _main_row(phone="79001234567", rest=4, d=None, cat=c.CAT_PRODUCT),
    ])
    index = build_main_index(main)

    # Заказ — точное совпадение даже со старой датой (заказ уникален).
    status, rec, _ = match_complaint("", "58383418", 15, d, c.CAT_PRODUCT, index)
    assert status == c.STATUS_EXACT and rec["__row_num"] == 1

    # Телефон + ресторан + дата + категория — точное совпадение.
    status, rec, _ = match_complaint("79991234567", "", 15, d, c.CAT_DELAY, index)
    assert status == c.STATUS_EXACT and rec["__row_num"] == 2

    # Телефон + дата в пределах допуска, категория другая — вероятное.
    status, _, _ = match_complaint(
        "79991234567", "", 15, date(2026, 10, 8), c.CAT_PRODUCT, index, tolerance_days=3,
    )
    assert status == c.STATUS_PROBABLE

    # Строка таблицы без даты: телефон+ресторан+категория — вероятное (сверка).
    status, _, _ = match_complaint("79001234567", "", 4, d, c.CAT_PRODUCT, index)
    assert status == c.STATUS_PROBABLE

    # Совпадений нет, ключи полные — невнесено.
    status, _, _ = match_complaint("79009999999", "", None, d, c.CAT_MISSING, index)
    assert status == c.STATUS_NOT_ENTERED

    # Ключей нет — не доказанное невнесение.
    status, _, _ = match_complaint("", "", None, d, c.CAT_MISSING, index)
    assert status == c.STATUS_NO_KEYS

    assert format_guest_phone("") == c.NO_PHONE_LABEL
    assert format_guest_phone("79991234567") == "+79991234567"


# ==========================================================
# ИМЕНА ФАЙЛОВ
# ==========================================================
def test_file_names() -> None:
    weekly = ControlSettings(use_period=True, date_start=date(2026, 10, 26), date_end=date(2026, 11, 1))
    assert weekly.period_kind == "недельная"
    assert weekly.file_name == "Проверка_внесения_жалоб_2026-10-26—2026-11-01_недельная.xlsx"

    monthly = ControlSettings(use_period=True, date_start=date(2026, 10, 1), date_end=date(2026, 10, 31))
    assert monthly.period_kind == "месячная"
    assert monthly.file_name == "Проверка_внесения_жалоб_2026-10-01—2026-10-31_месячная.xlsx"

    custom = ControlSettings(use_period=True, date_start=date(2026, 10, 5), date_end=date(2026, 10, 9))
    assert custom.period_kind == ""
    assert custom.file_name == "Проверка_внесения_жалоб_2026-10-05—2026-10-09.xlsx"


# ==========================================================
# СКВОЗНОЙ ПРОГОН (синтетические файлы)
# ==========================================================
def _main_xlsx() -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Обращения"
    ws.append([
        "Дата", "Номер телефона", "источник", "Ресторан", "Жалоба",
        "Вид позиции", "Комментарий", "Решение", "Стоимость компенсации",
        "Статус возмещения", "Имя в системе 1С ответственного",
    ])
    ws.append([date(2026, 10, 5), "15-58383418-APD", "чат", 15, "Жалоба на продукт",
               "", "холодная пицца", "Купон", 300, True, "Иванов"])
    ws.append([date(2026, 10, 5), 79991234567, "чат", 15, "Опоздание",
               "", "опоздал на час", "Баллы", 100, True, "Петров"])
    ws.append([date(2023, 7, 1), 79001234567, "чат", 4, "Жалоба на продукт",
               "", "старая запись", "", None, False, "Сидоров"])
    summary = wb.create_sheet("Сводная")
    summary.append(["15 Ветеранов", "04 Соверен"])
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out


def _chat_csv() -> io.BytesIO:
    rows = [
        ("2026-10-05 12:00:00", "Иванова", "sankt-peterburg-15-58383418-APD +79210000000 привезли холодную пиццу"),
        ("2026-10-05 13:00:00", "Петров", "+79991234567 заказ опоздал на час, где заказ"),
        ("2026-10-06 12:00:00", "Сидоров", "+79009999999 забыли соус"),
        ("2026-10-06 12:05:00", "Сидоров", "прошу отправить промокод за опоздание +79008888888"),
        ("2026-10-06 14:00:00", "Иванов", "заказ не попал в систему"),
        ("2026-10-07 10:00:00", "Петров", "+79001234567 холодная пицца невкусно"),
        ("2026-10-08 11:00:00", "Кузнецов", "+79991234567 пицца невкусно, есть не стали"),
        ("2026-10-09 12:00:00", "Иванов", "+79007777777 заказ не доставлен"),
        ("2026-10-09 13:00:00", "Петров", "отправьте промокод в качестве лояльности +79006666666"),
    ]
    df = pd.DataFrame(rows, columns=["Дата", "Автор", "Текст сообщения"])
    out = io.BytesIO()
    df.to_csv(out, index=False, encoding="utf-8-sig")
    out.seek(0)
    return out


def _request(overrides=None) -> ControlReportRequest:
    return ControlReportRequest(
        files=ControlSourceFiles(main_spb=_main_xlsx(), chat_spb=_chat_csv()),
        settings=ControlSettings(
            use_period=True, date_start=date(2026, 10, 1), date_end=date(2026, 10, 31),
            tolerance_days=3,
        ),
        overrides=overrides or {},
    )


def test_builder_end_to_end() -> None:
    result = build_complaints_control_report(_request())
    assert result.success, result.error
    data = result.data

    # 2 точных (заказ; телефон+ресторан+дата+категория), 4 невнесённых
    # (включая компенсацию «в качестве лояльности»), 1 вероятное,
    # 2 «требует внимания» (техсбой + недовоз целиком).
    assert len(data.not_entered) == 4, data.comparison[["Суть обращения", "Статус"]]
    assert len(data.probable) == 1
    assert len(data.attention) == 2
    assert (data.comparison["Статус"] == c.STATUS_EXACT).sum() == 2

    # Столбец «Телефон Гостя» — явный номер или явная пометка.
    assert "Телефон Гостя" in data.not_entered.columns
    assert "+79009999999" in set(data.not_entered["Телефон Гостя"])

    # Вероятные совпадения — в очереди разметки, не в счётчике.
    assert len(data.review_queue) >= 1
    assert c.RESULT_PROBABLE in set(data.probable["Результат сверки"])

    # Имя и листы книги.
    assert result.file_name.endswith("_месячная.xlsx")
    wb = load_workbook(result.excel)
    assert "Не внесённые жалобы" in wb.sheetnames
    assert "Сверка" in wb.sheetnames
    assert "Требует внимания" in wb.sheetnames

    # Ручная разметка: подтверждаем внесение одной жалобы — счётчик падает.
    key = data.not_entered.index[0]
    complaint_key = data.comparison.loc[
        data.comparison["Суть обращения"].str.contains("забыли соус"), "Ключ",
    ].iloc[0]
    rebuilt = build_complaints_control_report(_request({complaint_key: "exact"}))
    assert rebuilt.success, rebuilt.error
    assert len(rebuilt.data.not_entered) == 3
    assert key is not None


def main() -> None:
    tests = [
        test_classify_delay_promo_rule,
        test_classify_user_corrections_19_11,
        test_classify_categories_and_attention,
        test_parse_key_cell,
        test_find_orders_in_text,
        test_group_messages_order_phone_series,
        test_group_messages_different_questions_not_merged,
        test_meta_messages_filtered,
        test_match_levels,
        test_file_names,
        test_builder_end_to_end,
    ]
    for test in tests:
        test()
        print(f"OK  {test.__name__}")
    print(f"\nВсе тесты пройдены: {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    main()