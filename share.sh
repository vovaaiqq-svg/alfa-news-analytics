#!/bin/bash

# Публикация сервиса в интернете через временный туннель.
# Требуется, чтобы сервер уже был запущен на порту 8000.
#
# Использование:
#   ./share.sh            # авто: cloudflared, затем pinggy, затем localhost.run
#   ./share.sh 8000       # другой порт
#   TUNNEL=pinggy ./share.sh
#   TUNNEL=cloudflared ./share.sh
#   TUNNEL=localhostrun ./share.sh

PORT="${1:-8000}"
TUNNEL="${TUNNEL:-auto}"

if ! curl -s -m 3 "http://localhost:${PORT}/api/health" > /dev/null; then
    echo "Сервер на порту ${PORT} не отвечает. Сначала запустите:"
    echo "  python3 -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"
    exit 1
fi

health_ok() {
    local url="$1"
    for i in $(seq 1 6); do
        if curl -s -m 10 -o /dev/null -w "%{http_code}" "${url}/api/health" | grep -q "^200$"; then
            return 0
        fi
        sleep 5
    done
    return 1
}

start_cloudflared() {
    local bin="/tmp/opencode/bin/cloudflared"
    local log="/tmp/opencode/cloudflared.log"

    if [ ! -x "$bin" ]; then
        echo "Скачиваю cloudflared..."
        mkdir -p "$(dirname "$bin")"
        curl -sL -o "$bin" https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
        chmod +x "$bin"
    fi

    nohup "$bin" tunnel --url "http://localhost:${PORT}" --no-autoupdate > "$log" 2>&1 &
    local pid=$!

    local url=""
    for i in $(seq 1 25); do
        url=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$log" | head -1)
        [ -n "$url" ] && break
        sleep 1
    done
    [ -z "$url" ] && { kill "$pid" 2>/dev/null; return 1; }

    echo "Проверяю туннель Cloudflare..."
    if health_ok "$url"; then
        echo "cloudflared|$pid|$url|$log"
        return 0
    fi
    kill "$pid" 2>/dev/null
    return 1
}

start_pinggy() {
    local log="/tmp/opencode/pinggy.log"

    if [ ! -f "$HOME/.ssh/id_ed25519" ]; then
        echo "Генерирую SSH-ключ для pinggy..."
        ssh-keygen -t ed25519 -N "" -f "$HOME/.ssh/id_ed25519" -q
    fi

    nohup ssh -T -p 443 \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ServerAliveInterval=20 -o ExitOnForwardFailure=yes \
        -R0:"localhost:${PORT}" a.pinggy.io > "$log" 2>&1 &
    local pid=$!

    local url=""
    for i in $(seq 1 20); do
        url=$(grep -oE "https://[a-z0-9-]+\.(run\.pinggy-free\.link|free\.pinggy\.net)" "$log" | tail -1)
        [ -n "$url" ] && break
        sleep 1
    done
    [ -z "$url" ] && { kill "$pid" 2>/dev/null; return 1; }

    echo "Проверяю туннель Pinggy..."
    if health_ok "$url"; then
        echo "pinggy|$pid|$url|$log"
        return 0
    fi
    kill "$pid" 2>/dev/null
    return 1
}

start_localhostrun() {
    local log="/tmp/opencode/localhostrun.log"

    nohup ssh -T \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ServerAliveInterval=20 -o ExitOnForwardFailure=yes \
        -R 80:"localhost:${PORT}" nokey@localhost.run > "$log" 2>&1 &
    local pid=$!

    local url=""
    for i in $(seq 1 20); do
        url=$(grep -oE "https://[a-z0-9]+\.lhr\.life" "$log" | head -1)
        [ -n "$url" ] && break
        sleep 1
    done
    [ -z "$url" ] && { kill "$pid" 2>/dev/null; return 1; }

    echo "Проверяю туннель localhost.run..."
    if health_ok "$url"; then
        echo "localhost.run|$pid|$url|$log"
        return 0
    fi
    kill "$pid" 2>/dev/null
    return 1
}

RESULT=""
case "$TUNNEL" in
    cloudflared) RESULT=$(start_cloudflared) ;;
    pinggy)      RESULT=$(start_pinggy) ;;
    localhostrun) RESULT=$(start_localhostrun) ;;
    auto)
        RESULT=$(start_cloudflared) || RESULT=$(start_pinggy) || RESULT=$(start_localhostrun)
        ;;
    *)
        echo "Неизвестный TUNNEL=$TUNNEL (cloudflared|pinggy|localhostrun|auto)"
        exit 1
        ;;
esac

if [ -z "$RESULT" ]; then
    echo "Не удалось поднять публичный туннель. Смотрите логи в /tmp/opencode/."
    exit 1
fi

PROVIDER=$(echo "$RESULT" | cut -d'|' -f1)
PID=$(echo "$RESULT" | cut -d'|' -f2)
URL=$(echo "$RESULT" | cut -d'|' -f3)
LOG=$(echo "$RESULT" | cut -d'|' -f4)

echo ""
echo "=============================================="
echo "  Провайдер:         $PROVIDER"
echo "  Публичная ссылка:  $URL"
echo "  Веб-интерфейс:     $URL/app"
echo "  API health:        $URL/api/health"
echo "=============================================="
echo ""
if [ "$PROVIDER" = "pinggy" ]; then
    echo "Pinggy показывает браузеру страницу-предупреждение — нажмите «Continue»."
    echo "Бесплатный туннель Pinggy живёт 60 минут, затем перезапустите ./share.sh."
fi
echo "Туннель работает, пока запущен процесс (PID $PID)."
echo "Остановить:  kill $PID"
echo "Лог:         $LOG"
