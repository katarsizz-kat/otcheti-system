"""КП в фирменном дизайне: HTML (предпросмотр) и PDF (WeasyPrint)."""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment

from .core import SPICY, rub, tier_totals

ASSETS = Path(__file__).parent / "assets"


_MIME = {".png": "image/png", ".svg": "image/svg+xml", ".ttf": "font/ttf"}


@lru_cache
def _img(name: str) -> str:
    path = ASSETS / name
    return f"data:{_MIME[path.suffix]};base64," + base64.b64encode(path.read_bytes()).decode()


def _fonts_css() -> str:
    faces = [("Papa Sans", "fonts/PapaSans.ttf", 400),
             ("Roboto Condensed", "fonts/RobotoCondensed-Regular.ttf", 400),
             ("Roboto Condensed", "fonts/RobotoCondensed-SemiBold.ttf", 600),
             ("Roboto Condensed", "fonts/RobotoCondensed-Bold.ttf", 700)]
    return "\n".join(f'@font-face {{ font-family: "{f}"; src: url("{_img(p)}"); font-weight: {w}; }}'
                     for f, p, w in faces)


def plural_pizza(n: int) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return "пицца"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "пиццы"
    return "пицц"


def extras_label(extras: list[dict]) -> str:
    cats = {e.get("cat", "") for e in extras}
    if cats and cats <= {"Напитки"}:
        return "напитки"
    if "Напитки" in cats:
        return "закуски и напитки"
    return "доп. позиции"


