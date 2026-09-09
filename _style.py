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
