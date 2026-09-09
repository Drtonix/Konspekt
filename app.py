"""Окно Konspekt: источник слева, конспект справа, вопросы по нему внизу."""
import re, sys, subprocess, threading, time, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PySide6.QtCore import Qt, QProcess, QThread, Signal
from PySide6.QtCore import QPointF, QRectF, QSettings, QSize, QTimer
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QIcon, QIntValidator,
                           QPainter, QTextDocument, QPainterPath, QPen, QPixmap)
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QProgressBar, QPlainTextEdit, QLineEdit,
                               QTextBrowser, QFileDialog, QCheckBox, QMessageBox,
                               QFrame, QSizePolicy, QSplitter, QStackedWidget,
                               QListWidget, QListWidgetItem, QScrollArea, QMenu,
                               QMenuBar, QStyledItemDelegate)
from PySide6.QtWebEngineWidgets import QWebEngineView
from _style import STYLE
from i18n import t, tf
import i18n
import models_store

AUTHOR = "DrTonix"
SITE = "bdub.space"
URL = "https://bdub.space"

DISK_ACCESS = ("x-apple.systempreferences:com.apple.preference.security"
               "?Privacy_AllFiles")

# Папка и файл истории не переводятся: иначе при смене языка приложение
# начинает смотреть в другое место и сохранённое пропадает из списка.
OUT_DIR = Path.home() / "Documents" / "Konspekt"
OLD_DIRS = [Path.home() / "Documents" / n for n in ("Конспекты", "Summaries")]
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".mp3", ".wav", ".m4a"}

EXTRA = """
QLineEdit {
    background: rgba(255,255,255,0.07);
    border: none; border-radius: 10px;
    padding: 11px 13px; color: #e9ebef; font-size: 13px;
}
QLineEdit:focus { background: rgba(255,255,255,0.10); }
/* Цвет действия совпадает с цветом значка приложения. */
QPushButton#primary          { background: #c9433c; }
QPushButton#primary:hover    { background: #d9524a; }
QPushButton#primary:disabled { background: rgba(201,67,60,0.28); color: rgba(255,255,255,0.45); }
QPushButton#send             { background: #c9433c; }
QPushButton#send:hover       { background: #d9524a; }
QPushButton#seg:checked      { background: #c9433c; }
QPushButton#danger {
    background: rgba(255,255,255,0.10);
    color: #e9ebef;
    font-weight: 500;
}
QPushButton#danger:hover { background: rgba(255,255,255,0.15); }
QListWidget::item:selected { background: rgba(201,67,60,0.30); }
QFrame#panel {
    background: #232327;
    border: none;
    border-radius: 14px;
}
QScrollArea#feed, QWidget#feedInner { background: transparent; border: none; }
QLabel#summary { color: #dfe3ea; }
QLabel#dim { color: #9aa0a8; font-size: 12px; }
QLabel#userMsg {
    background: #c9433c;
    color: #ffffff;
    border-radius: 14px;
    padding: 10px 14px;
}
QLabel#botMsg { color: #dfe3ea; padding: 2px 2px 8px 2px; }
QFrame#divider { background: rgba(255,255,255,0.08); max-height: 1px; }

/* Меню рисуем сами: системное подсвечивает строку синим прямоугольником
   поверх скруглённой подложки. */
QMenu {
    background: #2c2c31;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 9px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 22px 6px 11px;
    border-radius: 6px;
    color: #e9ebef;
    font-size: 13px;
}
QMenu::item:selected { background: #c9433c; color: #ffffff; }
QMenu::item:disabled { color: #6b6f76; }
QMenu::item:disabled:selected { background: transparent; }

/* Список сохранённых — тот же фон и скругление, что у журнала рядом:
   иначе вкладки переключаются, а вид под ними скачет. */
QListWidget {
    background: #1a1a1d;
    border: none;
    border-radius: 12px;
    padding: 6px;
    color: #c3c8d0;
    font-size: 12px;
}
QListWidget::item {
    padding: 8px 10px;
    border-radius: 8px;
}
QListWidget::item:hover    { background: rgba(255,255,255,0.06); }
QListWidget::item:selected { background: rgba(201,67,60,0.32); color: #ffffff; }
/* Строка ввода — видимая «пилюля» поверх панели чата: фон и рамка у неё
   самой, а поле внутри прозрачное, иначе получается рамка внутри рамки. */
QFrame#composer {
    background: rgba(255,255,255,0.06);
    border: none;
    border-radius: 16px;
}
QFrame#composer QLineEdit {
    background: transparent;
    border: none;
    padding: 0 4px 0 10px;
    font-size: 13px;
}
QWidget#composerWrap { background: transparent; }
QPushButton#iconbtn {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 0;
}
QPushButton#iconbtn:hover { background: rgba(255,255,255,0.08); }
QPushButton#send {
    border: none;
    border-radius: 14px;
    padding: 0;
    color: white;
    font-size: 15px;
    font-weight: 700;
}
QPushButton#send:disabled { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.35); }
QSplitter::handle { background: transparent; width: 14px; }
"""


def _pixmap(px):
    """Холст в плотности экрана: иначе значок мылит на двукратном дисплее."""
    app = QApplication.instance()
    dpr = float(app.devicePixelRatio()) if app else 2.0
    pm = QPixmap(int(px * dpr), int(px * dpr))
    pm.fill(Qt.GlobalColor.transparent)
    pm.setDevicePixelRatio(dpr)
    return pm


def _icon_send(px=18, color="#ffffff"):
    """Стрелка вверх. Рисуем, а не берём глифом: шрифт смещает его от центра."""
    pm = _pixmap(px)
    pt = QPainter(pm)
    pt.setRenderHint(QPainter.RenderHint.Antialiasing)
    w = px * 0.13
    pen = QPen(QColor(color)); pen.setWidthF(w)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pt.setPen(pen)
    m = w                                    # поле = половина толщины с запасом
    c, top, bot = px / 2, m, px - m
    head = px * 0.28
    path = QPainterPath()
    path.moveTo(c, bot); path.lineTo(c, top)
    path.moveTo(c - head, top + head); path.lineTo(c, top); path.lineTo(c + head, top + head)
    pt.drawPath(path); pt.end()
    return QIcon(pm)


def _icon_sidebar(px=18, color="#9aa0a8"):
    """Прямоугольник с левой колонкой; рамка внутрь на полтолщины, иначе срез."""
    pm = _pixmap(px)
    pt = QPainter(pm)
    pt.setRenderHint(QPainter.RenderHint.Antialiasing)
    w = px * 0.09
    pen = QPen(QColor(color)); pen.setWidthF(w)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pt.setPen(pen)
    m = px * 0.13 + w / 2
    rect = QRectF(m, m, px - 2 * m, px - 2 * m)
    r = px * 0.14
    pt.drawRoundedRect(rect, r, r)
    x = rect.left() + rect.width() * 0.38
    # линию не ведём до самой рамки, иначе она наезжает на скругления
    pt.drawLine(QPointF(x, rect.top() + r * 0.5), QPointF(x, rect.bottom() - r * 0.5))
    pt.end()
    return QIcon(pm)


