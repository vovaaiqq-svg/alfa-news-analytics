#!/bin/bash

# Сторож туннеля: следит за публичной ссылкой и перезапускает туннель,
# если он перестал отвечать. Текущий адрес всегда лежит в URL_FILE.
#
#   ./keepalive.sh          # запустить в фоне (nohup)
#   ./keepalive.sh stop     # остановить

PORT="${PORT:-8000}"
BIN="/tmp/opencode/bin/cloudflared"
LOG="/tmp/opencode/cloudflared.log"
KEEP_LOG="/tmp/opencode/keepalive.log"
PID_FILE="/tmp/opencode/keepalive.pid"
URL_FILE="/tmp/opencode/cf_url.txt"
CHECK_URL="${CHECK_URL:-}"

if [ "$1" = "stop" ]; then
    [ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null
    rm -f "$PID_FILE"
    echo "Watchdog остановлен."
    exit 0
fi

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Watchdog уже запущен (PID $(cat "$PID_FILE"))"
    exit 0
fi

if [ ! -x "$BIN" ]; then
    mkdir -p "$(dirname "$BIN")"
    curl -sL -o "$BIN" https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
    chmod +x "$BIN"
fi

if ! curl -s -m 3 "http://localhost:${PORT}/api/health" > /dev/null; then
    echo "Сервер на порту ${PORT} не отвечает. Сначала запустите uvicorn."
    exit 1
fi

echo "$$" > "$PID_FILE"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$KEEP_LOG"
}

start_tunnel() {
    pkill -f "^$BIN tunnel" 2>/dev/null
    sleep 2
    : > "$LOG"
    nohup "$BIN" tunnel --url "http://localhost:${PORT}" --no-autoupdate >> "$LOG" 2>&1 &
    log "Запущен cloudflared (PID $!)"

    local url=""
    for i in $(seq 1 30); do
        # Адрес берём из баннера "Your quick Tunnel has been created",
        # чтобы не поймать служебный api.trycloudflare.com
        url=$(grep -A2 "quick Tunnel has been created" "$LOG" \
            | grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" | head -1)
        if [ -z "$url" ]; then
            url=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$LOG" \
                | grep -vE '^https://(api|update|region[0-9]+|cert|hundred)\.' | head -1)
        fi
        [ -n "$url" ] && break
        sleep 1
    done
    if [ -z "$url" ]; then
        log "Не удалось получить адрес туннеля"
        return 1
    fi

    # Ждём активации edge и проверяем, что ссылка действительно работает
    for i in $(seq 1 12); do
        sleep 5
        if curl -s -m 15 -o /dev/null -w "%{http_code}" "${url}/api/health" | grep -q "^200$"; then
            echo "$url" > "$URL_FILE"
            echo "$url" > "$(dirname "$0")/PUBLIC_URL.txt"
            log "Туннель поднят: $url"
            echo "$url"
            return 0
        fi
    done

    log "Туннель не отвечает после запуска: $url"
    return 1
}

URL=""
FAILS=0
if [ -n "$CHECK_URL" ]; then
    URL="$CHECK_URL"
fi

log "Watchdog запущен (PID $$), порт ${PORT}"

while true; do
    if [ -z "$URL" ]; then
        URL=$(start_tunnel | tail -1)
    fi

    if [ -n "$URL" ]; then
        code=$(curl -s -m 20 -o /dev/null -w "%{http_code}" "${URL}/api/health")
        if [ "$code" != "200" ]; then
            FAILS=$((FAILS + 1))
            log "Ссылка не отвечает (HTTP ${code}), неудачных попыток подряд: ${FAILS}"
            if [ "$FAILS" -ge 2 ]; then
                log "Перезапускаю туннель"
                URL=""
                FAILS=0
            fi
            continue
        fi
        FAILS=0
    fi

    sleep 30
done
