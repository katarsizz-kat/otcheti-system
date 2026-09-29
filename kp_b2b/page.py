"""Страница Streamlit «Корпоративное предложение (B2B)»."""
from __future__ import annotations

import copy
import re
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from .core import (DEFAULT_FOOTER, DOUGHS, SIZES, TIER_TEMPLATES, fill_even, fill_template,
                   load_menu, optimize, rub, tier_totals)
from .excel import build_xlsx, read_xlsx
from .render import build_html, build_pdf

MENU_PATH = Path(__file__).resolve().parent.parent / "data" / "menu.xlsx"
TIER_NAMES = ["Базовый", "Оптимальный", "Премиальный"]
MODES = ["Шаблон тарифа", "Самый дешёвый", "Выбранные пиццы поровну", "Под бюджет"]


# ------------------------------------------------------------------ состояние
@st.cache_data(show_spinner=False)
def _menu_from_bytes(data: bytes):
    import io
    return load_menu(io.BytesIO(data))


def get_menu():
    data = st.session_state.get("menu_bytes") or MENU_PATH.read_bytes()
    return _menu_from_bytes(data)


def new_kp(menu) -> dict:
    kp = {"title": "Предложение для корпоративного заказа", "client": "",
          "addresses": [{"addr": "", "qty": 60}], "size": "40 см", "dough": "Традиционное",
          "step": 3, "footer": DEFAULT_FOOTER, "price_source": "menu", "tiers": []}
    for name in TIER_NAMES:
        items = fill_template(name, menu, kp["size"], kp["dough"], 60, 3)
        kp["tiers"].append({"name": name, "discount": 10.0, "extras_discounted": False,
                            "pizzas": [{"name": n, "qty": q} for n, q in items], "extras": []})
    return kp


def reset_editors():
    """Пересоздать таблицы-редакторы из текущего состояния КП (после автоподбора / загрузки)."""
    st.session_state["ver"] = st.session_state.get("ver", 0) + 1
    st.session_state["base"] = copy.deepcopy(st.session_state["kp"]["tiers"])
    st.session_state["base_addr"] = copy.deepcopy(st.session_state["kp"]["addresses"])


def total_target(kp) -> int:
    s = sum(int(a.get("qty") or 0) for a in kp["addresses"])
    return s if s > 0 else int(kp.get("total_manual") or 0)


def price_of(kp, menu, kind, key):
    """Цена позиции: из загруженного файла (если так выбрано) или по текущему меню."""
    if kp.get("price_source") == "file":
        p = kp.get("file_prices", {}).get(kind, {}).get(key)
        if p:
            return int(p)
    if kind == "pz":
        return menu.pizza_price(key, kp["size"])
    e = menu.extra_by_label(key)
    return e["price"] if e else None


def priced_kp(kp, menu) -> dict:
    """Копия КП с проставленными ценами — для расчёта, PDF и Excel."""
    out = copy.deepcopy(kp)
    for t in out["tiers"]:
        t["pizzas"] = [dict(r, price=price_of(kp, menu, "pz", r["name"]) or 0)
                       for r in t["pizzas"] if r.get("name") and int(r.get("qty") or 0) > 0]
        ex = []
        for r in t["extras"]:
            if not r.get("label") or int(r.get("qty") or 0) <= 0:
                continue
            e = menu.extra_by_label(r["label"])
            ex.append(dict(r, price=price_of(kp, menu, "ex", r["label"]) or 0,
                           cat=r.get("cat") or (e["cat"] if e else "")))
        t["extras"] = ex
    return out


def slug(s: str) -> str:
    s = re.sub(r"[^\w\- ]+", "", s or "").strip().replace(" ", "_")
    return s[:40] or "клиент"


