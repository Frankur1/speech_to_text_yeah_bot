# ==== 1. Базовый образ ====
FROM python:3.11-slim

# ==== 2. Устанавливаем системные зависимости ====
# ffmpeg нужен для извлечения аудио из видео
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# ==== 3. Создаём рабочую директорию ====
WORKDIR /app

# ==== 4. Копируем зависимости ====
COPY requirements.txt .

# ==== 5. Устанавливаем зависимости ====
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==== 6. Копируем всё остальное ====
COPY . .

# ==== 7. Настройки среды ====
ENV PYTHONUNBUFFERED=1

# ==== 8. Команда запуска ====
CMD ["python", "speech_to_text_yeah.py"]