# Встраивание умеют не все площадки; без него разбор всё равно идёт.
EMBEDS = [
    (re.compile(r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/|live/)|youtu\.be/)"
                r"([A-Za-z0-9_-]{11})"),
     "https://www.youtube.com/embed/{0}?rel=0&modestbranding=1"),
    (re.compile(r"tiktok\.com/@[^/]+/video/(\d+)"),
     "https://www.tiktok.com/embed/v2/{0}"),
    (re.compile(r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)"),
     "https://www.instagram.com/p/{0}/embed"),
    (re.compile(r"vk\.com/video(-?\d+)_(\d+)"),
     "https://vk.com/video_ext.php?oid={0}&id={1}"),
    (re.compile(r"rutube\.ru/video/([0-9a-f]{32})"),
     "https://rutube.ru/play/embed/{0}"),
]


def embed_url(url):
    """Адрес встраиваемого плеера для ссылки, если площадка это умеет."""
    for pat, tpl in EMBEDS:
        m = pat.search(url or "")
        if m:
            return tpl.format(*m.groups())
    return None


class _PlayerServer:
    """Локальный сервер под плеер: без источника страницы YouTube даёт ошибку 153."""

    PAGE = """<!doctype html><html><head><meta charset="utf-8">
<!-- Скругление задаём здесь: веб-элемент своих углов скруглять не умеет,
     поэтому округляем саму страницу, а фон берём под цвет окна. -->
<style>html,body{margin:0;height:100%%;background:#1e1e20;overflow:hidden}
.box{height:100%%;border-radius:12px;overflow:hidden}
iframe{border:0;width:100%%;height:100%%;display:block}</style></head><body>
<div class="box">
<iframe src="%s"
 allow="accelerometer;autoplay;clipboard-write;encrypted-media;picture-in-picture"
 allowfullscreen></iframe></div></body></html>"""

    def __init__(self):
        self.embed = ""
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = (outer.PAGE % outer.embed).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def url(self, embed):
        self.embed = embed
        return f"http://127.0.0.1:{self.port}/?e={abs(hash(embed)) % 10**8}"


def app_icon():
    """Значок из бандла, при запуске из исходников — из проекта."""
    here = Path(__file__).resolve().parent
    for p in (here.parent / "AppIcon.icns", here / "icon" / "AppIcon.icns"):
        if p.exists():
            return QIcon(str(p))
    return QIcon()


class RowDelegate(QStyledItemDelegate):
    """Ширину строки задаёт список, а не текст: иначе длинное название
    растягивает строку за край и выделение обрезается по правой стороне."""

    def sizeHint(self, opt, index):
        return QSize(0, super().sizeHint(opt, index).height())


def md_to_html(md):
    """Markdown в HTML через QTextDocument: QLabel сам разметку не понимает."""
    doc = QTextDocument()
    doc.setDefaultFont(QFont("Helvetica Neue", 13))
    doc.setMarkdown(md or "")
    return doc.toHtml()


ACCENT = "#c9433c"      # один акцентный цвет на всё приложение


class Bar(QWidget):
    """Полоса хода работы.

    Своя, а не QProgressBar: штатная обрезает бегущий отрезок по прямой.
    """

    H = 6

    def __init__(self):
        super().__init__()
        self.setFixedHeight(self.H)
        self._busy = False
        self._pos = 0.0
        self._value = 0.0        # куда идём
        self._shown = 0.0        # что нарисовано
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def set_busy(self, on):
        self._busy = on
        self._timer.start(16) if on else self._timer.stop()
        self.update()

    def set_progress(self, cur, total):
        # Значение приходит раз в полсекунды рывками, полоса идёт к нему
        # плавно: иначе на многогигабайтной загрузке она выглядит стоящей.
        self._busy = False
        self._value = (cur / total) if total else 0.0
        if self._value <= self._shown:
            self._shown = self._value          # новая загрузка, откат к началу
        if not self._timer.isActive():
            self._timer.start(16)
        self.update()

    def _tick(self):
        if self._busy:
            self._pos = (self._pos + 0.011) % 1.0
        else:
            step = (self._value - self._shown) * 0.08
            if abs(self._value - self._shown) < 0.0002:
                self._shown = self._value
                self._timer.stop()
            else:
                self._shown += step
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        track = QPainterPath()
        track.addRoundedRect(QRectF(0, 0, w, h), r, r)
        p.setClipPath(track)
        p.fillPath(track, QColor(255, 255, 255, 16))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(ACCENT))
        if self._busy:
            seg = w * 0.32
            x = self._pos * (w + seg) - seg
            p.drawRoundedRect(QRectF(x, 0, seg, h), r, r)
        elif self._shown > 0:
            p.drawRoundedRect(QRectF(0, 0, max(h, w * self._shown), h), r, r)
        p.end()


