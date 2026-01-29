import asyncio

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Запускает Telegram бота"

    def handle(self, *args, **options):
        # Импортируем после того, как Django инициализирован через BaseCommand
        from resume_roaster.bot.bot import main

        self.stdout.write(self.style.SUCCESS("Starting Telegram bot..."))
        asyncio.run(main())

