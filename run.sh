#!/bin/bash

# Скрипт запуска сервиса новостной аналитики

echo "Запуск сервиса Альфа Хак - Новостная аналитика..."
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "Ошибка: Python 3 не установлен"
    exit 1
fi

# Установка зависимостей если необходимо
if [ ! -d ".venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-lite.txt
else
    source .venv/bin/activate
fi

# Запуск сервера
echo "Запуск сервера на http://localhost:8000"
echo "Веб-интерфейс: http://localhost:8000/app"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo ""

python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
