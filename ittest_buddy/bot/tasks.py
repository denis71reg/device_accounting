"""
Задачи Celery для бота: рассылки, онбординг и т.д.
"""
import asyncio
import logging
from datetime import datetime, time as dt_time
from django.utils import timezone
from celery import shared_task
from django.conf import settings
from aiogram import Bot
from aiogram.types import InlineKeyboardBuilder
from aiogram.enums import ParseMode
from core.models import User, BotMessage, UserStatus, Location

logger = logging.getLogger(__name__)


@shared_task
def send_day_one_onboarding():
    """
    Ежедневная задача (09:00 утра) - отправка инструкций в День 1
    Проверяет пользователей с start_date = сегодня и статусом ready_to_start
    """
    today = timezone.now().date()
    users_to_onboard = User.objects.filter(
        start_date=today,
        status=UserStatus.READY_TO_START,
        telegram_id__isnull=False
    )
    
    if not users_to_onboard.exists():
        logger.info(f"No users to onboard today ({today})")
        return
    
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return
    
    async def send_onboarding_messages():
        bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)
        
        for user in users_to_onboard:
            try:
                # Меняем статус на active
                user.status = UserStatus.ACTIVE
                user.save(update_fields=['status'])
                
                # Собираем пакет инструкций
                messages = []
                
                # 1. VPN инструкция
                vpn_msg = get_bot_message('vpn_instruction',
                    "🔐 <b>VPN</b>\n\n"
                    "Для подключения к VPN используй бота: @outline_ittest_bot"
                )
                messages.append(vpn_msg)
                
                # 2. Почта/Подпись
                email_msg = get_bot_message('email_instruction',
                    "📧 <b>Почта и Подпись</b>\n\n"
                    "Проверь свою корпоративную почту и настрой подпись согласно стандартам компании."
                )
                messages.append(email_msg)
                
                # 3. Блок "Обед" (Smart Lunch Logic)
                lunch_msg = get_lunch_message(user.location)
                if lunch_msg:
                    messages.append(lunch_msg)
                
                # Отправляем все сообщения
                for msg in messages:
                    await bot.send_message(chat_id=user.telegram_id, text=msg)
                    # Небольшая задержка между сообщениями
                    await asyncio.sleep(0.5)
                
                logger.info(f"Onboarding sent to {user.full_name} (ID: {user.telegram_id})")
                
            except Exception as e:
                logger.error(f"Error sending onboarding to {user.full_name}: {e}")
        
        await bot.session.close()
    
    # Запускаем асинхронную отправку
    asyncio.run(send_onboarding_messages())


def get_bot_message(slug: str, default: str = "") -> str:
    """Получить текст сообщения из БД по slug"""
    try:
        message = BotMessage.objects.get(slug=slug)
        return message.text
    except BotMessage.DoesNotExist:
        logger.warning(f"BotMessage with slug '{slug}' not found, using default")
        return default


def get_lunch_message(location: str) -> str:
    """
    Smart Lunch Logic - возвращает сообщение об обеде в зависимости от локации и времени
    """
    now = timezone.now()
    current_time = now.time()
    
    if location == Location.TULA:
        # Тула: до 12:00 - запись на завтра, после - закрыто
        if current_time < dt_time(12, 0):
            return get_bot_message('lunch_tula_tomorrow',
                "🍽 <b>Обед (Тула)</b>\n\n"
                "Запишись на завтра в боте: @ittest_tula_dinner_bot"
            )
        else:
            return get_bot_message('lunch_tula_closed',
                "🍽 <b>Обед (Тула)</b>\n\n"
                "На завтра запись закрыта. Сохрани бота на будущее: @ittest_tula_dinner_bot"
            )
    
    elif location == Location.SPB:
        # СПб: до 14:30 - запись на сегодня, после - опоздал
        if current_time < dt_time(14, 30):
            return get_bot_message('lunch_spb_today',
                "🍽 <b>Обед (СПб)</b>\n\n"
                "Запишись на сегодня в боте: @ittest_spb_dinner_bot"
            )
        else:
            return get_bot_message('lunch_spb_closed',
                "🍽 <b>Обед (СПб)</b>\n\n"
                "На сегодня опоздал. Сохрани бота на будущее: @ittest_spb_dinner_bot"
            )
    
    elif location == Location.REMOTE:
        # Удаленка - блок пропускается
        return None
    
    return None

