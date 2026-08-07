# pages/8_cart_kombo.py
"""Генератор карточек товара: расстановка вырезок на шаблоне с жёлтым эллипсом.

Размещение — по точным спецификациям (таблицы бренда):
  1168×920: пицца1 W430 X100 Y35 | пицца2 W490 X395 Y230 | пицца3 W445 X710 Y490
  640×400 : пицца1 W235 X55 Y20  | пицца2 W270 X215 Y125 | пицца3 W245 X390 Y265
  600×600 : пицца1 W220 X50 Y30  | пицца2 W250 X205 Y200 | пицца3 W230 X360 Y370
X, Y — левый верх видимой части вырезки; W — габарит (ширина для широких,
высота для вертикальных). Fill: 640×400 = FFFFFF, 600×600 = прозрачный.
Наборы 5/7/10 — ряды параллельно оси эллипса (2-1-2, 4-3, 4-3-3).
Положения корректируются вручную: стрелки (в % от карточки) + поворот.
"""
import io
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw

st.set_page_config(page_title="Генератор карточек", page_icon="🎨")

# ────────────────────────────── КОНСТАНТЫ ──────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "assets" / "card_templates"   # сюда положить шаблоны

YELLOW_RGB = (242, 221, 26)   # фирменный жёлтый
BG_RGB = (245, 247, 250)      # светлый фон шаблона 1168×920
ELLIPSE_ANGLE = -30           # наклон оси эллипса: левый верх -> правый низ

# название: (ширина, высота, прозрачный фон, цвет заливки фрейма)
PRESETS = {
    "1168×920 (сайт)": (1168, 920, False, BG_RGB),
    "640×400 (баннер)": (640, 400, False, (255, 255, 255)),   # Fill FFFFFF
    "600×600 (прозрачный)": (600, 600, True, None),           # НЕ красим
}

# Точные спецификации размещения: (W, X, Y) по позициям 1/2/3
SPEC_POS = {
    (1168, 920): ((430, 100, 35), (490, 395, 230), (445, 710, 490)),
    (640, 400): ((235, 55, 20), (270, 215, 125), (245, 390, 265)),
    (600, 600): ((220, 50, 30), (250, 205, 200), (230, 360, 370)),
}

ROLES = (
    "Главная (левый верх): пицца / закуска",
    "Доп (центр): соус, мерч, подарок",
    "Вторая (правый низ): напиток / 2-й продукт",
)
ROLE_SHORT = ("Главная", "Доп", "Напиток / 2-й")

ROW_SCHEMES = {5: (2, 1, 2), 7: (4, 3), 10: (4, 3, 3)}  # 3 — по спецификации
SET_SCALE = {5: 0.45, 7: 0.38, 10: 0.32}                # диаметр пиццы от min(W,H)
ROW_NAMES = ("Верхний ряд", "Средний ряд", "Нижний ряд")


# ────────────────────────────── ШАБЛОНЫ ──────────────────────────────
def draw_fallback_template(w: int, h: int, fill) -> Image.Image:
    """Резерв: если файла шаблона нет — рисуем эллипс сами."""
    if fill is None:
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    else:
        canvas = Image.new("RGBA", (w, h), fill + (255,))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a, b = int(w * 0.42), int(w * 0.16)
    d.ellipse([w / 2 - a, h / 2 - b, w / 2 + a, h / 2 + b], fill=YELLOW_RGB + (255,))
    layer = layer.rotate(ELLIPSE_ANGLE, resample=Image.BICUBIC)
    return Image.alpha_composite(canvas, layer)


def load_template(w: int, h: int, fill) -> Image.Image:
    path = TEMPLATE_DIR / f"template_{w}x{h}.png"
    if path.exists():
        t = Image.open(path).convert("RGBA")
        if t.size != (w, h):
            t = t.resize((w, h), Image.LANCZOS)
        return t
    return draw_fallback_template(w, h, fill)


def yellow_layer(template: Image.Image) -> Image.Image:
    """Только жёлтый эллипс (для прозрачного фона)."""
    arr = np.asarray(template.convert("RGBA")).astype(np.int16)
    mask = (arr[..., 0] > 200) & (arr[..., 1] > 170) & (arr[..., 2] < 120)
    layer = template.convert("RGBA").copy()
    layer.putalpha(Image.fromarray(np.where(mask, 255, 0).astype(np.uint8), "L"))
    return layer


