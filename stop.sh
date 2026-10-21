#!/bin/bash
# Останавливает сервер и туннель, запущенные через ./start.sh

cd "$(dirname "$0")" || exit 1
RUN_DIR=".run"

stopped=0
for name in tunnel server; do
    pidfile="$RUN_DIR/$name.pid"
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "Остановлен $name (PID $pid)"
            stopped=1
        fi
        rm -f "$pidfile"
    fi
done

rm -f PUBLIC_URL.txt

if [ "$stopped" = "0" ]; then
    echo "Запущенных через start.sh процессов не найдено."
fi
