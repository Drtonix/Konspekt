#!/bin/zsh
# Веса разделения голосов: 97 МБ, в репозитории им не место.
# Запускается сборкой сама; отдельно нужна только для запуска из исходников.
set -e
cd "${0:A:h}"
mkdir -p models

get() {  # имя  тег-релиза  ожидаемый размер
    if [ -f "models/$1" ] && [ "$(stat -f%z "models/$1")" = "$3" ]; then
        return
    fi
    print -P "%F{green}==>%f качаю $1"
    curl -fL --progress-bar \
        "https://github.com/k2-fsa/sherpa-onnx/releases/download/$2/$1" \
        -o "models/$1"
}

get silero_vad.onnx              asr-models                    643854
get nemo_en_titanet_large.onnx   speaker-recongition-models    101405493
