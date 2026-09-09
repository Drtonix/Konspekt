#!/bin/zsh
# Самодостаточный Konspekt.app: свой Python, библиотеки, ffmpeg и yt-dlp.
# Веса моделей качаются из вкладки «Модели» — иначе бандл на двадцать гигабайт.
set -e
cd "${0:A:h}"
SRC="$PWD"
OUT="$SRC/build"
APP="$OUT/Konspekt.app"
PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/20260901/cpython-3.12.14%2B20260901-aarch64-apple-darwin-install_only_stripped.tar.gz"

say() { print -P "%F{green}==>%f $*"; }

rm -rf "$APP"
mkdir -p "$OUT" "$APP/Contents/MacOS" "$APP/Contents/Resources"
RES="$APP/Contents/Resources"

say "переносимый Python"
if [ ! -f "$OUT/python.tar.gz" ]; then
    curl -fsSL "$PY_URL" -o "$OUT/python.tar.gz"
fi
mkdir -p "$RES/python"
tar xzf "$OUT/python.tar.gz" -C "$RES/python" --strip-components=1
PY="$RES/python/bin/python3"

say "библиотеки"
"$PY" -m pip -q install --upgrade pip
# yt-dlp модулем: бинарник распаковывает себя каждый запуск, восемь секунд.
"$PY" -m pip -q install PySide6 mlx-lm mlx-whisper sherpa-onnx soundfile scipy numpy yt-dlp \
    pyobjc-framework-Vision pyobjc-framework-Quartz
# torch приходит с mlx-whisper, но нужен ему только numba.
"$PY" -m pip -q uninstall -y torch sympy networkx 2>/dev/null || true

say "чистка лишнего"
SP="$RES/python/lib/python3.12/site-packages"
# Лишние модули Qt; веб-движок оставляем — на нём плеер.
for m in Qt3D QtCharts QtDataVis QtDesigner QtQuick3D QtSensors QtSerial QtSql \
         QtTest QtBluetooth QtNfc QtRemoteObjects QtScxml QtSpatialAudio \
         QtStateMachine QtTextToSpeech QtHelp QtUiTools QtMultimedia QtPdf; do
    rm -rf "$SP/PySide6/Qt/lib/${m}"*.framework "$SP/PySide6/${m}"* 2>/dev/null || true
done
rm -rf "$SP/PySide6/Qt/translations" "$SP/PySide6/Qt/qml" \
       "$SP/PySide6/Designer.app" "$SP/PySide6/assistant.app" \
       "$SP/PySide6/linguist.app" "$SP/PySide6/examples" 2>/dev/null || true
find "$SP" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
# dist-info не трогаем: без них transformers падает на проверке версий.
find "$RES/python/lib" -name "test" -type d -prune -exec rm -rf {} + 2>/dev/null || true

say "ffmpeg"
# Своя сборка: готовые либо x86_64, либо с --enable-nonfree (распространять
# нельзя). Здесь arm64 и чистый LGPL 2.1. Результат кэшируется.
mkdir -p "$RES/app/bin" "$OUT/tools"
if [ ! -f "$OUT/tools/ffmpeg" ]; then
    say "  собираю ffmpeg из исходников, это долго"
    rm -rf "$OUT/ffsrc"; mkdir -p "$OUT/ffsrc"
    curl -fsSL "https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz" -o "$OUT/ffsrc/ff.tar.xz"
    tar xf "$OUT/ffsrc/ff.tar.xz" -C "$OUT/ffsrc" --strip-components=1
    ( cd "$OUT/ffsrc" && ./configure --prefix="$OUT/ffsrc/out" --disable-doc \
        --disable-ffplay --disable-debug --enable-small --disable-network \
        --disable-autodetect --enable-zlib --enable-videotoolbox >/dev/null 2>&1 \
      && make -j"$(sysctl -n hw.ncpu)" >/dev/null 2>&1 \
      && make install >/dev/null 2>&1 )
    cp "$OUT/ffsrc/out/bin/ffmpeg" "$OUT/ffsrc/out/bin/ffprobe" "$OUT/tools/"
    rm -rf "$OUT/ffsrc"
fi
cp "$OUT/tools/ffmpeg" "$OUT/tools/ffprobe" "$RES/app/bin/"
chmod +x "$RES/app/bin/"*

say "исходники и модели"
cp app.py pipeline.py diarize_cli.py _style.py models_store.py i18n.py \
   screen_text.py "$RES/app/"
mkdir -p "$RES/app/models"
./fetch_models.sh
cp models/silero_vad.onnx models/nemo_en_titanet_large.onnx "$RES/app/models/"

