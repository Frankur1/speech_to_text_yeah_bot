import os
import asyncio
import ffmpeg
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from openai import OpenAI
from dotenv import load_dotenv

# === Загружаем .env ===
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TEMP_DIR = "downloads"

os.makedirs(TEMP_DIR, exist_ok=True)

# === Настройка бота ===
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)


# === Извлекаем аудио из видео ===
async def extract_audio(video_path: str, output_path: str):
    stream = ffmpeg.input(video_path)
    stream = ffmpeg.output(stream, output_path, ac=1, ar=16000)
    ffmpeg.run(stream, overwrite_output=True, quiet=True)
    return output_path


# === Распознаём речь через OpenAI ===
def transcribe_audio(audio_path: str) -> str:
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcription


# === Обработчик команды /start ===
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "🎥 <b>Привет!</b>\n\n"
        "Отправь мне видео, аудио или голосовое — и я превращу речь в текст ✨"
    )


# === Обработчик медиа ===
@dp.message(lambda m: m.video or m.audio or m.voice or m.video_note or (m.document and m.document.mime_type and m.document.mime_type.startswith("video")))
async def handle_media(message: types.Message):
    await message.answer("🎧 Обрабатываю файл... это может занять немного времени ⏳")

    try:
        file = message.video or message.audio or message.voice or message.video_note or message.document
        file_info = await bot.get_file(file.file_id)
        file_path = f"{TEMP_DIR}/{file.file_unique_id}"
        await bot.download_file(file_info.file_path, file_path)

        audio_path = f"{file_path}.wav"
        await extract_audio(file_path, audio_path)

        text = await asyncio.to_thread(transcribe_audio, audio_path)

        if text.strip():
            await message.answer(f"📝 <b>Распознанный текст:</b>\n\n{text}")
        else:
            await message.answer("⚠️ Не удалось распознать речь в этом файле.")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: <code>{e}</code>")
    finally:
        for f in [file_path, audio_path]:
            if os.path.exists(f):
                os.remove(f)


# === Запуск ===
async def main():
    print("✅ Бот запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
