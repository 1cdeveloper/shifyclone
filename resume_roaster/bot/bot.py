import logging
import os

import django
from asgiref.sync import sync_to_async

# Инициализируем Django ДО импорта моделей
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resume_roaster.settings")
django.setup()

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile
from django.conf import settings

from .models import ResumeProcessing
from .tasks import process_pdf_task, process_resume_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Вспомогательные функции для работы с Django ORM в async контексте
async def create_resume_processing(**kwargs):
    """Создаёт запись ResumeProcessing в БД (async-safe)"""
    return await sync_to_async(ResumeProcessing.objects.create)(**kwargs)

dp = Dispatcher()
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "Привет я на вайбкодил хуйни\n\n"
        "Отправь мне PDF-файл с резюме — я его прочитаю и жестко, но по делу разберу.\n\n"
        "Либо просто вставь текст резюме сообщением — я тоже прожарю.\n"
    )
    await message.answer(text)


@dp.message(F.document)
async def handle_document(message: Message) -> None:
    document = message.document
    if not document:
        return

    if not (document.mime_type == "application/pdf" or (document.file_name or "").lower().endswith(".pdf")):
        await message.answer("Пожалуйста, пришли именно PDF-файл с резюме.")
        return

    if not message.from_user:
        await message.answer("Не удалось определить пользователя.")
        return

    await message.answer("Получил файл, читаю резюме и готовлю прожарку... 🔥")

    try:
        file = await bot.get_file(document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        pdf_data = file_bytes.read()

        # Создаём запись в БД (async-safe)
        processing = await create_resume_processing(
            telegram_user_id=message.from_user.id,
            telegram_chat_id=message.chat.id,
            telegram_message_id=message.message_id,
            file_id=document.file_id,
            resume_text="",  # Будет заполнено после извлечения текста
            status=ResumeProcessing.STATUS_PENDING,
        )

        # Отправляем задачу в Celery для обработки PDF
        process_pdf_task.delay(processing.id, pdf_data)

    except Exception as e:
        logger.exception("Error while processing PDF")
        await message.answer(f"Произошла ошибка при обработке файла: {e}")


@dp.message(F.text)
async def handle_text(message: Message) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    # Не прожариваем команды
    if text.startswith("/"):
        return

    if not message.from_user:
        await message.answer("Не удалось определить пользователя.")
        return

    await message.answer("Принял текст. Готовлю прожарку... 🔥")

    try:
        # Создаём запись в БД (async-safe)
        processing = await create_resume_processing(
            telegram_user_id=message.from_user.id,
            telegram_chat_id=message.chat.id,
            telegram_message_id=message.message_id,
            resume_text=text,
            status=ResumeProcessing.STATUS_PENDING,
        )

        # Отправляем задачу в Celery для обработки текста
        process_resume_task.delay(processing.id, text)

    except Exception as e:
        logger.exception("Error while processing text")
        await message.answer(f"Произошла ошибка при обработке текста: {e}")


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

