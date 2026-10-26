#!/bin/bash

# Публикация сервиса в интернете через временный туннель.
# Требуется, чтобы сервер уже был запущен (обычно через ./start.sh).
#
# Использование:
#   ./share.sh            # авто: cloudflared, затем pinggy, затем localhost.run
#   ./share.sh 8000       # другой порт
#   TUNNEL=pinggy ./share.sh
#   TUNNEL=cloudflared ./share.sh
#   TUNNEL=localhostrun ./share.sh

PORT="${1:-8000}"
TUNNEL="${TUNNEL:-auto}"
RUN_DIR=".run"
mkdir -p "$RUN_DIR"

if ! curl -s -m 3 "http://localhost:${PORT}/api/health" > /dev/null; then
    echo "Сервер на порту ${PORT} не отвечает. Сначала запустите:"
    echo "  ./start.sh"
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

# Достаёт адрес quick-туннеля из баннера cloudflared,
# чтобы не поймать служебный api.trycloudflare.com.
extract_cf_url() {
    local log="$1"
    grep -A2 "quick Tunnel has been created" "$log" 2>/dev/null \
        | grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" | head -1
}

start_cloudflared() {
    local log="$RUN_DIR/cloudflared.log"

    if [ "$(uname -s)" != "Linux" ]; then
        echo "cloudflared: автоскачивание поддерживается только в Linux." >&2
        return 1
    fi

    local bin="${CLOUDFLARED_BIN:-}"
    if [ -z "$bin" ]; then
        bin=$(command -v cloudflared 2>/dev/null || true)
    fi
    if [ -z "$bin" ]; then
        bin="$RUN_DIR/bin/cloudflared"
        if [ ! -x "$bin" ]; then
            echo "Скачиваю cloudflared..." >&2
            mkdir -p "$(dirname "$bin")"
            case "$(uname -m)" in
                x86_64|amd64) cf_arch=amd64 ;;
                aarch64|arm64) cf_arch=arm64 ;;
                *) echo "Неизвестная архитектура: $(uname -m)"; return 1 ;;
            esac
            curl -fsSL -o "$bin" \
                "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${cf_arch}" \
                || { echo "Не удалось скачать cloudflared"; return 1; }
            chmod +x "$bin"
        fi
    fi

    nohup "$bin" tunnel --url "http://localhost:${PORT}" --no-autoupdate > "$log" 2>&1 &
    local pid=$!

    local url=""
    for i in $(seq 1 25); do
        url=$(extract_cf_url "$log")
        [ -n "$url" ] && break
        sleep 1
    done
    [ -z "$url" ] && { kill "$pid" 2>/dev/null; return 1; }

    echo "Проверяю туннель Cloudflare..." >&2
    if health_ok "$url"; then
        echo "cloudflared|$pid|$url|$log"
        return 0
    fi
    kill "$pid" 2>/dev/null
    return 1
}

start_pinggy() {
    local log="$RUN_DIR/pinggy.log"

    if [ ! -f "$HOME/.ssh/id_ed25519" ]; then
        echo "Генерирую SSH-ключ для pinggy..." >&2
        ssh-keygen -t ed25519 -N "" -f "$HOME/.ssh/id_ed25519" -q
    fi

    nohup ssh -T -p 443 \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ServerAliveInterval=20 -o ExitOnForwardFailure=yes \
        -R0:"localhost:${PORT}" a.pinggy.io > "$log" 2>&1 &
    local pid=$!

    local url=""
    for i in $(seq 1 20); do
        # Pinggy печатает два адреса; актуальный — run.pinggy-free.link,
        # free.pinggy.net оставлен как legacy и может не резолвиться.
        url=$(grep -oE "https://[a-z0-9-]+\.run\.pinggy-free\.link" "$log" | head -1)
        if [ -z "$url" ]; then
            url=$(grep -oE "https://[a-z0-9-]+\.free\.pinggy\.net" "$log" | head -1)
        fi
        [ -n "$url" ] && break
        sleep 1
    done
    [ -z "$url" ] && { kill "$pid" 2>/dev/null; return 1; }

    echo "Проверяю туннель Pinggy..." >&2
    if health_ok "$url"; then
        echo "pinggy|$pid|$url|$log"
        return 0
    fi
    kill "$pid" 2>/dev/null
    return 1
}

start_localhostrun() {
    local log="$RUN_DIR/localhostrun.log"

    nohup ssh -T \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ServerAliveInterval=20 -o ExitOnForwardFailure=yes \
        -R 80:"localhost:${PORT}" nokey@localhost.run > "$log" 2>&1 &
    local pid=$!

    local url=""
    for i in $(seq 1 20); do
        # localhost.run может переиздать домен при переподключении — берём последний.
        url=$(grep -oE "https://[a-z0-9]+\.lhr\.life" "$log" | tail -1)
        [ -n "$url" ] && break
        sleep 1
    done
    [ -z "$url" ] && { kill "$pid" 2>/dev/null; return 1; }

    echo "Проверяю туннель localhost.run..." >&2
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
    echo "Не удалось поднять публичный туннель. Смотрите логи в ${RUN_DIR}/."
    exit 1
fi

# На случай, если в перехваченный вывод попали служебные строки,
# оставляем только строку формата provider|pid|url|log.
RESULT=$(echo "$RESULT" | grep -E "^(cloudflared|pinggy|localhost\.run)\|" | tail -1)

PROVIDER=$(echo "$RESULT" | cut -d'|' -f1)
PID=$(echo "$RESULT" | cut -d'|' -f2)
URL=$(echo "$RESULT" | cut -d'|' -f3)
LOG=$(echo "$RESULT" | cut -d'|' -f4)

echo "$URL" > PUBLIC_URL.txt
echo "$PID" > "$RUN_DIR/tunnel.pid"

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
echo "Остановить:  ./stop.sh"
echo "Лог:         $LOG"
