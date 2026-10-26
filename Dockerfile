FROM python:3.11-slim

WORKDIR /app

# Зависимости без тяжёлых опциональных пакетов (torch/sentence-transformers).
# RAG автоматически использует поиск по ключевым словам, если модель не установлена.
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt

# Копирование кода
COPY . .

# Создание директорий для данных
RUN mkdir -p data/client_profiles data/news data/alfa_analytics

# Экспорт порта
EXPOSE 8000

# Запуск приложения
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