say "лицензии"
# Qt и ffmpeg под LGPL: распространение требует текстов лицензий и ссылки
# на исходники. Остальное разрешительное, но уведомления тоже обязательны.
LIC="$RES/Лицензии"
mkdir -p "$LIC"
# find, а не шаблон: zsh на пустом совпадении падает, а с set -e рвёт сборку.
find "$SP" -maxdepth 1 -type d -name "*.dist-info" | while read -r d; do
    pkg=$(basename "$d" .dist-info)
    find "$d" -maxdepth 2 \( -name "LICENSE*" -o -name "COPYING*" -o -name "NOTICE*" \) \
        -type f 2>/dev/null | while read -r f; do
        mkdir -p "$LIC/$pkg"
        cp "$f" "$LIC/$pkg/" 2>/dev/null || true
    done
done
cat > "$LIC/О лицензиях.txt" <<'LICNOTE'
Из чего собран Konspekt и на каких условиях.

Qt / PySide6 — LGPL 3.0
    Библиотеки Qt лежат в приложении отдельными файлами и не вкомпилированы
    в него, поэтому их можно заменить своими сборками. Исходники:
    https://download.qt.io/official_releases/qt/

ffmpeg — LGPL 2.1 или новее
    Собран из исходников ffmpeg 7.1 без внешних библиотек и без частей
    под GPL: ./configure --disable-doc --disable-ffplay --disable-debug
    --enable-small --disable-network --disable-autodetect --enable-videotoolbox
    Исходники: https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz

yt-dlp — Unlicense (общественное достояние)
Python — PSF License
mlx, mlx-lm, mlx-whisper — MIT
sherpa-onnx, huggingface_hub, transformers — Apache 2.0
numpy, scipy, numba — BSD
libsndfile (через soundfile) — LGPL 2.1

Полные тексты — в папках рядом, по одной на пакет.

Модели нейросетей в приложение не входят и скачиваются отдельно:
Qwen3 — Apache 2.0, Whisper — MIT.
LICNOTE
echo "  собрано лицензий: $(ls -1 "$LIC" | wc -l | tr -d ' ')"

say "интерпретатор в MacOS"
# Приложение опознаётся по пути процесса: питон из Resources даёт в доке
# ракету и имя «python3». Интерпретатор кладём в MacOS, рядом pyvenv.cfg
# с путём к настоящей установке.
cp "$RES/python/bin/python3.12" "$APP/Contents/MacOS/python"
cat > "$APP/Contents/MacOS/pyvenv.cfg" <<CFG
home = $RES/python/bin
include-system-site-packages = true
version = 3.12.14
CFG

say "оболочка"
cat > "$APP/Contents/MacOS/launcher" <<'LAUNCH'
#!/bin/zsh
LOG="$HOME/Library/Logs/Konspekt.log"
mkdir -p "$HOME/Library/Logs"
exec >> "$LOG" 2>&1
echo "=== запуск $(date) ==="
DIR="${0:A:h}"
RES="$DIR/../Resources"
export PATH="$RES/app/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export TOKENIZERS_PARALLELISM=false
# Путь в pyvenv.cfg абсолютный: после переноса переписываем под текущий.
WANT="home = $RES/python/bin"
if [ "$(head -1 "$DIR/pyvenv.cfg" 2>/dev/null)" != "$WANT" ]; then
    printf '%s\ninclude-system-site-packages = true\nversion = 3.12.14\n' \
        "$WANT" > "$DIR/pyvenv.cfg"
fi
cd "$RES/app"
exec "$DIR/python" "$RES/app/app.py"
LAUNCH
chmod +x "$APP/Contents/MacOS/launcher"
# Значок из проекта: иначе сборка требует уже установленного приложения.
cp icon/AppIcon.icns "$RES/AppIcon.icns"

# Имя в доке по языку системы.
mkdir -p "$RES/ru.lproj" "$RES/en.lproj"
printf '"CFBundleDisplayName" = "Konspekt";\n"CFBundleName" = "Konspekt";\n' \
    > "$RES/ru.lproj/InfoPlist.strings"
cp "$RES/ru.lproj/InfoPlist.strings" "$RES/en.lproj/InfoPlist.strings"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleDevelopmentRegion</key><string>ru</string>
<key>CFBundleDisplayName</key><string>Konspekt</string>
<key>CFBundleExecutable</key><string>launcher</string>
<key>CFBundleIconFile</key><string>AppIcon</string>
<key>CFBundleIdentifier</key><string>com.local.summary</string>
<key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
<key>CFBundleName</key><string>Konspekt</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>LSMinimumSystemVersion</key><string>13.0</string>
<key>CFBundleLocalizations</key><array><string>ru</string><string>en</string></array>
<key>NSHighResolutionCapable</key><true/>
<key>NSDocumentsFolderUsageDescription</key><string>Konspekt сохраняет готовые конспекты в папку «Документы».</string>
<key>NSDownloadsFolderUsageDescription</key><string>Konspekt может сохранять конспекты в папку «Загрузки».</string>
<key>NSDesktopFolderUsageDescription</key><string>Konspekt может сохранять конспекты на рабочий стол.</string>
<key>NSHumanReadableCopyright</key><string>DrTonix · bdub.space</string>
</dict></plist>
PLIST

say "готово: $(du -sh "$APP" | cut -f1)  ->  $APP"