class Worker(QThread):
    line = Signal(str)
    step = Signal(str, int, int)
    done = Signal(dict)
    failed = Signal(str)
    cancelled = Signal()
    needs_access = Signal(str)

    def __init__(self, source, style, with_transcript, with_speakers,
                 with_comments=False, own_asr=False, with_screen=False,
                 num_speakers=0, comment_limit=60, model_id=None, engine=None):
        super().__init__()
        self.source, self.style = source, style
        self.with_transcript, self.with_speakers = with_transcript, with_speakers
        self.with_comments, self.num_speakers = with_comments, num_speakers
        self.own_asr = own_asr
        self.with_screen = with_screen
        self.comment_limit = comment_limit
        self.model_id = model_id
        self.engine = engine
        self._stop = False
        self._t0 = 0.0
        self._stage_name, self._stage_t0 = "", 0.0

    def stop(self):
        self._stop = True

    @staticmethod
    def _span(sec):
        h, m, s = int(sec // 3600), int(sec // 60) % 60, int(sec) % 60
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def _log(self, msg):
        """Строка журнала со временем от начала разбора."""
        self.line.emit(f"[{self._span(time.monotonic() - self._t0)}] {msg}")

    def _stage(self, name, cur, total):
        """Смена этапа — повод записать, сколько занял предыдущий."""
        now = time.monotonic()
        if name != self._stage_name:
            if self._stage_name:
                self._log(f"  ↳ «{self._stage_name}" + t("» заняло ") + self._span(now - self._stage_t0))
            self._stage_name, self._stage_t0 = name, now
        self.step.emit(name, cur, total)

    def run(self):
        self._t0 = self._stage_t0 = time.monotonic()
        try:
            import pipeline
            r = pipeline.summarize(self.source, None, style=self.style,
                                   with_transcript=self.with_transcript,
                                   with_speakers=self.with_speakers,
                                   with_comments=self.with_comments,
                                   own_asr=self.own_asr,
                                   with_screen=self.with_screen,
                                   comment_limit=self.comment_limit,
                                   model_id=self.model_id,
                                   num_speakers=self.num_speakers,
                                   log=self._log,
                                   stage=self._stage,
                                   should_stop=lambda: self._stop,
                                   keep_engine=self.engine)
            if self._stage_name:
                self._log(f"  ↳ «{self._stage_name}" + t("» заняло ")
                          + self._span(time.monotonic() - self._stage_t0))
            self._log(t("Всего ") + self._span(time.monotonic() - self._t0))
            self.done.emit(r)
        except Exception as e:
            import pipeline
            if isinstance(e, pipeline.Cancelled):
                self.cancelled.emit()
            elif isinstance(e, pipeline.NeedsCookies):
                self.needs_access.emit(str(e))
            elif isinstance(e, pipeline.SourceError):
                # Про такое человеку нужен текст, а не разбор стека.
                self.failed.emit(str(e))
            else:
                self.failed.emit(f"{e}\n\n{traceback.format_exc()}")


class _Call(QThread):
    """Выполнить что-то долгое, не морозя окно, и вернуть строку."""
    finished_with = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        self.finished_with.emit(self.fn())


class DownloadWorker(QThread):
    # qint64, а не int: у Qt int тридцатидвухбитный, и 16 ГБ в него не влезают.
    progress = Signal("qint64", "qint64")
    done = Signal(bool, str)

    def __init__(self, repo):
        super().__init__()
        self.repo = repo
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            models_store.download(self.repo,
                                  on_progress=lambda a, b: self.progress.emit(int(a), int(b)),
                                  should_stop=lambda: self._stop)
            self.done.emit(True, "")
        except Exception as e:
            self.done.emit(False, f"{type(e).__name__}: {e}")


class AskWorker(QThread):
    answered = Signal(str)
    failed = Signal(str)
    engine_ready = Signal(object)

    def __init__(self, engine, question, context, history):
        super().__init__()
        self.engine, self.question = engine, question
        self.context, self.history = context, history

    def run(self):
        try:
            if self.engine is None:
                # Конспект из истории: движка в памяти нет, поднимаем здесь.
                import pipeline
                self.engine = pipeline.Summarizer(pipeline.MODEL_ID)
                self.engine_ready.emit(self.engine)
            self.answered.emit(self.engine.ask(self.question, self.context, self.history))
        except Exception as e:
            self.failed.emit(str(e))


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle(i18n.APP_NAME[i18n.current()])
        self.setAcceptDrops(True)
        self.settings = QSettings("local", "Konspekt")
        import pipeline
        # Браузер не выбирают: берём тот, чьи cookies читаются.
        pipeline.COOKIES = (pipeline.cookie_browsers() or [""])[0]
        g = self.settings.value("geometry")
        if g is not None:
            self.restoreGeometry(g)
        else:
            self.resize(1180, 900)
        self.setStyleSheet(STYLE + EXTRA)
        self.source = None
        self.worker = self.asker = None
        self.engine = None
        self.result_md = ""
        self.result_style = ""          # режим разбора — уходит в имя файла
        self._alive = []                # потоки живут здесь до конца run()
        self._downloading = {}          # репозиторий -> поток загрузки
        self.context = ""
        self.chat_history = []          # переписка с моделью

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        split = QSplitter(Qt.Horizontal)
        outer.addWidget(split)

        # ─────────── слева: что делаем
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(24, 20, 10, 20)
        lv.setSpacing(0)

        s = QLabel(t("Ссылка на видео")); s.setObjectName("section")
        lv.addWidget(s); lv.addSpacing(8)
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://www.youtube.com/watch?v=…")
        self.url.textChanged.connect(self._on_url)
        row = QHBoxLayout(); row.setSpacing(8)
        row.addWidget(self.url, 1)
        self.url.setFixedHeight(38)
        self.pick = QPushButton(t("Выбрать файл…"))
        self.pick.setFixedHeight(38)
        self.pick.clicked.connect(self.choose)
        row.addWidget(self.pick)
        lv.addLayout(row)

        # Плеер только для распознанных ссылок.
        self._srv = _PlayerServer()
        self.player = QWebEngineView()
        self.player.setVisible(False)
        # Фон страницы цветом окна: скругления рисует она, виджет под ней прямоугольный.
        self.player.page().setBackgroundColor(QColor("#1e1e20"))
        # Прогрев движка: иначе окно подвисает на первой ссылке.
        self.player.setUrl("about:blank")
        lv.addSpacing(12)

        s2 = QLabel(t("Что нужно")); s2.setObjectName("section")
        lv.addWidget(s2); lv.addSpacing(8)
        card = QFrame(); card.setObjectName("card")
        cl = QVBoxLayout(card); cl.setContentsMargins(16, 14, 16, 14); cl.setSpacing(13)
        seg = QFrame(); seg.setObjectName("segment")
        sl = QHBoxLayout(seg); sl.setContentsMargins(3, 3, 3, 3); sl.setSpacing(3)
        self.modes = []
        for text, key in (
                (t("Быстро"), "fast"), (t("Кратко"), "short"),
                (t("Подробно"), "full"), (t("Конспект"), "notes")):
            b = QPushButton(text); b.setObjectName("seg"); b.setCheckable(True)
            b.setAutoExclusive(True); b.setCursor(Qt.PointingHandCursor)
            b.setProperty("key", key)
            sl.addWidget(b, 1); self.modes.append(b)
        self.modes[2].setChecked(True)
        cl.addWidget(seg)
        for label, attr in ((t("Разделять по говорящим"), "speakers"),
                            (t("Полная расшифровка в конце"), "transcript"),
                            (t("Принудительно распознать речь"), "own_asr"),
                            (t("Распознавать текст с кадров"), "screen"),
                            (t("Учитывать комментарии"), "comments")):
            r = QHBoxLayout()
            cap = QLabel(label)          # подпись гасим вместе с галочкой
            r.addWidget(cap); r.addStretch()
            cb = QCheckBox(); cb.setProperty("caption", cap)
            setattr(self, attr, cb)
            r.addWidget(cb); cl.addLayout(r)
        self.transcript.setChecked(True)

        # У популярного ролика комментариев десятки тысяч — «все» это минуты.
        cr = QHBoxLayout()
        clab = QLabel(t("Сколько комментариев"))
        cr.addWidget(clab); cr.addStretch()
        self.climit = QLineEdit()
        self.climit.setObjectName("small")
        self.climit.setPlaceholderText(t("все"))
        self.climit.setFixedSize(
            QFontMetrics(self.climit.font()).horizontalAdvance(
                self.climit.placeholderText()) + 48, 30)
        self.climit.setAlignment(Qt.AlignCenter)
        cr.addWidget(self.climit)
        cl.addLayout(cr)
        self._climit_row = (clab, self.climit)

        # Точное число участников снимает вопрос дробления одного человека.
        vr = QHBoxLayout()
        vlab = QLabel(t("Сколько голосов"))
        vr.addWidget(vlab); vr.addStretch()
        # Поле, а не счётчик: число вбивают руками, «все» — подсказка в пустом.
        self.voices = QLineEdit()
        self.voices.setObjectName("small")
        self.voices.setPlaceholderText(t("определить самому"))
        self.voices.setValidator(QIntValidator(1, 12, self))
        # Ширина по подсказке: заданная на глаз упиралась в края.
        pad = 11 * 2 + 26
        wide = QFontMetrics(self.voices.font()).horizontalAdvance(
            self.voices.placeholderText()) + pad
        self.voices.setFixedSize(wide, 30)
        self.voices.setAlignment(Qt.AlignCenter)
        vr.addWidget(self.voices)
        cl.addLayout(vr)
        for w in (vlab, self.voices):
            w.setEnabled(False)
        self._voice_row = (vlab, self.voices)
        self.speakers.toggled.connect(self._sync_mode)
        self.comments.toggled.connect(self._sync_mode)
        for b in self.modes:
            b.toggled.connect(self._sync_mode)
        self._sync_mode()
        lv.addWidget(card)
        lv.addSpacing(20)

        act = QHBoxLayout(); act.setSpacing(8)
        self.go = QPushButton(t("Сделать конспект")); self.go.setObjectName("primary")
        self.go.setEnabled(False); self.go.clicked.connect(self.start)
        self.go.setFixedHeight(46)
        act.addWidget(self.go, 1)
        self.cancel = QPushButton(t("Отмена")); self.cancel.setObjectName("danger")
        self.cancel.setVisible(False); self.cancel.clicked.connect(self.stop)
        self.cancel.setFixedHeight(46); self.cancel.setFixedWidth(110)
        act.addWidget(self.cancel)
        lv.addLayout(act)

        self.progress = QWidget()
        pv = QVBoxLayout(self.progress); pv.setContentsMargins(0, 12, 0, 0); pv.setSpacing(7)
        self.stage = QLabel(" "); self.stage.setObjectName("stage")
        pv.addWidget(self.stage)
        self.bar = Bar()
        pv.addWidget(self.bar)
        self.progress.setVisible(False)
        lv.addWidget(self.progress)
        lv.addSpacing(18)

        tabs = QFrame(); tabs.setObjectName("segment")
        tl = QHBoxLayout(tabs); tl.setContentsMargins(3, 3, 3, 3); tl.setSpacing(3)
        self.tab_log = QPushButton(t("Ход работы")); self.tab_hist = QPushButton(t("История"))
        self.tab_models = QPushButton(t("Настройки"))
        for b in (self.tab_log, self.tab_hist, self.tab_models):
            b.setObjectName("seg"); b.setCheckable(True); b.setAutoExclusive(True)
            b.setCursor(Qt.PointingHandCursor); tl.addWidget(b, 1)
        self.tab_log.setChecked(True)
        self.tab_log.clicked.connect(lambda: self.bottom.setCurrentIndex(0))
        self.tab_hist.clicked.connect(self.show_history)
        self.tab_models.clicked.connect(self.show_models)
        lv.addWidget(tabs); lv.addSpacing(8)

        self.bottom = QStackedWidget()
        self.log = QPlainTextEdit(); self.log.setReadOnly(True)
        self.history = QListWidget()
        self.history.setItemDelegate(RowDelegate(self.history))
        self.history.setTextElideMode(Qt.ElideRight)
        self.history.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history.customContextMenuRequested.connect(self._history_menu)
        self.history.itemActivated.connect(self.open_from_history)
        self.history.itemClicked.connect(self.open_from_history)
        self.models_page = self._build_models()
        self.bottom.addWidget(self.log); self.bottom.addWidget(self.history)
        self.bottom.addWidget(self.models_page)
        self.bottom.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lv.addWidget(self.bottom, 1)
        # Своего минимума нет: он перебивал расчётный и сминал надписи.
        left.setSizePolicy(QSizePolicy.Preferred, left.sizePolicy().verticalPolicy())

        # ─────────── справа: сам конспект и вопросы по нему
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(10, 20, 24, 20)
        rv.setSpacing(0)

        head = QHBoxLayout()
        self.toggle = QPushButton(); self.toggle.setObjectName("iconbtn")
        self.toggle.setIcon(_icon_sidebar(18)); self.toggle.setIconSize(QSize(18, 18))
        self.toggle.setFixedSize(30, 30); self.toggle.setCursor(Qt.PointingHandCursor)
        self.toggle.setToolTip(t("Свернуть или показать левую панель"))
        self.toggle.clicked.connect(self.toggle_sidebar)
        head.addWidget(self.toggle)
        head.addStretch()
        self.save = QPushButton(t("Сохранить…")); self.save.setVisible(False)
        self.save.clicked.connect(self.save_result)
        head.addWidget(self.save)
        head.addSpacing(8)
        self.copy = QPushButton(t("Скопировать")); self.copy.setVisible(False)
        self.copy.clicked.connect(self.copy_result)
        head.addWidget(self.copy)
        rv.addLayout(head); rv.addSpacing(8)
        # Потолок по ширине и центр: иначе на широком окне кадр не 16:9.
        prow = QHBoxLayout(); prow.setContentsMargins(0, 0, 0, 0)
        prow.addStretch(); prow.addWidget(self.player); prow.addStretch()
        rv.addLayout(prow)
        self._player_gap = QWidget(); self._player_gap.setFixedHeight(10)
        self._player_gap.setVisible(False)
        rv.addWidget(self._player_gap)

        panel = QFrame(); panel.setObjectName("panel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(0, 0, 0, 0); pl.setSpacing(0)

        self.feed = QScrollArea(); self.feed.setObjectName("feed")
        self.feed.setWidgetResizable(True)
        self.feed.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setObjectName("feedInner")
        self.feed_box = QVBoxLayout(inner)
        self.feed_box.setContentsMargins(18, 16, 18, 8); self.feed_box.setSpacing(14)
        self.summary = QLabel(); self.summary.setObjectName("summary")
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.summary.setOpenExternalLinks(True)
        self.summary.setAlignment(Qt.AlignTop)
        self.feed_box.addWidget(self.summary)
        self.feed_box.addStretch(1)
        self.feed.setWidget(inner)
        pl.addWidget(self.feed, 1)

        wrap = QWidget(); wrap.setObjectName("composerWrap")
        wl = QVBoxLayout(wrap); wl.setContentsMargins(14, 6, 14, 14); wl.setSpacing(0)
        composer = QFrame(); composer.setObjectName("composer")
        wl.addWidget(composer)
        cv = QHBoxLayout(composer)
        cv.setContentsMargins(6, 6, 6, 6); cv.setSpacing(8)
        self.question = QLineEdit()
        self.question.setPlaceholderText(t("Спросите что-нибудь о видео"))
        self.question.setFixedHeight(34)
        self.question.setEnabled(False)
        self.question.returnPressed.connect(self.ask)
        cv.addWidget(self.question, 1)
        self.send = QPushButton(); self.send.setObjectName("send")
        self.send.setIcon(_icon_send(18)); self.send.setIconSize(QSize(18, 18))
        self.send.setFixedSize(30, 30); self.send.setEnabled(False)
        self.send.setCursor(Qt.PointingHandCursor)
        self.send.clicked.connect(self.ask)
        cv.addWidget(self.send)
        pl.addWidget(wrap)

        rv.addWidget(panel, 1)
        right.setMinimumWidth(420)

        # Панель в прокрутке: с плеером содержимому нужно больше, чем даёт экран ноутбука.
        self.left_panel = QScrollArea()
        self.left_panel.setObjectName("feed")
        self.left_panel.setWidgetResizable(True)
        self.left_panel.setFrameShape(QFrame.NoFrame)
        self.left_panel.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_panel.setWidget(left)
        self.left_inner = left
        split.addWidget(self.left_panel); split.addWidget(right)
        split.setStretchFactor(0, 0); split.setStretchFactor(1, 1)
        split.setSizes([420, 760])
        # Схлопывание перетаскиванием запрещено: для этого есть кнопка свёртки.
        split.setCollapsible(0, False)
        split.setCollapsible(1, False)
        # Минимумы из требований раскладки: числа на глаз тут уже подводили.
        self.setMinimumWidth(left.minimumSizeHint().width()
                             + right.minimumWidth() + 56)
        # Плеер при запуске скрыт и в расчёт минимума не попадает.
        self.setMinimumHeight(560)
        self._adopt_old()
        self._build_menu()
        QTimer.singleShot(400, self._ask_disk_access)

    def _keep(self, worker):
        """Ссылка на поток нужна до конца run(). Если она пропадёт раньше,
        Qt уронит приложение прямо из деструктора QThread."""
        self._alive.append(worker)
        worker.finished.connect(lambda w=worker: self._alive.remove(w))
        return worker

    def _card(self, box, name, role):
        """Карточка настроек: название, роль, состояние справа."""
        card = QFrame(); card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 11, 14, 11); cl.setSpacing(2)
        top = QHBoxLayout(); top.setSpacing(8)
        title = QLabel(name); title.setObjectName("cardName")
        state = QLabel(); state.setObjectName("dim")
        state.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(title); top.addStretch(); top.addWidget(state)
        cl.addLayout(top)
        sub = QLabel(role); sub.setObjectName("dim")
        cl.addWidget(sub)
        box.addWidget(card)
        return card, cl, state, sub

    def _card_buttons(self, cl, *buttons):
        row = QHBoxLayout(); row.setSpacing(8)
        row.addStretch()
        for b in buttons:
            b.setCursor(Qt.PointingHandCursor)
            row.addWidget(b)
        cl.addSpacing(6); cl.addLayout(row)

    def _build_models(self):
        """Настройки: модели, загрузчик видео и доступ к файлам."""
        page = QScrollArea(); page.setObjectName("feed")
        page.setWidgetResizable(True)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setObjectName("feedInner")
        box = QVBoxLayout(inner)
        box.setContentsMargins(2, 2, 2, 2); box.setSpacing(8)

        self.model_rows = {}
        for m in models_store.CATALOG:
            card, cl, state, _ = self._card(box, models_store.short_name(m["repo"]),
                                            t(m["role"]))
            bar = Bar(); bar.setVisible(False)
            cl.addSpacing(6); cl.addWidget(bar)
            use = QPushButton(t("Использовать")); use.setObjectName("cardbtn")
            use.clicked.connect(lambda _=False, r=m["repo"]: self._use_model(r))
            act = QPushButton()
            act.clicked.connect(lambda _=False, mm=m: self._model_action(mm))
            self._card_buttons(cl, use, act)
            self.model_rows[m["repo"]] = {"state": state, "act": act, "use": use,
                                          "bar": bar, "meta": m}

        # yt-dlp внутри бандла заморожен, а YouTube ломает его регулярно.
        _, cl, self.ytdlp_state, self.ytdlp_role = self._card(
            box, "yt-dlp", t("Загрузчик видео"))
        self.ytdlp_btn = QPushButton(t("Обновить")); self.ytdlp_btn.setObjectName("cardbtn")
        self.ytdlp_btn.clicked.connect(self._update_ytdlp)
        self._card_buttons(cl, self.ytdlp_btn)
        _, cl, self.lang_state, _ = self._card(
            box, t("Язык"), t("Язык интерфейса и конспектов"))
        self.lang_btns = []
        row = QHBoxLayout(); row.setSpacing(8); row.addStretch()
        for code, label in (("ru", "Русский"), ("en", "English")):
            b = QPushButton(label)
            b.setObjectName("cardbtnAccent" if code == i18n.current() else "cardbtn")
            b.setCursor(Qt.PointingHandCursor)
            b.setEnabled(code != i18n.current())
            b.clicked.connect(lambda _=False, c=code: self._set_lang(c))
            row.addWidget(b); self.lang_btns.append(b)
        cl.addSpacing(6); cl.addLayout(row)

        box.addStretch(1)
        sign = QLabel(f'Konspekt · {AUTHOR} · '
                      f'<a href="{URL}">{SITE}</a>')
        sign.setObjectName("dim")
        sign.setAlignment(Qt.AlignCenter)
        sign.setOpenExternalLinks(True)
        box.addWidget(sign)
        page.setWidget(inner)
        return page

    def _build_menu(self):
        """Пункт «О программе»: на macOS уходит в меню приложения."""
        bar = QMenuBar(self)
        self.about_act = QAction(tf("О программе {name}", name="Konspekt"), self)
        self.about_act.setMenuRole(QAction.AboutRole)
        self.about_act.triggered.connect(self.show_about)
        bar.addMenu("Konspekt").addAction(self.about_act)

    def show_about(self):
        box = QMessageBox(self)
        box.setIconPixmap(app_icon().pixmap(72, 72))
        box.setTextFormat(Qt.RichText)
        box.setText("<b>Konspekt</b>")
        # nobr: без него строка ломается пополам и точка-разделитель повисает.
        box.setInformativeText(
            f'<nobr>{AUTHOR} · <a href="{URL}">{SITE}</a></nobr>')
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        # Без этого ссылка в диалоге только подсвечивается и никуда не ведёт.
        for lab in box.findChildren(QLabel):
            lab.setOpenExternalLinks(True)
        box.addButton(t("Закрыть"), QMessageBox.AcceptRole)
        box.exec()

    def _ask_disk_access(self):
        """Один раз при первом запуске. Cookies браузера открывают площадки,
        которые отдают видео только вошедшим; какой браузер — выясняем сами,
        а Safari вдобавок требует полного доступа к диску."""
        import pipeline
        if self.settings.value("cookies_asked"):
            return
        self.settings.setValue("cookies_asked", "1")
        if pipeline.cookie_browsers():
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.NoIcon)
        box.setWindowTitle(t("Доступ к диску"))
        box.setText(t("Полный доступ к диску позволяет разбирать больше сервисов."))
        box.setInformativeText(t("Разрешите доступ в системных настройках "
                                 "и перезапустите Konspekt."))
        go = box.addButton(t("Открыть настройки"), QMessageBox.YesRole)
        box.setDefaultButton(box.addButton(t("Позже"), QMessageBox.NoRole))
        box.exec()
        if box.clickedButton() is go:
            subprocess.run(["open", DISK_ACCESS])

    def _set_lang(self, code):
        if code == i18n.current():
            return
        i18n.set_current(code)
        self.retranslate()

    def retranslate(self):
        """Перевод собранного окна: ключ ищется по видимой надписи."""
        self.setWindowTitle(i18n.APP_NAME[i18n.current()])
        # Пункт меню не виджет, обход по надписям его не достаёт.
        self.about_act.setText(tf("О программе {name}", name="Konspekt"))
        for w in self.findChildren(QWidget):
            for get, put in ((getattr(w, "text", None), getattr(w, "setText", None)),
                             (getattr(w, "placeholderText", None),
                              getattr(w, "setPlaceholderText", None)),
                             (getattr(w, "toolTip", None), getattr(w, "setToolTip", None))):
                if not (get and put):
                    continue
                try:
                    cur = get()
                except TypeError:            # у некоторых text() требует аргумент
                    continue
                key = i18n.key_of(cur) if cur else None
                if key:
                    put(t(key))
        # Надписи, которые собираются из кусков, проще перерисовать заново.
        self._sync_mode()
        self._refresh_models()
        self._refresh_ytdlp()
        for b, code in zip(self.lang_btns, ("ru", "en")):
            b.setObjectName("cardbtnAccent" if code == i18n.current() else "cardbtn")
            b.setEnabled(code != i18n.current())
            b.setStyleSheet("")
        if self.history.count():
            self.show_history()

    def _refresh_ytdlp(self):
        """Размер на диске справа, версия — подписью; версия спрашивается в потоке."""
        self.ytdlp_state.setText(models_store.human(self._ytdlp_size()))
        known = self.settings.value("ytdlp_version", "")
        self.ytdlp_role.setText(t("Загрузчик видео")
                                + (f" · {known}" if known else ""))
        if known:
            return
        self._ver = _Call(self._ytdlp_version)
        self._ver.finished_with.connect(self._remember_version)
        self._ver.start()

    def _remember_version(self, v):
        self.settings.setValue("ytdlp_version", v)
        self.ytdlp_role.setText(t("Загрузчик видео · ") + v)

    def _ytdlp_size(self):
        import importlib.util
        import pipeline
        spec = importlib.util.find_spec("yt_dlp")
        if spec and spec.submodule_search_locations:
            root = Path(list(spec.submodule_search_locations)[0])
            return sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
        try:
            return Path(pipeline.YTDLP[-1]).stat().st_size
        except OSError:
            return 0

    def _ytdlp_version(self):
        import pipeline
        try:
            r = subprocess.run([*pipeline.YTDLP, "--version"], capture_output=True,
                               text=True, timeout=60)
            return (r.stdout or "").strip() or t("неизвестно")
        except Exception:
            return t("не найден")

    def _update_ytdlp(self):
        import pipeline
        self.ytdlp_btn.setEnabled(False); self.ytdlp_btn.setText(t("Обновление…"))

        def work():
            # Модуль обновляется через pip, отдельный бинарник — сам.
            if pipeline.YTDLP[0] == sys.executable:
                cmd = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"]
            else:
                cmd = [*pipeline.YTDLP, "-U"]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                out = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
                return out[-1] if out else t("готово")
            except Exception as e:
                return t("не получилось: ") + str(e)

        def done(msg):
            self.ytdlp_btn.setEnabled(True); self.ytdlp_btn.setText(t("Обновить"))
            self.settings.remove("ytdlp_version")     # версия сменилась
            self._refresh_ytdlp()
            QMessageBox.information(self, t("Загрузчик видео"), msg)

        self._ydl = _Call(work)
        self._ydl.finished_with.connect(done)
        self._ydl.start()

    def _refresh_models(self):
        cur = models_store.active_llm(self.settings.value("llm_repo"))
        for repo, w in self.model_rows.items():
            if repo in self._downloading:
                continue          # у качающейся строки своя надпись и свой ход
            m = w["meta"]
            ready = models_store.is_ready(repo, m["gb"])
            size = models_store.size_on_disk(repo)
            w["state"].setText(models_store.human(size) if ready
                               else t("нет, скачать ") + f"{m['gb']:g}" + t(" ГБ"))
            w["act"].setText(t("Удалить") if ready else t("Скачать"))
            w["act"].setObjectName("cardbtn" if ready else "cardbtnAccent")
            w["act"].setStyleSheet("")            # перечитать оформление под новое имя
            # Выбранная модель показывается подписью: две красные кнопки в карточке спорят.
            w["use"].setVisible(m["kind"] == "llm" and ready)
            w["use"].setEnabled(repo != cur)
            w["use"].setText(t("Используется") if repo == cur else t("Использовать"))

    def show_models(self):
        self._refresh_models()
        self._refresh_ytdlp()
        self.bottom.setCurrentIndex(2)

    def _use_model(self, repo):
        self.settings.setValue("llm_repo", repo)
        self.engine = None                        # прежняя модель больше не годится
        self._refresh_models()

    def _model_action(self, m):
        if m["repo"] in self._downloading:
            self._downloading[m["repo"]].stop()      # недокачанное докачается потом
            return
        if models_store.is_ready(m["repo"], m["gb"]):
            if not self._confirm(
                    t("Удалить модель"),
                    t("Удалить ") + models_store.short_name(m["repo"]) + t(" с диска?"),
                    t("Удалить")):
                return
            if self.settings.value("llm_repo", models_store.DEFAULT_LLM) == m["repo"]:
                self.engine = None
            models_store.delete(m["repo"])
            self._refresh_models()
            return
        self._download(m)

    def _download(self, m):
        if m["repo"] in self._downloading:
            return
        w = self.model_rows[m["repo"]]
        w["act"].setText(t("Отмена")); w["act"].setObjectName("cardbtn")
        w["act"].setStyleSheet("")
        w["bar"].setVisible(True); w["bar"].set_progress(0, 1)
        dl = self._keep(DownloadWorker(m["repo"]))
        self._downloading[m["repo"]] = dl
        dl.progress.connect(
            lambda a, b, ww=w: (ww["bar"].set_progress(a, b),
                                ww["state"].setText(models_store.human(a) + t(" из ")
                                                    + f"{m['gb']:g}" + t(" ГБ"))))
        dl.done.connect(lambda ok, msg, ww=w: self._download_done(ww, ok, msg))
        dl.start()

    def _download_done(self, w, ok, msg):
        self._downloading.pop(w["meta"]["repo"], None)
        w["bar"].setVisible(False); w["act"].setEnabled(True)
        self._refresh_models()
        if not ok:
            QMessageBox.warning(self, t("Не скачалось"), msg)

    def _comment_limit(self):
        """Сколько комментариев брать. «все» — сколько найдётся."""
        raw = self.climit.text().strip().lower()
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        return -1                     # пусто или «все» — берём сколько есть

    # Площадки, у которых yt-dlp умеет комментарии; TikTok отдаёт только счётчик.
    COMMENT_HOSTS = ("youtube.com", "youtu.be", "instagram.com", "bilibili.com",
                     "soundcloud.com", "patreon.com", "rokfin.com", "gamejolt.com")

    def _source_kind(self):
        """Что за источник сейчас выбран: ссылка на площадку или файл с диска."""
        src = self.source or ""
        if not src.startswith(("http://", "https://")):
            return "file" if src else "none"
        return "web"

    def _sync_source(self):
        """Погасить то, что для этого источника не работает."""
        kind = self._source_kind()
        src = (self.source or "").lower()
        has_comments = kind == "web" and any(h in src for h in self.COMMENT_HOSTS)
        # Субтитры бывают только у ссылок: у файла речь распознаётся всегда.
        has_subs = kind == "web"
        self.comments.setEnabled(has_comments)
        if not has_comments:
            self.comments.setChecked(False)
        self.own_asr.setEnabled(has_subs)
        if not has_subs:
            self.own_asr.setChecked(False)
        self._sync_mode()

    def _sync_mode(self):
        """Быстрый режим гасит дополнения; поле голосов живёт с галочкой говорящих."""
        fast = any(b.isChecked() and b.property("key") == "fast" for b in self.modes)
        kind = self._source_kind()
        src = (self.source or "").lower()
        allowed = {
            self.speakers: True, self.transcript: True, self.screen: True,
            self.comments: kind == "web" and any(h in src for h in self.COMMENT_HOSTS),
            self.own_asr: kind == "web",
        }
        for w, ok in allowed.items():
            w.setEnabled(not fast and ok)
            cap = w.property("caption")
            if cap is not None:
                cap.setEnabled(w.isEnabled())
        for w in self._voice_row:
            w.setEnabled(not fast and self.speakers.isChecked())
        for w in self._climit_row:
            w.setEnabled(not fast and self.comments.isEnabled()
                         and self.comments.isChecked())

    def closeEvent(self, e):
        # Окно уносит с собой ссылки на потоки; живой поток без ссылки
        # роняет приложение из деструктора QThread.
        for w in list(self._alive):
            if hasattr(w, "stop"):
                w.stop()
            w.requestInterruption()
            w.wait(3000)
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(e)

    def _add_message(self, text, mine):
        """Сообщение блоком: своё — пузырём справа, ответ — во всю ширину."""
        row = QHBoxLayout(); row.setContentsMargins(0, 0, 0, 0)
        lab = QLabel(text)
        lab.setWordWrap(True)
        lab.setObjectName("userMsg" if mine else "botMsg")
        lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        if mine:
            lab.setMaximumWidth(int(self.feed.width() * 0.72) or 420)
            row.addStretch(1); row.addWidget(lab)
        else:
            lab.setTextFormat(Qt.RichText)
            row.addWidget(lab, 1)
        holder = QWidget(); holder.setLayout(row)
        self.feed_box.insertWidget(self.feed_box.count() - 1, holder)
        return lab

    def _scroll_down(self):
        b = self.feed.verticalScrollBar()
        QTimer.singleShot(30, lambda: b.setValue(b.maximum()))

    def _clear_messages(self):
        while self.feed_box.count() > 2:                  # подпись конспекта и распорка
            w = self.feed_box.takeAt(1).widget()
            if w:
                w.deleteLater()

    def toggle_sidebar(self):
        self.left_panel.setVisible(not self.left_panel.isVisible())
        QTimer.singleShot(0, self._fit_player)     # ширина меняется не сразу

    # ---- источник
    def _on_url(self, text):
        t = text.strip()
        self.source = t if t.startswith(("http://", "https://")) else (self.source if t else None)
        self.go.setEnabled(bool(self.source))
        self._sync_source()
        self._show_player(t)

    def _show_player(self, url):
        emb = embed_url(url)
        if emb == getattr(self, "_embed", None):
            return
        self._embed = emb
        if emb:
            self.player.setUrl(self._srv.url(emb))
            self.player.setVisible(True)
        else:
            self.player.setVisible(False)
            self.player.setUrl("about:blank")
        self._player_gap.setVisible(bool(emb))
        self._fit_player()


    def _fit_player(self):
        """Кадр 16:9 по ширине панели."""
        if not self.player.isVisible():
            return
        room = max(240, self.player.parentWidget().width() - 20)
        wide = min(room, 760)
        self.player.setFixedWidth(wide)
        self.player.setFixedHeight(int(wide * 9 / 16))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit_player()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = Path(u.toLocalFile())
            if p.suffix.lower() in VIDEO_EXT:
                self.set_file(p); break

    def choose(self):
        f, _ = QFileDialog.getOpenFileName(
            self, t("Выберите видео или аудио"), str(Path.home()),
            t("Медиа (*.mp4 *.mov *.m4v *.mkv *.avi *.webm *.mp3 *.wav *.m4a)"))
        if f:
            self.set_file(Path(f))

    def set_file(self, p):
        self.source = str(p)
        self._sync_source()
        self.url.setText(p.name)
        self.go.setEnabled(True)
        self._show_player("")

    def _busy(self, on):
        for w in (self.go, self.pick, self.url, self.transcript, self.speakers, *self.modes):
            w.setEnabled(not on)
        self.cancel.setVisible(on)
        self.progress.setVisible(on)
        if not on:
            self.bar.set_busy(False)

    # ---- разбор
    def start(self):
        if not self.source:
            return
        # Без модели разбирать нечего — отправляем в настройки.
        repo = models_store.active_llm(self.settings.value("llm_repo"))
        gb = next((m["gb"] for m in models_store.CATALOG if m["repo"] == repo), 0)
        if not models_store.is_ready(repo, gb):
            QMessageBox.information(
                self, t("Нужна модель"),
                t("Языковая модель ещё не скачана.\n"
                "Откройте «Настройки» и выберите, какую скачать."))
            self.tab_models.setChecked(True)
            self.show_models()
            return
        style = next(b.property("key") for b in self.modes if b.isChecked())
        self.result_style = style
        self.log.clear(); self.result_md = ""; self.chat_history = []
        self.save.setVisible(False); self.copy.setVisible(False)
        self.question.setEnabled(False); self.send.setEnabled(False)
        self.summary.setText(""); self._clear_messages()
        self._busy(True)
        # Только по именам: позиционный вызов однажды разъехался с объявлением.
        self.worker = self._keep(Worker(
            self.source, style,
            with_transcript=self.transcript.isChecked(),
            with_speakers=self.speakers.isChecked(),
            with_comments=self.comments.isChecked(),
            own_asr=self.own_asr.isChecked(),
            with_screen=self.screen.isChecked(),
            comment_limit=self._comment_limit(),
            num_speakers=min(12, int(self.voices.text() or 0)),
            model_id=models_store.active_llm(self.settings.value("llm_repo")),
            engine=self.engine))
        self.worker.line.connect(self.log.appendPlainText)
        self.worker.step.connect(self.on_step)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.cancelled.connect(self.on_cancelled)
        self.worker.needs_access.connect(self.on_needs_access)
        self.worker.start()

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.cancel.setEnabled(False)
            self.stage.setText(t("Остановка…"))

    def on_step(self, name, cur, total):
        self.stage.setText(f"{name}…" + (f"   {cur} из {total}" if total > 1 else ""))
        if total > 1:
            self.bar.set_progress(cur, total)
        else:
            self.bar.set_busy(True)

    def on_done(self, r):
        self._busy(False); self.cancel.setEnabled(True)
        self.result_md = r.get("markdown", "")
        self.result_name = r.get("title", t("Конспект"))
        self.engine = r.get("engine")            # остаётся в памяти — для вопросов
        self.context = r.get("context", "")
        parts = f"{r['parts']}" + t(" частей · ") + f"{r['segments']}" + t(" строк")
        if r.get("speakers"):
            parts += t(" · голосов: ") + str(r["speakers"])
        self.summary.setText(md_to_html(self.result_md))
        self._clear_messages()
        self.save.setVisible(True); self.copy.setVisible(True)
        self.question.setEnabled(True); self.send.setEnabled(True)

    def on_cancelled(self):
        self._busy(False); self.cancel.setEnabled(True)
        self.stage.setText(" ")
        self.log.appendPlainText(t("Отменено."))
        self.summary.setText(""); self._clear_messages()

    def on_needs_access(self, msg):
        """Отказ, который лечится разрешением: показываем, куда идти."""
        self._busy(False); self.cancel.setEnabled(True)
        self.log.appendPlainText(msg)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.NoIcon)
        box.setTextFormat(Qt.RichText)
        box.setWindowTitle(t("Нужно разрешение"))
        box.setText(msg.split("\n\n")[0].replace("\n", "<br>"))
        box.setInformativeText(
            f'<a href="{DISK_ACCESS}">' + t("Открыть настройки доступа") + "</a>"
            + "<br><br>" + t("Системные настройки → Конфиденциальность и "
                             "безопасность → Полный доступ к диску"))
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        for lab in box.findChildren(QLabel):
            lab.setOpenExternalLinks(True)
        box.addButton(t("Закрыть"), QMessageBox.AcceptRole)
        box.exec()

    def on_failed(self, msg):
        self._busy(False); self.cancel.setEnabled(True)
        self.log.appendPlainText(msg)
        # До пустой строки — текст для человека, дальше ответ программы.
        QMessageBox.critical(self, t("Не получилось"), msg.split("\n\n")[0])

    # ---- вопросы по видео
    def ask(self):
        q = self.question.text().strip()
        if not q:
            return
        self.question.clear()
        self.question.setEnabled(False); self.send.setEnabled(False)
        self._add_message(q, mine=True)
        self._thinking = self._add_message(
            "…" if self.engine else t("загрузка модели…"), mine=False)
        self._scroll_down()
        self._pending_q = q
        self.asker = self._keep(
            AskWorker(self.engine, q, self.context, self.chat_history))
        self.asker.answered.connect(self.on_answer)
        self.asker.engine_ready.connect(lambda e: setattr(self, "engine", e))
        self.asker.failed.connect(lambda m: self.on_answer(f"Не получилось ответить: {m}"))
        self.asker.start()

    def on_answer(self, text):
        self._thinking.setText(md_to_html(text))
        self.chat_history.append((self._pending_q, text))
        self._scroll_down()
        self.question.setEnabled(True); self.send.setEnabled(True)
        self.question.setFocus()

    # ---- история
    def _index_path(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        return OUT_DIR / "history.json"

    def _adopt_old(self):
        """Перенести конспекты из папок прежних версий: они назывались по языку
        интерфейса, поэтому их две и в каждой своя половина."""
        import json
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        moved = []
        for old in OLD_DIRS:
            if not old.is_dir() or old == OUT_DIR:
                continue
            for f in old.glob("*.md"):
                dst = OUT_DIR / f.name
                if not dst.exists():
                    f.replace(dst)
                    moved.append(dst)
            for idx in old.glob("*.json"):
                idx.unlink(missing_ok=True)
            try:
                old.rmdir()
            except OSError:
                pass                  # осталось что-то чужое — не трогаем
        return moved

    def _known_files(self):
        """Список из индекса плюс всё, что просто лежит в папке: потерянный
        индекс не должен прятать сохранённое."""
        import json
        items = [x for x in self._load_index() if Path(x["path"]).exists()]
        have = {x["path"] for x in items}
        for f in sorted(OUT_DIR.glob("*.md"), key=lambda x: -x.stat().st_mtime):
            if str(f) in have:
                continue
            head = ""
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    if line.startswith("# "):
                        head = line[2:].strip()
                        break
            except OSError:
                pass
            items.append({"path": str(f), "title": head or f.stem, "source": ""})
        return items

    def _load_index(self):
        import json
        p = self._index_path()
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _remember(self, path, title, source):
        import json
        items = [x for x in self._load_index() if x.get("path") != str(path)]
        items.insert(0, {"path": str(path), "title": title, "source": source,
                         "style": self.result_style})
        self._index_path().write_text(json.dumps(items[:100], ensure_ascii=False, indent=1),
                                      encoding="utf-8")
        # Перерисовываем сразу: иначе сохранённое видно лишь после смены вкладки.
        self._fill_history()

    def show_history(self):
        self._fill_history()
        self.bottom.setCurrentIndex(1)

    def _fill_history(self):
        self.history.clear()
        for it in self._known_files():
            row = QListWidgetItem(it["title"])
            row.setToolTip(it.get("source") or it["path"])
            row.setData(Qt.UserRole, it)
            self.history.addItem(row)
        if self.history.count() == 0:
            self.history.addItem(QListWidgetItem(t("Сохранённых конспектов пока нет")))

    def _confirm(self, title, text, ok):
        """Свои надписи на кнопках: штатные Yes/No остаются английскими."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.NoIcon)
        box.setWindowTitle(title)
        box.setText(text)
        yes = box.addButton(ok, QMessageBox.YesRole)
        box.setDefaultButton(box.addButton(t("Отмена"), QMessageBox.NoRole))
        box.exec()
        return box.clickedButton() is yes

    def _history_menu(self, pos):
        item = self.history.itemAt(pos)
        it = item.data(Qt.UserRole) if item else None
        if not it:
            return
        menu = QMenu(self)
        # Иначе за скруглением остаётся квадратный угол системной подложки.
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint
                            | Qt.NoDropShadowWindowHint)
        again = menu.addAction(t("Сделать заново"))
        again.setEnabled(bool(it.get("source")))
        drop = menu.addAction(t("Удалить"))
        picked = menu.exec(self.history.viewport().mapToGlobal(pos))
        if picked is again:
            self._repeat(it)
        elif picked is drop:
            self._forget(it)

    def _repeat(self, it):
        """Источник конспекта обратно в панель; запуск остаётся за человеком."""
        src = it.get("source") or ""
        if src.startswith("http"):
            self.url.setText(src)
        elif src:
            self.set_file(Path(src))
        self.tab_log.setChecked(True)
        self.bottom.setCurrentIndex(0)

    def _forget(self, it):
        import json
        if not self._confirm(t("Удалить конспект"),
                             tf("Удалить «{name}»? Файл конспекта будет стёрт.",
                                name=it["title"]), t("Удалить")):
            return
        Path(it["path"]).unlink(missing_ok=True)
        items = [x for x in self._load_index() if x.get("path") != it["path"]]
        self._index_path().write_text(json.dumps(items, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
        self._fill_history()

    def open_from_history(self, item):
        it = item.data(Qt.UserRole)
        if not it:
            return
        try:
            self.result_md = Path(it["path"]).read_text(encoding="utf-8")
        except Exception as e:
            QMessageBox.warning(self, t("Не открылось"), str(e)); return
        self.result_name = it["title"]
        self.result_style = it.get("style", "")
        self.context = self.result_md      # материалы для вопросов — сам конспект
        self.chat_history = []
        self.summary.setText(md_to_html(self.result_md))
        self._clear_messages()
        self.save.setVisible(True); self.copy.setVisible(True)
        self.question.setEnabled(True); self.send.setEnabled(True)
        src = it.get("source") or ""
        if src.startswith("http"):
            self.url.setText(src)        # ссылка подставляется, плеер оживает сам

    def _free_path(self, base):
        """Свободное имя: «… 2», «… 3». Иначе система переспрашивает про замену."""
        path, n = OUT_DIR / f"{base}.md", 1
        while path.exists():
            n += 1
            path = OUT_DIR / f"{base} {n}.md"
        return path

    def save_result(self):
        if not self.result_md:
            return
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        safe = "".join(c for c in self.result_name if c not in '/\\:*?"<>|')[:80] or t("Конспект")
        mode = next((b.text() for b in self.modes
                     if b.property("key") == self.result_style), "")
        path, _ = QFileDialog.getSaveFileName(
            self, t("Сохранить конспект"),
            str(self._free_path(f"{safe} — {mode}" if mode else safe)),
            t("Markdown (*.md);;Текст (*.txt)"))
        if path:
            Path(path).write_text(self.result_md, encoding="utf-8")
            self._remember(path, self.result_name, self.source or "")

    def copy_result(self):
        if self.result_md:
            QApplication.clipboard().setText(self.result_md)
            self.copy.setText(t("Скопировано"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(t("Конспект"))
    w = Window(); w.show()
    sys.exit(app.exec())
