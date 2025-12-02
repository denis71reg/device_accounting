"""
Management команда для запуска Telegram бота
"""
from django.core.management.base import BaseCommand
import asyncio
import logging
from bot.bot import main as bot_main

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Запустить Telegram бота'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Telegram bot...'))
        try:
            asyncio.run(bot_main())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Bot stopped by user'))
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            self.stdout.write(self.style.ERROR(f'Error: {e}'))







