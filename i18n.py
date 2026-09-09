"""Язык интерфейса. Ключ перевода — сама русская строка."""
from PySide6.QtCore import QLocale, QSettings

LANGS = ("ru", "en")

# Отдельно от словаря: «Конспект» там же значит режим разбора.
APP_NAME = {"ru": "Konspekt", "en": "Konspekt"}

EN = {
    # единицы и мелочь
    "Б": "B", "КБ": "KB", "МБ": "MB", "ГБ": "GB", " ГБ": " GB",
    " из ": " of ", " строк": " lines", "Всего ": "Total ",
    " частей · ": " parts · ", " · голосов: ": " · voices: ",
    "» заняло ": "» took ", "готово": "done", "не найден": "not found",
    "неизвестно": "unknown", "не получилось: ": "failed: ",

    # левая панель
    "Ссылка на видео": "Video link",
    "Выбрать файл…": "Choose file…",
    "Выберите видео или аудио": "Choose video or audio",
    "Медиа (*.mp4 *.mov *.m4v *.mkv *.avi *.webm *.mp3 *.wav *.m4a)":
        "Media (*.mp4 *.mov *.m4v *.mkv *.avi *.webm *.mp3 *.wav *.m4a)",
    "Что нужно": "What you need",
    "Быстро": "Quick", "Кратко": "Short",
    "Подробно": "Detailed", "Конспект": "Notes",
    "Разделять по говорящим": "Separate speakers",
    "Полная расшифровка в конце": "Full transcript at the end",
    "Принудительно распознать речь": "Force speech recognition",
    "Учитывать комментарии": "Include comments",
    "Сколько голосов": "How many voices",
    "определить самому": "detect automatically",
    "Сделать конспект": "Summarise",
    "Отмена": "Cancel",

    # вкладки и списки
    "Ход работы": "Progress", "История": "History", "Настройки": "Settings",
    "Сохранённых конспектов пока нет": "No saved summaries yet",
    "Свернуть или показать левую панель": "Hide or show the left panel",
    "Спросите что-нибудь о видео": "Ask anything about the video",
    "загрузка модели…": "loading the model…",
    "Не получилось ответить: ": "Could not answer: ",
    "Сделать заново": "Run again",
    "Удалить конспект": "Delete summary",
    "Удалить «{name}»? Файл конспекта будет стёрт.":
        "Delete «{name}»? The summary file will be erased.",
    "О программе {name}": "About {name}",
    "Закрыть": "Close",
    "Сохранить…": "Save…", "Скопировать": "Copy", "Скопировано": "Copied",
    "Сохранить конспект": "Save summary",
    "Markdown (*.md);;Текст (*.txt)": "Markdown (*.md);;Text (*.txt)",
    "Не открылось": "Could not open",
    "Не получилось": "Something went wrong",
    "Отменено.": "Cancelled.",
    "Остановка…": "Stopping…",

    # настройки
    "Языковая модель": "Language model",
    "Распознавание речи": "Speech recognition",
    "Загрузчик видео": "Video downloader",
    "Загрузчик видео · ": "Video downloader · ",
    "Скачать": "Download", "Удалить": "Delete", "Обновить": "Update",
    "Загрузка…": "Downloading…", "Обновление…": "Updating…",
    "Использовать": "Use", "Используется": "In use",
    "нет, скачать ": "not installed, ",
    "Удалить модель": "Delete model",
    "Удалить ": "Delete ", " с диска?": " from disk?",
    "Не скачалось": "Download failed",
    "Нужна модель": "A model is required",
    "Языковая модель ещё не скачана.\n"
    "Откройте «Настройки» и выберите, какую скачать.":
        "No language model has been downloaded yet.\n"
        "Open Settings and pick one to download.",
    "Доступ к диску": "Disk access",
    "Нужно разрешение": "Permission required",
    "Этот сервис отдаёт видео только с разрешением.\nДайте полный доступ к диску и перезапустите приложение.":
        "This service serves video only with permission.\n"
        "Grant full disk access and restart the app.",
    "Открыть настройки доступа": "Open access settings",
    "Системные настройки → Конфиденциальность и безопасность → Полный доступ к диску":
        "System Settings → Privacy & Security → Full Disk Access",
    "Полный доступ к диску позволяет разбирать больше сервисов.":
        "Full disk access lets the app handle more services.",
    "Разрешите доступ в системных настройках и перезапустите Konspekt.":
        "Grant access in System Settings and restart Konspekt.",
    "Открыть настройки": "Open Settings", "Позже": "Later",
    "Язык": "Language",
    "Язык интерфейса и конспектов": "Interface and summary language",
    "Русский": "Русский", "English": "English",
    "Приложение перезапустится, чтобы применить язык.":
        "The app will restart to apply the language.",

    # ход работы
    "Получение видео": "Fetching the video",
    "Поиск готовых субтитров…": "Looking for existing subtitles…",
    "Загрузка звука": "Downloading audio",
    "Субтитров нет, загрузка звука…": "No subtitles, downloading audio…",
    "Своё распознавание, загрузка звука…":
        "Own transcription, downloading audio…",
    "Распознавание речи…": "Speech recognition…",
    "Разделение голосов": "Separating voices",
    "Разделение голосов…": "Separating voices…",
    "Разбор": "Analysing",
    "Определение имён": "Identifying names",
    "Определение имён…": "Identifying names…",
    "Сборка конспекта": "Building the summary",
    "Сборка конспекта…": "Building the summary…",
    "Разбор комментариев": "Reading comments",
    "Разбор комментариев…": "Reading comments…",
    "Готово": "Done", "Сохранено: ": "Saved: ",
    "  звуковой дорожки нет": "  no audio track",
    "Ни речи, ни текста на экране распознать не удалось.":
        "No speech and no on-screen text could be recognised.",
    "Чтение текста с экрана": "Reading on-screen text",
    "Чтение текста с экрана…": "Reading on-screen text…",
    "  видео скачать не удалось": "  could not download the video",
    "  прочитать текст с экрана не удалось: {e}":
        "  could not read on-screen text: {e}",
    "  кадров отобрано: {n}": "  frames selected: {n}",
    "  кадры извлечь не удалось: {e}": "  could not extract frames: {e}",
    "  надписей на экране: {n}": "  on-screen captions: {n}",
    "  что видно на кадрах: {n} признаков": "  visible in frames: {n} tags",
    "  комментариев много, сводка частями: {n}":
        "  many comments, summarising in {n} batches",
    "Сколько комментариев": "How many comments",
    "Отмечено зрителями:": "Marked by viewers:",
    "все": "all",
    "  комментариев очень много, оставлены верхние: {n}":
        "  a great many comments, only the top {n} kept",
    "Речи и надписей нет — сводка по комментариям и тому, что видно на кадрах.":
        "No speech or captions — summary based on comments and what is visible.",
    "Распознавать текст с кадров": "Recognise text in frames",

    # строки журнала: ключ — заготовка со скобками
    "Сводка по этой ссылке невозможна.\n"
    "Площадка не поддерживается, ролик удалён или закрыт.":
        "This link cannot be summarised.\n"
        "The site is unsupported, or the video was removed or made private.",
    "  сведения о ролике получить не удалось":
        "  could not fetch video details",
    "  субтитры «{code}»: {n} строк": "  subtitles «{code}»: {n} lines",
    "  YouTube ограничил запросы, следующий язык…":
        "  YouTube throttled the requests, trying the next language…",
    "  кусок {n} из {total}": "  chunk {n} of {total}",
    "  кусок {n} из {total} — {at}": "  chunk {n} of {total} — {at}",
    "  окон речи: {w}, голосов набралось: {v}":
        "  speech windows: {w}, voices found: {v}",
    "  уровень {level}: {a} разборов -> {b} сводок":
        "  level {level}: {a} analyses -> {b} summaries",
    "  глав от автора: {n}": "  chapters from the author: {n}",
    "  комментариев: {n}": "  comments: {n}",
    "  смотрят чужой ролик: «{title}» от {channel}":
        "  reacting to «{title}» by {channel}",
    "  нашлись, {n} строк — распознавание не нужно":
        "  found, {n} lines — no recognition needed",
    "  строк: {n}": "  lines: {n}",
    "  задано голосов: {n}": "  voices set to: {n}",
    "  голосов: {n}": "  voices: {n}",
    "  не удалось разделить голоса: {e}": "  could not separate voices: {e}",
    "Длительность ~{min} мин, кусков для разбора: {n}":
        "Duration ~{min} min, chunks to analyse: {n}",
    "  под разными номерами оказался один человек ({n}) — сведены вместе":
        "  the same person appeared under several numbers ({n}) — merged",
    "  имена определить не удалось: {e}": "  could not identify names: {e}",
    "  комментарии разобрать не удалось: {e}": "  could not read comments: {e}",
}

_lang = None


def current():
    """Настройка важнее системного языка."""
    global _lang
    if _lang is None:
        saved = QSettings("local", "Konspekt").value("lang", "")
        if saved in LANGS:
            _lang = saved
        else:
            _lang = "ru" if QLocale.system().language() == QLocale.Russian else "en"
    return _lang


def set_current(lang):
    global _lang
    if lang in LANGS:
        _lang = lang
        QSettings("local", "Konspekt").setValue("lang", lang)


def key_of(text):
    """Русский ключ по видимой надписи — для перевода собранного окна."""
    if text in EN:
        return text
    return _BACK.get(text)


_BACK = {v: k for k, v in EN.items() if v != k}


def tf(fmt, **kw):
    """Перевод заготовки со скобками и подстановка значений."""
    return t(fmt).format(**kw)


def t(s):
    """Нет в словаре — возвращаем как есть."""
    return EN.get(s, s) if current() == "en" else s