TEMPLATE = r"""
<!doctype html><html lang="ru"><head><meta charset="utf-8">
<style>
{{ fonts_css|safe }}
@page { size: A4 landscape; margin: 0; background: #f4e8dc; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: "Roboto Condensed", "Liberation Sans", Arial, sans-serif;
       color: #1c2a22; background: #f4e8dc; font-size: 9pt;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { width: 297mm; background: #f4e8dc; padding-bottom: 4mm; }
.head { background: #0d3d26; color: #fff; padding: 6mm 12mm 5mm; }
.head table { width: 100%; border-collapse: collapse; }
.head img { height: 18mm; display: block; }
.head .t { text-align: right; vertical-align: middle; }
.head h1 { margin: 0; font-family: "Papa Sans", "Roboto Condensed", sans-serif; font-weight: 400;
           font-size: 21pt; letter-spacing: 0.3pt; text-transform: uppercase; }
.pp { font-family: "Papa Sans", "Roboto Condensed", sans-serif; font-weight: 400; }
.head .for { margin-top: 1.5mm; color: #c9e265; font-weight: 700; font-size: 10pt; }
.bar { background: #083625; color: #fff; padding: 2.6mm 12mm; font-size: 8.5pt; }
.bar .lbl { color: #c9e265; font-weight: 700; margin-right: 10mm; }
.bar .a { margin-right: 9mm; white-space: nowrap; }
.bar .a:before { content: "●"; color: #c9e265; font-size: 6pt; margin-right: 2mm; vertical-align: 1px; }
.cards { width: 100%; border-collapse: separate; border-spacing: 5mm 0; margin: 6mm 0 0; padding: 0 3mm; }
.card { background: #fff; border-radius: 3mm; padding: 4.5mm 4mm 4mm; vertical-align: top; }
.ttl { text-align: center; font-family: "Papa Sans", "Roboto Condensed", sans-serif; font-size: 17pt;
       color: #0d3d26; margin: 0 0 3mm; letter-spacing: 0.3pt; }
.badge { display: inline-block; background: #e12d26; color: #fff; border-radius: 6pt;
         font-family: "Roboto Condensed", sans-serif; font-size: 7.5pt; font-weight: 700; padding: 0.6mm 2mm; vertical-align: 3pt; margin-left: 1.5mm; }
.box { background: #0d3d26; border-radius: 2mm; padding: 3mm 4mm; margin-bottom: 3.5mm; }
.box table { width: 100%; border-collapse: collapse; }
.box .l { color: #c9e265; font-weight: 700; font-size: 11pt; vertical-align: middle; }
.box .r { text-align: right; vertical-align: middle; }
.box .old { color: #b9c7bd; text-decoration: line-through; font-size: 8pt; }
.box .new { color: #c9e265; font-family: "Papa Sans", "Roboto Condensed", sans-serif; font-size: 11pt;
            line-height: 1.05; letter-spacing: 0.3pt; }
table.it { width: 100%; border-collapse: collapse; font-size: 8.4pt; }
table.it th { background: #0d3d26; color: #fff; font-size: 7pt; font-weight: 700; text-transform: uppercase;
              padding: 1.6mm 1.4mm; text-align: right; white-space: nowrap; }
table.it th:first-child { text-align: left; }
table.it td { padding: 1.5mm 1.4mm; text-align: right; border-bottom: 0.2mm solid #f1e9df; white-space: nowrap; }
table.it td:first-child { text-align: left; white-space: normal; }
table.it tr:nth-child(even) td { background: #fbf6ef; }
table.it tr.sum td { background: #fff; border-top: 0.5mm solid #0d3d26; border-bottom: 0; font-weight: 700;
                      color: #0d3d26; padding-top: 2mm; }
table.it tr.sum td:first-child { white-space: normal; }
.chili { height: 3mm; vertical-align: -0.6mm; margin-left: 1mm; }
.sub { margin-top: 3mm; }
.grand { margin-top: 2.5mm; border-top: 0.5mm solid #0d3d26; padding-top: 2mm; font-weight: 700; color: #0d3d26; font-size: 8pt; }
.grand table { width: 100%; border-collapse: collapse; }
.grand td { padding: 0.6mm 1.4mm; }
.grand td.v { text-align: right; white-space: nowrap; }
.foot { background: #0d3d26; color: #fff; margin: 5mm 8mm 0; border-radius: 1.5mm; padding: 5mm 9mm;
        font-size: 9pt; line-height: 1.6; page-break-inside: avoid; }
/* плотнее, когда позиций много — чтобы всё влезло на один лист */
body.c1 table.it td { padding-top: 1.05mm; padding-bottom: 1.05mm; }
body.c1 .box { padding: 2.2mm 4mm; margin-bottom: 2.5mm; } body.c1 .cards { margin-top: 4mm; }
body.c1 .foot { margin-top: 4mm; padding: 3.5mm 9mm; } body.c1 .head { padding: 4.5mm 12mm 4mm; }
body.c2 table.it { font-size: 7.6pt; } body.c2 table.it td { padding-top: 0.6mm; padding-bottom: 0.6mm; }
body.c2 .ttl { font-size: 14pt; margin-bottom: 2mm; } body.c2 .box .new { font-size: 9pt; }
body.c2 .head img { height: 14mm; }
</style></head><body class="{{ density }}"><div class="page">
<div class="head"><table><tr>
  <td><img src="{{ logo }}" alt="Папа Джонс"></td>
  <td class="t"><h1>{{ title }}</h1>{% if client %}<div class="for">Для {{ client }}</div>{% endif %}</td>
</tr></table></div>
{% if addresses %}<div class="bar"><span class="lbl">АДРЕСА ДОСТАВКИ:</span>
{% for a in addresses %}<span class="a">{{ a.addr }}{% if a.qty %} — <b>{{ a.qty }} {{ plural(a.qty) }}</b>{% endif %}</span>{% endfor %}</div>{% endif %}
<table class="cards"><tr>
{% for t in tiers %}
<td class="card" style="width: {{ (100 / tiers|length)|round(2) }}%">
  <div class="ttl">{{ t.name|upper }}{% if t.discount %}<span class="badge">−{{ t.discount|int }}%</span>{% endif %}</div>
  <div class="box"><table><tr>
    <td class="l">{{ t.box_label }}</td>
    <td class="r">{% if t.discount %}<div class="old">{{ rub(t.tot.full) }}</div>{% endif %}
      <div class="new">{{ rub(t.tot.to_pay) }}</div></td>
  </tr></table></div>
  <table class="it">
    <tr><th>{{ pizza_head }}</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>
    {% for r in t.pizzas %}<tr><td>{{ r.name }}{% if r.name in spicy %}<img class="chili" src="{{ chili }}">{% endif %}</td>
      <td>{{ r.qty }}</td><td>{{ rub(r.price) }}</td><td>{{ rub(r.qty * r.price) }}</td></tr>{% endfor %}
    <tr class="sum"><td>Итого ({{ size_short }}{% if not t.discount %}){% else %}, без скидки){% endif %}</td>
      <td>{{ t.tot.count }}</td><td></td><td>{{ rub(t.tot.pizza_sum) }}</td></tr>
  </table>
  {% if t.extras %}
  <table class="it sub">
    <tr><th>{{ t.extras_head }}</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr>
    {% for r in t.extras %}<tr><td>{{ r.label }}</td><td>{{ r.qty }}</td><td>{{ rub(r.price) }}</td>
      <td>{{ rub(r.qty * r.price) }}</td></tr>{% endfor %}
    <tr class="sum"><td>Итого {{ t.extras_word }}</td><td></td><td></td><td>{{ rub(t.tot.extras_sum) }}</td></tr>
  </table>
  <div class="grand"><table>
    {% if t.discount %}<tr><td>Всего без скидки</td><td class="v">{{ rub(t.tot.full) }}</td></tr>{% endif %}
    <tr><td>К оплате{% if t.discount %} (скидка {{ t.discount|int }}%{% if not t.extras_discounted %} на пиццу{% endif %}){% endif %}</td>
      <td class="v">{{ rub(t.tot.to_pay) }}</td></tr>
  </table></div>
  {% endif %}
</td>
{% endfor %}
</tr></table>
{% if footer %}<div class="foot">{{ footer }}</div>{% endif %}
</div></body></html>
"""

