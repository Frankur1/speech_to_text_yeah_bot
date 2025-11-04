import os
import asyncio
import mimetypes
import requests
import ffmpeg
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import OpenAI
from dotenv import load_dotenv

# === Загружаем .env ===
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TEMP_DIR = "downloads"

os.makedirs(TEMP_DIR, exist_ok=True)

# === Настройка бота ===
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)

# === Извлечение аудио ===
async def extract_audio(input_path: str, output_path: str):
    """Извлекает аудио из любого файла (видео, аудио, документ)"""
    try:
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.output(stream, output_path, ac=1, ar=16000)
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
    except ffmpeg.Error as e:
        raise Exception(f"FFmpeg error: {e}")
    return output_path

# === Распознавание речи ===
def transcribe_audio(audio_path: str) -> str:
    """Распознаёт речь через OpenAI Whisper"""
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcription

# === GPT форматирование ===
async def beautify_text(raw_text: str) -> str:
    prompt = f"""
Ты профессиональный редактор.
Отформатируй и структурируй следующий текст речи:
---
{raw_text}
---
Требования:
1. Добавь заголовок, если уместно.
2. Разбей на абзацы.
3. Поставь правильные знаки препинания.
4. Удали шумовые слова.
5. Сохрани естественность речи.
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# === GPT перевод ===
async def translate_text(text: str, lang: str) -> str:
    lang_name = {"en": "английский", "ru": "русский", "hy": "армянский"}.get(lang, lang)
    prompt = f"Переведи этот текст на {lang_name} язык, сохранив стиль и форматирование:\n\n{text}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# === Команда /start ===
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "🎥 <b>Привет!</b>\n\n"
        "Я принимаю любые видео 🎬, аудио 🔊 или ссылку 📎 (например WB Disk, Google Drive, Dropbox) — "
        "и превращаю речь в структурированный текст ✨"
    )

# === Универсальный обработчик ===
@dp.message()
async def handle_any_file(message: types.Message):
    # === 1. Если прислали ссылку ===
    if message.text and message.text.startswith(("http://", "https://")):
        await message.answer("📥 Скачиваю файл по ссылке...")
        try:
            url = message.text.strip()
            local_path = f"{TEMP_DIR}/remote_file"

            # --- Скачивание файла ---
            response = requests.get(url, stream=True, timeout=600)
            total = 0
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
                        if total > 1024 * 1024 * 500:  # 500 MB лимит
                            raise Exception("Файл слишком большой (>500 MB).")
            await process_file(message, local_path)
            return
        except Exception as e:
            await message.answer(f"❌ Не удалось скачать файл по ссылке:\n<code>{e}</code>")
            return

    # === 2. Если файл отправлен через Telegram ===
    file = message.video or message.audio or message.voice or message.video_note or message.document
    if not file:
        await message.answer("📂 Отправь видео, аудио, документ или ссылку на файл.")
        return

    await message.answer("🎧 Обрабатываю файл, подожди немного ⏳")

    try:
        file_info = await bot.get_file(file.file_id)
        file_name = getattr(file, "file_name", f"{file.file_unique_id}")
        input_path = f"{TEMP_DIR}/{file_name}"
        await bot.download_file(file_info.file_path, input_path)
        await process_file(message, input_path)
    except Exception as e:
        await message.answer(f"❌ Ошибка при скачивании через Telegram:\n<code>{e}</code>")

# === Основная обработка файла ===
async def process_file(message: types.Message, input_path: str):
    """Общий процесс: аудио/видео → текст → форматирование"""
    try:
        mime, _ = mimetypes.guess_type(input_path)
        output_path = f"{input_path}.wav"

        if mime and mime.startswith("audio"):
            os.rename(input_path, output_path)
        else:
            await extract_audio(input_path, output_path)

        raw_text = await asyncio.to_thread(transcribe_audio, output_path)
        formatted_text = await beautify_text(raw_text)

        kb = InlineKeyboardBuilder()
        kb.button(text="🇷🇺 Русский", callback_data="translate_ru")
        kb.button(text="🇺🇸 English", callback_data="translate_en")
        kb.button(text="🇦🇲 Հայերեն", callback_data="translate_hy")

        await message.answer(
            f"📝 <b>Структурированный текст:</b>\n\n{formatted_text}",
            reply_markup=kb.as_markup()
        )

        dp.workflow_data["last_text"] = formatted_text

    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке файла:\n<code>{e}</code>")
    finally:
        for f in [input_path, f"{input_path}.wav"]:
            if os.path.exists(f):
                os.remove(f)

# === Обработка перевода ===
@dp.callback_query(lambda c: c.data.startswith("translate_"))
async def translate_callback(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    text = dp.workflow_data.get("last_text", "")
    if not text:
        await callback.answer("Текст не найден, попробуй отправить файл заново.")
        return
    translated = await translate_text(text, lang)
    await callback.message.answer(f"🌍 <b>Перевод:</b>\n\n{translated}")

# === Запуск ===
async def main():
    print("✅ Бот запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