def detect_ellipse(template: Image.Image) -> dict:
    """Центр, направляющая оси u (левый верх -> правый низ) и полуось a."""
    arr = np.asarray(template.convert("RGBA")).astype(np.int16)
    mask = (arr[..., 0] > 200) & (arr[..., 1] > 170) & (arr[..., 2] < 120)
    ys, xs = np.nonzero(mask)
    cx, cy = xs.mean(), ys.mean()
    x, y = xs - cx, ys - cy
    evals, evecs = np.linalg.eigh(np.cov(np.stack([x, y]).astype(float)))
    u = evecs[:, np.argmax(evals)]
    if u[0] < 0:
        u = -u
    if u[1] < 0:
        u = -u
    proj = x * u[0] + y * u[1]
    a = (proj.max() - proj.min()) / 2
    return {"center": (float(cx), float(cy)), "u": u, "a": float(a)}


# ────────────────────────────── ХОЛСТ ──────────────────────────────
def prepare_fit(img: Image.Image, box: int, rot: int = 0) -> Image.Image:
    """Кроп пустых полей -> поворот -> вписывание в box×box (пропорции)."""
    im = img.convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    im.thumbnail((box, box), Image.LANCZOS)
    return im


def paste_tl(canvas, im, x, y, clamp: bool = False):
    """Вставка по левому верхнему углу видимой части."""
    x, y = int(round(x)), int(round(y))
    if clamp:
        x = max(0, min(x, canvas.width - im.width))
        y = max(0, min(y, canvas.height - im.height))
    canvas.paste(im, (x, y), im)


# ─────────────────────── РУЧНЫЕ СМЕЩЕНИЯ ───────────────────────
def move_panel(key: str, label: str, step: int):
    """Стрелки правее/левее/выше/ниже + сброс + поворот. Смещения в % от карточки."""
    o = st.session_state.setdefault(key, {"x": 0, "y": 0})
    c = st.columns(5)
    if c[0].button("⬅️", key=f"{key}_l", help="Левее"):
        o["x"] -= step
    if c[1].button("➡️", key=f"{key}_r", help="Правее"):
        o["x"] += step
    if c[2].button("⬆️", key=f"{key}_u", help="Выше"):
        o["y"] -= step
    if c[3].button("⬇️", key=f"{key}_d", help="Ниже"):
        o["y"] += step
    if c[4].button("⟲", key=f"{key}_0", help="Сброс"):
        o.update(x=0, y=0)
    st.slider("Поворот, °", -45, 45, 0, 1, key=f"{key}_rot")
    st.caption(
        f"**{label}** · X {o['x']:+d}% · Y {o['y']:+d}% · "
        f"Поворот {int(st.session_state.get(f'{key}_rot', 0)):+d}°"
    )


def get_offs() -> dict:
    keys = ["global"] + [f"combo_{i}" for i in range(3)] + [f"set_row_{i}" for i in range(3)]
    return {
        k: {
            "x": st.session_state.get(k, {"x": 0, "y": 0})["x"],
            "y": st.session_state.get(k, {"x": 0, "y": 0})["y"],
            "rot": int(st.session_state.get(f"{k}_rot", 0)),
        }
        for k in keys
    }


# ─────────────────────────── КОМПОЗИЦИИ ───────────────────────────
def build_spec(canvas, spec, imgs, w, h, factors, adv, offs, keys):
    """Расстановка по спецификации (комбо и набор 3). Z-order: 1 -> 2 -> 3."""
    g = offs["global"]
    for i, img in enumerate(imgs):
        if img is None:
            continue
        e = offs[keys[i]]
        w0, x0, y0 = spec[i]
        im = prepare_fit(img, int(w0 * factors[i]), e["rot"])
        dx = (g["x"] + e["x"]) / 100 * w
        dy = (g["y"] + e["y"]) / 100 * h
        paste_tl(canvas, im, x0 + dx, y0 + dy, adv["clamp"])


def build_set_rows(canvas, ell, pizza, count, w, h, adv, offs):
    """Наборы 5/7/10: ряды параллельно оси эллипса."""
    m = min(w, h)
    u, C = np.array(ell["u"]), np.array(ell["center"])
    d = int(m * SET_SCALE[count] * adv["set_scale_k"])
    p = np.array([-u[1], u[0]])
    scheme = ROW_SCHEMES[count]
    gap = d * adv["row_gap"]
    step = d * (1 - adv["overlap"])
    g = offs["global"]
    for ri, cnt in enumerate(scheme):
        e = offs[f"set_row_{ri}"]
        im = prepare_fit(pizza, d, e["rot"])
        row_c = C + p * ((ri - (len(scheme) - 1) / 2) * gap)
        dx = (g["x"] + e["x"]) / 100 * w
        dy = (g["y"] + e["y"]) / 100 * h
        row_c = row_c + np.array([dx, dy])
        for i in range(cnt):
            pos = row_c + u * ((i - (cnt - 1) / 2) * step)
            x, y = pos[0] - im.width / 2, pos[1] - im.height / 2
            paste_tl(canvas, im, x, y, adv["clamp"])


