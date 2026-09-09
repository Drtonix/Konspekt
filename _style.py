"""Оформление, общее с Dubl."""
STYLE = """
/* Пунктирная рамка фокуса на тёмном фоне читается как россыпь точек. */
* { outline: none; }
QAbstractScrollArea, QScrollArea, QListWidget { outline: none; }

QWidget#root { background: #1e1e20; }

/* Только имена, которые Qt находит: ".AppleSystemUIFont" роняет приложение. */
QWidget {
    font-family: "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* Без своей подложки: внутри скруглённых блоков проступают прямоугольники. */
QLabel, QCheckBox { background: transparent; color: #e9ebef; font-size: 13px; }
/* Подпись гаснет вместе с галочкой. */
QLabel:disabled, QCheckBox:disabled { color: #6b6f76; }
QCheckBox::indicator:disabled { background: rgba(255,255,255,0.04); }

QLabel#section  { font-size: 12px; color: #8a8f98; padding-left: 4px; }
QLabel#dropTitle{ font-size: 16px; color: #f4f5f7; }
QLabel#dropHint { font-size: 12px; color: #75797f; }
QLabel#stage    { font-size: 12px; color: #8a8f98; }
QLabel#hint     { font-size: 12px; color: #75797f; }

QFrame#card {
    background: #26262a;
    border: none;
    border-radius: 14px;
}
QFrame#drop {
    background: #232327;
    border: none;
    border-radius: 14px;
}
QFrame#dropOn {
    background: #1e2836;
    border: 1px solid #c9433c;
    border-radius: 14px;
}

QPushButton {
    background: rgba(255,255,255,0.07);
    border: none;
    border-radius: 9px;
    padding: 8px 16px;
    color: #e9ebef;
    font-size: 13px;
}
QPushButton:hover    { background: rgba(255,255,255,0.11); }
QPushButton:disabled { color: #5c5f65; background: rgba(255,255,255,0.04); }

QPushButton#primary {
    background: #c9433c;
    border-radius: 12px;
    color: white;
    font-size: 15px;
    font-weight: 600;
    padding: 15px;
}
QPushButton#primary:hover    { background: #d9524a; }
QPushButton#primary:disabled { background: rgba(201,67,60,0.28); color: rgba(255,255,255,0.4); }

/* Кнопки карточек: #primary сделан под большую кнопку и рядом смотрится вдвое крупнее. */
QPushButton#cardbtn, QPushButton#cardbtnAccent {
    border-radius: 9px;
    padding: 0 14px;
    font-size: 13px;
    min-height: 30px;
    max-height: 30px;
}
QPushButton#cardbtn          { background: rgba(255,255,255,0.09); color: #e9ebef; }
QPushButton#cardbtn:hover    { background: rgba(255,255,255,0.14); }
QPushButton#cardbtn:disabled { background: rgba(255,255,255,0.05); color: #6b6f76; }
QPushButton#cardbtnAccent          { background: #c9433c; color: white; font-weight: 600; }
QPushButton#cardbtnAccent:hover    { background: #d9524a; }
QPushButton#cardbtnAccent:disabled { background: rgba(201,67,60,0.28); color: rgba(255,255,255,0.4); }
QLabel#cardName { color: #e9ebef; font-size: 14px; }

QFrame#segment {
    background: rgba(255,255,255,0.06);
    border-radius: 10px;
}
QPushButton#seg {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 7px 10px;
    color: #a9adb5;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#seg:hover   { color: #e9ebef; }
QPushButton#seg:checked { background: #c9433c; color: white; font-weight: 600; }

QComboBox {
    background: rgba(255,255,255,0.07);
    border: none;
    border-radius: 9px;
    padding: 7px 12px;
    min-width: 150px;
    color: #e9ebef;
}
QComboBox::drop-down { border: none; width: 22px; }

/* Поле в карточке: снизу на 2px больше — у подсказки только нижние выносы. */
QLineEdit#small { padding: 4px 11px 6px 11px; }
QLineEdit#small:disabled { color: rgba(233,235,239,0.35); }


QCheckBox::indicator {
    width: 18px; height: 18px;
    border-radius: 6px;
    background: rgba(255,255,255,0.09);
}
QCheckBox::indicator:checked { background: #c9433c; }

QProgressBar {
    background: rgba(255,255,255,0.06);
    border: none;
    border-radius: 3px;
    height: 6px;
}
QProgressBar::chunk { background: #c9433c; border-radius: 3px; }

QPlainTextEdit {
    background: #1a1a1d;
    border: none;
    border-radius: 12px;
    padding: 10px;
    color: #a8adb6;
    font-family: Menlo, monospace;
    font-size: 11px;
}
"""


import colorsys  # noqa: E402
import re  # noqa: E402

LIGHT = {
    "#1e1e20": "#e8e9ec", "#19191c": "#dfe0e4", "#1a1a1d": "#f1f2f5",
    "#232327": "#ffffff", "#26262a": "#ffffff", "#2c2c31": "#ffffff", "#2c2c32": "#ffffff",
    "#333338": "#d9dbe0",
    "#e9ebef": "#1d1f24", "#f4f5f7": "#111318", "#a8adb6": "#4a4f58", "#a9adb5": "#5a5f68",
    "#8a8f98": "#6a6f78", "#75797f": "#80858d", "#6b6f76": "#9aa0a8", "#5c5f65": "#a9adb3",
}


def light_hex(h):
    """Подложки светлеют, серый текст темнеет; бледные тона акцента густеют,
    чтобы читаться на светлом. Сам акцент не меняется."""
    h = h.lower()
    if h in LIGHT:
        return LIGHT[h]
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hue, lum, sat = colorsys.rgb_to_hls(r, g, b)
    if lum < 0.22 or sat < 0.2:
        lum = 1 - lum * 0.85 if lum < 0.5 else max(0.1, 1.04 - lum)
    elif lum > 0.8:
        lum, sat = 0.5, sat * 0.7
    else:
        return h
    return "#" + "".join(f"{round(c * 255):02x}" for c in colorsys.hls_to_rgb(hue, lum, sat))


def _light_rgba(m):
    r, g, b, a = m.group(1), m.group(2), m.group(3), float(m.group(4))
    if (r, g, b) == ("255", "255", "255"):
        return f"rgba(0,0,0,{a * 0.8:.3g})"
    h = light_hex("#" + "".join(f"{int(x):02x}" for x in (r, g, b)))
    return f"rgba({int(h[1:3], 16)},{int(h[3:5], 16)},{int(h[5:7], 16)},{a:g})"


def light(css):
    """Белые заливки становятся чёрными. Текст на акценте (#1e1e20, #ffffff)
    остаётся каким был."""
    def decl(m):
        prop, value = m.group(1), m.group(2)
        if prop.strip() == "color" and value.strip().lower() in ("#1e1e20", "#ffffff"):
            return m.group(0)
        value = re.sub(r"#[0-9a-fA-F]{6}\b", lambda x: light_hex(x.group(0)), value)
        value = re.sub(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", _light_rgba, value)
        return f"{prop}:{value}"
    return re.sub(r"([\w-]+\s*):([^;{}]+)", decl, css)
