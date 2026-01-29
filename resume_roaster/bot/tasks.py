import logging
from io import BytesIO

import httpx
from celery import shared_task
from django.conf import settings
from PyPDF2 import PdfReader

from .models import ResumeProcessing

logger = logging.getLogger(__name__)


def extract_text_from_pdf(data: bytes) -> str:
    """Извлекает текст из PDF файла"""
    reader = PdfReader(BytesIO(data))
    texts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        texts.append(text)
    return "\n\n".join(texts).strip()


def roast_resume_with_llm(resume_text: str) -> str:
    """Отправляет запрос в OpenRouter для прожарки резюме (синхронная версия для Celery)"""
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    url = f"{settings.OPENROUTER_API_BASE.rstrip('/')}/chat/completions"
    model = "gpt-4o-mini"

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-org/resume-roaster-bot",
                "X-Title": "Resume Roaster Bot",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Ты опытный карьерный консультант и HR."},
                    {"role": "user", "content": settings.ROAST_PROMPT + "\n\n" + resume_text},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


@shared_task
def process_resume_task(processing_id: int, resume_text: str) -> None:
    """
    Celery задача для обработки резюме.
    Извлекает текст (если нужно), отправляет в LLM и сохраняет результат.
    """
    try:
        processing = ResumeProcessing.objects.get(id=processing_id)
        processing.status = ResumeProcessing.STATUS_PROCESSING
        processing.save()

        roast_result = roast_resume_with_llm(resume_text)

        processing.roast_result = roast_result
        processing.status = ResumeProcessing.STATUS_COMPLETED
        processing.save()

        # Отправляем результат в Telegram через другую задачу
        send_roast_result_task.delay(processing_id)

    except Exception as e:
        logger.exception(f"Error processing resume {processing_id}")
        processing = ResumeProcessing.objects.get(id=processing_id)
        processing.status = ResumeProcessing.STATUS_FAILED
        processing.error_message = str(e)
        processing.save()
        send_error_message_task.delay(processing_id, str(e))


@shared_task
def process_pdf_task(processing_id: int, pdf_data: bytes) -> None:
    """
    Celery задача для обработки PDF файла.
    Извлекает текст и запускает прожарку.
    """
    try:
        processing = ResumeProcessing.objects.get(id=processing_id)
        processing.status = ResumeProcessing.STATUS_PROCESSING
        processing.save()

        resume_text = extract_text_from_pdf(pdf_data)
        if not resume_text:
            processing.status = ResumeProcessing.STATUS_FAILED
            processing.error_message = "Не удалось извлечь текст из PDF"
            processing.save()
            send_error_message_task.delay(processing_id, "Не удалось извлечь текст из PDF. Проверь, что в файле есть текст (а не просто скан).")
            return

        processing.resume_text = resume_text
        processing.save()

        # Запускаем прожарку
        process_resume_task.delay(processing_id, resume_text)

    except Exception as e:
        logger.exception(f"Error processing PDF {processing_id}")
        processing = ResumeProcessing.objects.get(id=processing_id)
        processing.status = ResumeProcessing.STATUS_FAILED
        processing.error_message = str(e)
        processing.save()
        send_error_message_task.delay(processing_id, str(e))


@shared_task
def send_roast_result_task(processing_id: int) -> None:
    """Отправляет результат прожарки пользователю в Telegram"""
    from aiogram import Bot
    from aiogram.types import BufferedInputFile

    try:
        # Получаем данные из БД синхронно ДО запуска async контекста
        processing = ResumeProcessing.objects.get(id=processing_id)
        if not processing.roast_result:
            return

        # Сохраняем нужные значения в переменные
        chat_id = processing.telegram_chat_id
        roast = processing.roast_result

        # Теперь запускаем async код (без доступа к Django ORM внутри)
        import asyncio

        async def send_message():
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            try:
                if len(roast) > 3500:
                    data = roast.encode("utf-8")
                    await bot.send_document(
                        chat_id,
                        BufferedInputFile(data, filename="roast.txt"),
                        caption="Твоя прожарка готова 🔥",
                    )
                else:
                    await bot.send_message(chat_id, roast)
            finally:
                await bot.session.close()

        asyncio.run(send_message())

    except Exception as e:
        logger.exception(f"Error sending roast result {processing_id}")
        send_error_message_task.delay(processing_id, f"Ошибка при отправке результата: {e}")


@shared_task
def send_error_message_task(processing_id: int, error_message: str) -> None:
    """Отправляет сообщение об ошибке пользователю в Telegram"""
    from aiogram import Bot

    try:
        # Получаем данные из БД синхронно ДО запуска async контекста
        processing = ResumeProcessing.objects.get(id=processing_id)
        chat_id = processing.telegram_chat_id

        # Теперь запускаем async код (без доступа к Django ORM внутри)
        import asyncio

        async def send_error():
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            try:
                await bot.send_message(chat_id, f"Произошла ошибка: {error_message}")
            finally:
                await bot.session.close()

        asyncio.run(send_error())

    except Exception as e:
        logger.exception(f"Error sending error message {processing_id}")