def make_card(preset_name, mode, slots, count, adv, offs):
    w, h, transparent, fill = PRESETS[preset_name]
    template = load_template(w, h, fill)
    if transparent:
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        yl = yellow_layer(template)         # эллипс остаётся, фон прозрачный
        canvas.paste(yl, (0, 0), yl)
    else:
        canvas = template.copy()
    spec = SPEC_POS[(w, h)]
    if mode == "combo":
        build_spec(canvas, spec, slots, w, h,
                   (adv["f0"], adv["f1"], adv["f2"]), adv, offs,
                   [f"combo_{i}" for i in range(3)])
    elif count == 3:
        build_spec(canvas, spec, [slots[0], slots[0], slots[0]], w, h,
                   (adv["set_scale_k"], adv["set_scale_k"], adv["set_scale_k"]),
                   adv, offs, [f"set_row_{i}" for i in range(3)])
    else:
        ell = detect_ellipse(template)
        build_set_rows(canvas, ell, slots[0], count, w, h, adv, offs)
    return canvas


# ────────────────────────────── ИНТЕРФЕЙС ──────────────────────────────
st.title("🎨 Генератор карточек")
st.caption("Размещение по спецификациям бренда; доводка — стрелками и поворотом.")

mode = st.radio(
    "Режим",
    ("Разнородное комбо (до 3 позиций)", "Набор одинаковых пицц (3/5/7/10)"),
    horizontal=True,
)

files = st.file_uploader(
    "Вырезанные позиции (PNG с прозрачностью)",
    type=["png", "webp"],
    accept_multiple_files=True,
)
images = [Image.open(f).convert("RGBA") for f in files] if files else []

slots = [None, None, None]
count = 5

if mode.startswith("Разнородное"):
    chosen = []
    for i, img in enumerate(images[:3]):
        role_val = st.selectbox(
            f"Файл {i + 1} — {files[i].name}: роль",
            ROLES, index=min(i, 2), key=f"role{i}",
        )
        role = ROLES.index(role_val)
        chosen.append(role)
        slots[role] = img
    if len(set(chosen)) != len(chosen):
        st.error("Роли не должны повторяться.")
        st.stop()
else:
    count = st.selectbox("Пицц в наборе", (3, 5, 7, 10), index=0)
    if images:
        slots[0] = images[0]

with st.expander("⚙️ Настройки раскладки"):
    adv = {
        "f0": st.slider("Размер позиции 1, % от спецификации", 0.60, 1.50, 1.00, 0.05),
        "f1": st.slider("Размер позиции 2, % от спецификации", 0.60, 1.50, 1.00, 0.05),
        "f2": st.slider("Размер позиции 3, % от спецификации", 0.60, 1.50, 1.00, 0.05),
        "set_scale_k": st.slider("Масштаб набора", 0.80, 1.40, 1.00, 0.05),
        "overlap": st.slider("Перекрытие в ряду (5/7/10)", 0.20, 0.35, 0.28, 0.01),
        "row_gap": st.slider("Шаг между рядами (5/7/10)", 0.50, 1.00, 0.75, 0.05),
        "clamp": st.checkbox("Держать позиции в границах карточки", False),
    }

with st.expander("🎛 Ручная доводка (стрелки + поворот)", expanded=True):
    step = st.selectbox("Шаг стрелок, %", (1, 2, 5, 10), index=1, key="move_step")
    move_panel("global", "Вся композиция", step)
    if mode.startswith("Разнородное"):
        for role in range(3):
            if slots[role] is not None:
                move_panel(f"combo_{role}", ROLE_SHORT[role], step)
    else:
        n_rows = 3 if count == 3 else len(ROW_SCHEMES[count])
        for ri in range(n_rows):
            move_panel(f"set_row_{ri}", ROW_NAMES[ri], step)

# ────────────────────────────── РЕЗУЛЬТАТ ──────────────────────────────
if any(slots):
    st.divider()
    offs = get_offs()
    results = []
    for name in PRESETS:
        card = make_card(
            name,
            "combo" if mode.startswith("Разнородное") else "set",
            slots, count, adv, offs,
        )
        results.append((name, card))
    cols = st.columns(len(results))
    for col, (name, card) in zip(cols, results):
        w, h, _, _ = PRESETS[name]
        buf = io.BytesIO()
        card.save(buf, format="PNG")
        with col:
            st.image(card, caption=name)
            st.download_button(
                "⬇️ PNG", buf.getvalue(),
                file_name=f"card_{w}x{h}.png", mime="image/png", key=f"dl_{w}x{h}",
            )
else:
    st.info("Загрузите вырезанные позиции — карточки соберутся автоматически.")