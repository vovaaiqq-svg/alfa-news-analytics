FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание директорий для данных
RUN mkdir -p data/client_profiles data/news data/alfa_analytics

# Экспорт порта
EXPOSE 8000

# Запуск приложения
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