_env = Environment(autoescape=True)
_tpl = _env.from_string(TEMPLATE)


def build_html(kp: dict) -> str:
    """kp — словарь состояния КП (см. page)."""
    size = kp["size"]
    thin = kp.get("dough") == "Тонкое"
    size_short = size.replace(" ", " ")
    tiers = []
    for t in kp["tiers"]:
        pizzas = [r for r in t["pizzas"] if r.get("name") and int(r.get("qty") or 0) > 0]
        extras = [r for r in t.get("extras", []) if r.get("label") and int(r.get("qty") or 0) > 0]
        tt = dict(t, pizzas=pizzas, extras=extras)
        tt["tot"] = tier_totals(tt)
        word = extras_label(extras)
        tt["extras_word"] = word
        tt["extras_head"] = word.upper()
        tt["box_label"] = f"Пицца {size_short}" + (" + " + word if extras else "")
        tiers.append(tt)
    addresses = [a for a in kp.get("addresses", []) if a.get("addr")]
    rows = max([len(t["pizzas"]) + (len(t["extras"]) + 5 if t["extras"] else 0) for t in tiers] or [0])
    density = "" if rows <= 10 else ("c1" if rows <= 15 else "c1 c2")
    return _tpl.render(
        logo=_img("logo_white.svg"), fonts_css=_fonts_css(), chili=_img("chili.png"),
        title=kp.get("title") or "Предложение для корпоративного заказа",
        client=kp.get("client", "").strip(), addresses=addresses,
        tiers=tiers, footer=kp.get("footer", ""), spicy=SPICY,
        pizza_head=f"Пицца ({size}{', тонкое' if thin else ''})",
        size_short=size_short, density=density, rub=rub, plural=plural_pizza,
    )


def build_pdf(kp: dict) -> bytes:
    from weasyprint import HTML
    return HTML(string=build_html(kp)).write_pdf()
