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
# Сначала обновляем pip, потом ставим зависимости из requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==== 6. Переменные окружения ====
# Railway сам подставит их из Settings → Variables
ENV PYTHONUNBUFFERED=1

# ==== 7. Команда запуска ====
CMD ["python", "speech_to_text_yeah.py"]