# ------------------------------------------------------------------ страница
def render_page():
    try:
        st.set_page_config(page_title="КП для B2B", page_icon="🍕", layout="wide")
    except Exception:
        pass

    menu = get_menu()
    if "kp" not in st.session_state:
        st.session_state["kp"] = new_kp(menu)
        reset_editors()
    kp = st.session_state["kp"]
    ver = st.session_state["ver"]

    st.title("Корпоративное предложение")

    # ---------- загрузка сохранённого КП / меню
    c1, c2 = st.columns(2)
    with c1.expander("📂 Открыть сохранённое КП (Excel)"):
        up = st.file_uploader("Файл КП, скачанный с этой страницы", type=["xlsx"], key=f"up_{ver}")
        if up is not None and st.button("Открыть", type="primary"):
            try:
                loaded = read_xlsx(up, menu)
            except Exception as e:  # noqa: BLE001
                st.error(f"Не получилось открыть файл: {e}")
            else:
                loaded["price_source"] = "file"
                loaded["file_prices"] = {
                    "pz": {r["name"]: r["price"] for t in loaded["tiers"] for r in t["pizzas"]},
                    "ex": {r["label"]: r["price"] for t in loaded["tiers"] for r in t["extras"]},
                }
                loaded.setdefault("step", 1)
                st.session_state["kp"] = loaded
                reset_editors()
                st.rerun()
        if st.button("Начать новое КП"):
            st.session_state["kp"] = new_kp(menu)
            reset_editors()
            st.rerun()
    with c2.expander("📋 Меню и цены"):
        st.caption("По умолчанию цены берутся из файла data/menu.xlsx. "
                   "Можно загрузить свежий файл меню в том же формате — он будет действовать до закрытия вкладки.")
        mup = st.file_uploader("Файл меню (.xlsx)", type=["xlsx"], key="menu_up")
        if mup is not None:
            st.session_state["menu_bytes"] = mup.getvalue()
            st.success("Меню обновлено.")
        if kp.get("price_source") == "file" or kp.get("file_prices"):
            use_file = st.toggle("Цены из открытого КП (не пересчитывать по новому меню)",
                                 value=kp.get("price_source") == "file")
            kp["price_source"] = "file" if use_file else "menu"

    # ---------- параметры
    st.subheader("1. Параметры заказа")
    a, b = st.columns([1.2, 1])
    with a:
        kp["client"] = st.text_input("Для кого (появится в шапке)", kp.get("client", ""),
                                     placeholder='ООО "Ромашка"')
        st.caption("Адреса доставки и количество пицц на каждый")
        addr_df = pd.DataFrame(st.session_state["base_addr"] or [{"addr": "", "qty": 0}])[["qty", "addr"]]
        addr_df = st.data_editor(
            addr_df, key=f"addr_{ver}", num_rows="dynamic", width="stretch", hide_index=True,
            column_config={"addr": st.column_config.TextColumn("Адрес", width="medium"),
                           "qty": st.column_config.NumberColumn("Пицц", min_value=0, step=1, width="small")})
        kp["addresses"] = [{"addr": (r.addr or "").strip() if isinstance(r.addr, str) else "",
                            "qty": int(r.qty) if pd.notna(r.qty) else 0}
                           for r in addr_df.itertuples()]
    with b:
        s1, s2 = st.columns(2)
        kp["size"] = s1.selectbox("Размер", SIZES, index=SIZES.index(kp["size"]))
        kp["dough"] = s2.radio("Тесто", DOUGHS, index=DOUGHS.index(kp["dough"]), horizontal=True)
        s3, s4 = st.columns(2)
        if sum(a["qty"] for a in kp["addresses"]) == 0:
            kp["total_manual"] = s3.number_input("Всего пицц", 1, 2000, int(kp.get("total_manual") or 60))
        else:
            s3.metric("Всего пицц", total_target(kp))
        kp["step"] = s4.number_input("Кратность количества", 1, 10, int(kp.get("step", 1)),
                                     help="Например, 3 — количество каждой пиццы делится на 3.")
        n_tiers = st.radio("Сколько вариантов в КП", [1, 2, 3], index=len(kp["tiers"]) - 1,
                           horizontal=True)
    if n_tiers != len(kp["tiers"]):
        while len(kp["tiers"]) < n_tiers:
            name = next((n for n in TIER_NAMES if n not in [t["name"] for t in kp["tiers"]]),
                        f"Вариант {len(kp['tiers']) + 1}")
            kp["tiers"].append({"name": name, "discount": 10.0, "extras_discounted": False,
                                "pizzas": [], "extras": []})
        del kp["tiers"][n_tiers:]
        reset_editors()
        st.rerun()

    target = total_target(kp)
    eligible = sorted(menu.eligible(kp["size"], kp["dough"]))
    if kp["dough"] == "Тонкое" and kp["size"] not in ("30 см", "35 см", "40 см"):
        st.warning("Тонкое тесто бывает только 30, 35 и 40 см.")

    bcol1, bcol2 = st.columns([1.6, 2.4])
    if bcol1.button("⚡ Заполнить все варианты по шаблонам", help="Базовый / Оптимальный / Премиальный"):
        for t in kp["tiers"]:
            tpl = t["name"] if t["name"] in TIER_TEMPLATES else "Оптимальный"
            t["pizzas"] = [{"name": n, "qty": q} for n, q in
                           fill_template(tpl, menu, kp["size"], kp["dough"], target, kp["step"])]
        reset_editors()
        st.rerun()

    # ---------- варианты
    st.subheader("2. Варианты")
    base = st.session_state["base"]
    extra_labels = [e["label"] for e in menu.extras]
    pz_options = sorted(set(eligible) | {r["name"] for t in kp["tiers"] for r in t["pizzas"] if r.get("name")})
    ex_options = extra_labels + sorted({r["label"] for t in kp["tiers"] for r in t["extras"]
                                        if r.get("label") and r["label"] not in extra_labels})
    tabs = st.tabs([t["name"] or f"Вариант {i + 1}" for i, t in enumerate(kp["tiers"])])
    for i, (tab, t) in enumerate(zip(tabs, kp["tiers"])):
        with tab:
            h1, h2, h3 = st.columns([2, 1, 1.4])
            t["name"] = h1.text_input("Название варианта", t["name"], key=f"name_{i}_{ver}")
            t["discount"] = h2.number_input("Скидка, %", 0.0, 90.0, float(t.get("discount", 0)),
                                            step=1.0, key=f"disc_{i}_{ver}")
            t["extras_discounted"] = h3.checkbox("Скидка и на закуски/напитки",
                                                 t.get("extras_discounted", False), key=f"exd_{i}_{ver}")

            _autofill_block(i, t, kp, menu, eligible, target)

            left, right = st.columns([1.35, 1])
            with left:
                st.markdown("**Пиццы**")
                bp = base[i]["pizzas"] if i < len(base) else []
                df = pd.DataFrame(bp or [{"name": None, "qty": None}])[["qty", "name"]]
                df = st.data_editor(
                    df, key=f"pz_{i}_{ver}", num_rows="dynamic", width="stretch", hide_index=True,
                    column_config={
                        "name": st.column_config.SelectboxColumn("Пицца", options=pz_options, width="medium"),
                        "qty": st.column_config.NumberColumn("Кол-во", min_value=0, step=1, width="small")})
                t["pizzas"] = [{"name": r.name, "qty": int(r.qty)} for r in df.itertuples()
                               if isinstance(r.name, str) and pd.notna(r.qty) and r.qty > 0]
            with right:
                st.markdown("**Закуски и напитки**")
                be = base[i]["extras"] if i < len(base) else []
                edf = pd.DataFrame(be or [{"label": None, "qty": None}])[["qty", "label"]]
                edf = st.data_editor(
                    edf, key=f"ex_{i}_{ver}", num_rows="dynamic", width="stretch", hide_index=True,
                    column_config={
                        "label": st.column_config.SelectboxColumn("Позиция", options=ex_options, width="medium"),
                        "qty": st.column_config.NumberColumn("Кол-во", min_value=0, step=1, width="small")})
                t["extras"] = [{"label": r.label, "qty": int(r.qty)} for r in edf.itertuples()
                               if isinstance(r.label, str) and pd.notna(r.qty) and r.qty > 0]

            pt = priced_kp({**kp, "tiers": [t]}, menu)["tiers"][0]
            tot = tier_totals(pt)
            missing = [r["name"] for r in pt["pizzas"] if not r["price"]]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Пицц", tot["count"], delta=(tot["count"] - target) or None, delta_color="off")
            m2.metric("Пицца без скидки", rub(tot["pizza_sum"]))
            m3.metric("Закуски и напитки", rub(tot["extras_sum"]))
            m4.metric("К оплате", rub(tot["to_pay"]))
            if target and tot["count"] != target:
                st.warning(f"В варианте {tot['count']} пицц, а по адресам нужно {target}.")
            if missing:
                st.error("Нет цены для выбранного размера/теста: " + ", ".join(missing))

    # ---------- результат
    st.subheader("3. Готовое КП")
    kp["footer"] = st.text_area("Текст внизу", kp.get("footer", ""), height=70)
    final = priced_kp(kp, menu)
    html = build_html(final)
    preview = html.replace("</head>", "<style>html{zoom:.82} body{margin:0}</style></head>")
    if hasattr(st, "iframe"):
        st.iframe(preview, height=580)
    else:  # старые версии Streamlit
        components.html(preview, height=580, scrolling=True)

    fname = f"КП_{slug(kp.get('client'))}_{date.today():%d.%m.%Y}"
    d1, d2, _ = st.columns([1, 1, 2])
    try:
        pdf = build_pdf(final)
        d1.download_button("⬇️ Скачать PDF", pdf, f"{fname}.pdf", "application/pdf",
                           type="primary", width="stretch")
    except Exception as e:  # noqa: BLE001
        d1.error(f"PDF не собрался: {e}")
    d2.download_button("⬇️ Скачать Excel (для правок)", build_xlsx(final, menu), f"{fname}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       width="stretch")
    st.caption("Excel сохраните у себя: через несколько дней его можно открыть здесь же "
               "(«Открыть сохранённое КП») и продолжить правку. Мелкие изменения можно "
               "внести и прямо в Excel — суммы пересчитаются формулами.")


def _autofill_block(i, t, kp, menu, eligible, target):
    with st.expander("🪄 Подобрать состав автоматически", expanded=not t["pizzas"]):
        mode = st.radio("Способ", MODES, horizontal=True, key=f"mode_{i}")
        step = int(kp.get("step", 1))
        items, err = None, None
        if mode == "Шаблон тарифа":
            tpl_names = list(TIER_TEMPLATES)
            default = tpl_names.index(t["name"]) if t["name"] in tpl_names else 1
            tpl = st.selectbox("Шаблон", tpl_names, index=default, key=f"tpl_{i}")
            st.caption(", ".join(TIER_TEMPLATES[tpl]))
            if st.button("Подобрать", key=f"go_{i}", type="primary"):
                items = fill_template(tpl, menu, kp["size"], kp["dough"], target, step)
        elif mode == "Самый дешёвый":
            k = st.slider("Сколько видов пицц", 1, min(12, len(eligible)), 5, key=f"k_{i}")
            if st.button("Подобрать", key=f"go_{i}", type="primary"):
                items, err = optimize(menu, kp["size"], kp["dough"], target, kinds_min=k,
                                      kinds_max=k, step=step, goal="min")
        elif mode == "Выбранные пиццы поровну":
            chosen = st.multiselect("Какие пиццы", eligible, key=f"ch_{i}")
            if st.button("Разложить поровну", key=f"go_{i}", type="primary", disabled=not chosen):
                items = fill_even(chosen, target, step)
        else:
            c1, c2 = st.columns(2)
            budget = c1.number_input("Бюджет к оплате, ₽ (со скидкой, вместе с закусками)", 0, 10_000_000,
                                     70000, step=1000, key=f"bud_{i}")
            kmin, kmax = c2.slider("Сколько видов пицц", 1, min(12, len(eligible)), (4, 7), key=f"kk_{i}")
            only = st.multiselect("Только из этих пицц (необязательно)", eligible, key=f"only_{i}")
            ex_cost = sum(int(r["qty"]) * (price_of(kp, menu, "ex", r["label"]) or 0) for r in t["extras"])
            if ex_cost:
                st.caption(f"Закуски и напитки этого варианта ({rub(ex_cost)}) учитываются в бюджете.")
            if st.button("Подобрать под бюджет", key=f"go_{i}", type="primary"):
                items, err = optimize(menu, kp["size"], kp["dough"], target, kinds_min=kmin, kinds_max=kmax,
                                      step=step, budget=budget, discount=t["discount"],
                                      extras_cost=ex_cost, extras_discounted=t["extras_discounted"],
                                      goal="max", allowed=only or None)
        if err:
            st.error(err)
        elif items is not None:
            if not items:
                st.error("Не получилось подобрать — проверьте размер, тесто и количество.")
            else:
                t["pizzas"] = [{"name": n, "qty": q} for n, q in items]
                reset_editors()
                st.rerun()
