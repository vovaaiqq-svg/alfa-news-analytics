#!/bin/bash
# Запуск «в один клик»: окружение -> зависимости -> сервер -> публичная ссылка.
# Использование:
#   ./start.sh            # порт 8000
#   PORT=8080 ./start.sh  # другой порт

set -u
cd "$(dirname "$0")" || exit 1

PORT="${PORT:-8000}"
RUN_DIR=".run"
mkdir -p "$RUN_DIR"

echo "=============================================="
echo "  Альфа Хак — Новостная аналитика"
echo "  Запуск сервиса и публичной ссылки"
echo "=============================================="

# ---------- 1. Python ----------
if ! command -v python3 >/dev/null 2>&1; then
    echo "ОШИБКА: Python 3 не найден."
    echo "Установите Python 3.10+ (Linux: sudo apt install python3 python3-venv python3-pip)."
    exit 1
fi
echo "[1/4] Python: $(python3 --version)"

# ---------- 2. Виртуальное окружение ----------
PYTHON="python3"
if [ -x ".venv/bin/python" ]; then
    echo "[2/4] Использую готовое окружение .venv"
else
    echo "[2/4] Создаю виртуальное окружение .venv..."
    if python3 -m venv .venv 2>/dev/null; then
        echo "      Готово."
    else
        echo "      Не удалось создать venv (нет пакета python3-venv)."
        echo "      Ставлю зависимости в пользовательское окружение."
        rm -rf .venv
    fi
fi
if [ -x ".venv/bin/python" ]; then
    PYTHON="$PWD/.venv/bin/python"
fi

# ---------- 3. Зависимости ----------
echo "[3/4] Проверяю зависимости (requirements-lite.txt)..."
if "$PYTHON" -c "import fastapi, uvicorn, feedparser, bs4, lxml, numpy" 2>/dev/null; then
    echo "      Всё уже установлено."
else
    echo "      Устанавливаю (один раз, ~1 минута)..."
    if ! "$PYTHON" -m pip install -q -r requirements-lite.txt; then
        echo "ОШИБКА: не удалось установить зависимости."
        echo "Проверьте интернет и выполните вручную:"
        echo "  $PYTHON -m pip install -r requirements-lite.txt"
        exit 1
    fi
fi

# ---------- 4. Сервер ----------
echo "[4/4] Запускаю сервер на порту ${PORT}..."
if curl -s -m 3 "http://localhost:${PORT}/api/health" | grep -q '"status":"healthy"'; then
    echo "      Сервер уже работает — использую его."
else
    nohup "$PYTHON" -m uvicorn api.main:app --host 0.0.0.0 --port "$PORT" \
        > "$RUN_DIR/server.log" 2>&1 &
    echo $! > "$RUN_DIR/server.pid"

    ready=0
    for i in $(seq 1 40); do
        if curl -s -m 2 "http://localhost:${PORT}/api/health" | grep -q '"status":"healthy"'; then
            ready=1
            break
        fi
        sleep 1
    done
    if [ "$ready" != "1" ]; then
        echo "ОШИБКА: сервер не поднялся. Последние строки лога:"
        tail -20 "$RUN_DIR/server.log"
        exit 1
    fi
    echo "      Сервер готов: http://localhost:${PORT}/app"
fi

# ---------- Публичная ссылка ----------
echo ""
echo "Поднимаю публичный туннель (это может занять до 1–2 минут)..."
chmod +x share.sh
if ! ./share.sh "$PORT"; then
    echo ""
    echo "Не удалось открыть публичную ссылку, но локально всё работает:"
    echo "  http://localhost:${PORT}/app"
    exit 1
fi

URL=$(cat PUBLIC_URL.txt 2>/dev/null)
echo ""
echo "=============================================="
echo "  ГОТОВО. Открой эту ссылку в браузере:"
echo ""
echo "      ${URL}/app"
echo ""
echo "  Локально:  http://localhost:${PORT}/app"
echo "  Остановить: ./stop.sh"
echo "=============================================="
