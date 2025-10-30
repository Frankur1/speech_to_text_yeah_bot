# ==== 1. Базовый образ ====
FROM python:3.11-slim

# ==== 2. Устанавливаем системные зависимости ====
# ffmpeg нужен для извлечения аудио из видео
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# ==== 3. Создаём рабочую директорию ====
WORKDIR /app

# ==== 4. Копируем файлы проекта ====
COPY . .

# ==== 5. Устанавливаем зависимости ====
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir aiogram openai ffmpeg-python
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

# ==== 6. Переменные окружения ====
# Чтобы Railway мог передавать ключи и токен
ENV PYTHONUNBUFFERED=1
ENV BOT_TOKEN=${BOT_TOKEN}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# ==== 7. Команда запуска ====
CMD ["python", "speech_to_text_yeah.py"]
