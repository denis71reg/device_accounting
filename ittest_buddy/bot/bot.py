"""
Основной файл бота на Aiogram 3.x
"""
import os
import django
from django.conf import settings

# Настройка Django перед импортом моделей
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ittest_buddy.settings')
django.setup()

import asyncio
import logging
from datetime import datetime, time
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.enums import ParseMode

from core.models import User, Device, BotMessage, UserStatus, Location

logger = logging.getLogger(__name__)


class PreboardingStates(StatesGroup):
    waiting_for_documents = State()


def get_bot_message(slug: str, default: str = "") -> str:
    """Получить текст сообщения из БД по slug"""
    try:
        message = BotMessage.objects.get(slug=slug)
        return message.text
    except BotMessage.DoesNotExist:
        logger.warning(f"BotMessage with slug '{slug}' not found, using default")
        return default


async def get_or_create_user(telegram_id: int, username: str = None, full_name: str = None) -> Optional[User]:
    """Получить или создать пользователя по telegram_id"""
    try:
        user = User.objects.get(telegram_id=telegram_id)
        # Обновляем username если изменился
        if username and user.username != username:
            user.username = username
            user.save(update_fields=['username'])
        return user
    except User.DoesNotExist:
        logger.warning(f"User with telegram_id {telegram_id} not found")
        return None


async def handle_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    telegram_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()

    # Получаем аргументы команды
    command_args = None
    if message.text and len(message.text.split()) > 1:
        command_args = message.text.split()[1]

    # Проверка токена перепривязки
    if command_args and command_args.startswith('reinvite_'):
        token = command_args.replace('reinvite_', '')
        try:
            user_to_reinvite = User.objects.get(reinvite_token=token)
            user_to_reinvite.telegram_id = telegram_id
            user_to_reinvite.username = username
            user_to_reinvite.save(update_fields=['telegram_id', 'username'])
            
            await message.answer(
                f"✅ Аккаунт успешно перепривязан!\n"
                f"Добро пожаловать, {user_to_reinvite.full_name}!"
            )
            user = user_to_reinvite
            
            # Логика в зависимости от статуса после перепривязки
            if user.status == UserStatus.PRE_HIRE:
                await handle_preboarding(message, user, state)
            elif user.status == UserStatus.ACTIVE:
                await show_main_menu(message, user)
            elif user.status == UserStatus.READY_TO_START:
                await message.answer(
                    f"⏳ Ждем тебя {user.start_date.strftime('%d.%m.%Y') if user.start_date else 'скоро'}!\n"
                    f"Утром в этот день я пришлю инструкции."
                )
            return
        except User.DoesNotExist:
            await message.answer("❌ Токен перепривязки недействителен или истек.")
            return

    user = await get_or_create_user(telegram_id, username, full_name)

    if not user:
        await message.answer(
            "🚫 Доступ запрещен. Обратитесь к HR для получения доступа."
        )
        return

    # Логика в зависимости от статуса
    if user.status == UserStatus.PRE_HIRE:
        await handle_preboarding(message, user, state)
    elif user.status == UserStatus.ACTIVE:
        await show_main_menu(message, user)
    elif user.status == UserStatus.READY_TO_START:
        await message.answer(
            f"⏳ Ждем тебя {user.start_date.strftime('%d.%m.%Y') if user.start_date else 'скоро'}!\n"
            f"Утром в этот день я пришлю инструкции."
        )
    elif user.status == UserStatus.ALUMNI:
        await message.answer("👋 Вы уволены. Доступ к боту ограничен.")


async def handle_preboarding(message: Message, user: User, state: FSMContext):
    """Сценарий пребординга - сбор документов"""
    welcome_text = get_bot_message('welcome_msg', 
        "👋 Добро пожаловать в IT Test!\n\n"
        "Мы рады, что вы присоединяетесь к нашей команде."
    )
    
    docs_request = get_bot_message('docs_request',
        "📄 Пожалуйста, отправьте следующие документы:\n"
        "- Паспорт (первая страница + прописка)\n"
        "- ИНН\n"
        "- СНИЛС\n"
        "- Трудовая книжка (если есть)\n\n"
        "Вы можете отправить файлы фотографиями или документами."
    )

    await message.answer(welcome_text)
    await message.answer(docs_request)
    
    await state.set_state(PreboardingStates.waiting_for_documents)
    await state.update_data(user_id=user.id)


async def handle_documents(message: Message, state: FSMContext):
    """Обработка полученных документов"""
    data = await state.get_data()
    user_id = data.get('user_id')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        await message.answer("❌ Ошибка. Пожалуйста, начните с /start")
        await state.clear()
        return

    # Пересылаем файл в чат HR
    hr_chat_id = settings.TELEGRAM_HR_CHAT_ID
    if not hr_chat_id:
        logger.error("TELEGRAM_HR_CHAT_ID not configured")
        await message.answer("❌ Ошибка конфигурации. Сообщите HR.")
        return

    bot = message.bot
    try:
        if message.photo:
            # Отправляем фото с подписью
            file_id = message.photo[-1].file_id
            caption = f"📎 Документ от {user.full_name} (@{user.username})"
            await bot.send_photo(chat_id=hr_chat_id, photo=file_id, caption=caption)
        elif message.document:
            # Отправляем документ
            file_id = message.document.file_id
            caption = f"📎 Документ от {user.full_name} (@{user.username})"
            await bot.send_document(chat_id=hr_chat_id, document=file_id, caption=caption)
        
        await message.answer("✅ Получено")
        
        # Предлагаем кнопку "Я всё отправил"
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Я всё отправил", callback_data="docs_complete")
        await message.answer(
            "Нажмите кнопку, когда отправите все документы:",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"Error forwarding document: {e}")
        await message.answer("❌ Ошибка при отправке. Попробуйте еще раз.")


async def handle_docs_complete(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки 'Я всё отправил'"""
    data = await state.get_data()
    user_id = data.get('user_id')
    
    try:
        user = User.objects.get(id=user_id)
        user.status = UserStatus.READY_TO_START
        user.save(update_fields=['status'])
        
        start_date_text = user.start_date.strftime('%d.%m.%Y') if user.start_date else "скоро"
        
        await callback.message.answer(
            f"✅ Спасибо! Документы получены.\n\n"
            f"⏳ Ждем тебя {start_date_text}!\n"
            f"Утром в этот день я пришлю инструкции."
        )
        await callback.answer()
        await state.clear()
    except User.DoesNotExist:
        await callback.answer("❌ Ошибка. Попробуйте снова.")
        await state.clear()


async def show_main_menu(message: Message, user: User):
    """Главное меню активного сотрудника"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Мое оборудование")
    builder.button(text="ℹ️ Инфо / Контакты")
    builder.adjust(1)
    
    await message.answer(
        f"👋 Добро пожаловать, {user.full_name}!\n\n"
        f"Выберите действие:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )


async def handle_my_devices(message: Message):
    """Показать оборудование сотрудника"""
    telegram_id = message.from_user.id
    try:
        user = User.objects.get(telegram_id=telegram_id)
    except User.DoesNotExist:
        await message.answer("❌ Пользователь не найден. Начните с /start")
        return
    
    devices = Device.objects.filter(holder=user)
    
    if not devices.exists():
        await message.answer("📦 У вас нет выданного оборудования.")
        return
    
    text = "📱 Ваше оборудование:\n\n"
    for device in devices:
        text += f"• {device.name}\n"
        text += f"  Инвентарный номер: {device.inventory_number}\n"
        if device.issued_at:
            text += f"  Выдано: {device.issued_at.strftime('%d.%m.%Y')}\n"
        text += "\n"
    
    return_text = get_bot_message('return_device_text',
        "Не используешь — сдай"
    )
    text += f"\n{return_text}"
    
    await message.answer(text)


async def handle_info(message: Message):
    """Показать информацию/контакты"""
    info_text = get_bot_message('info_contacts',
        "ℹ️ Информация и контакты:\n\n"
        "По вопросам обращайтесь к HR.\n"
        "Email: hr@ittest-team.ru"
    )
    await message.answer(info_text)


def register_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    
    # Команда /start
    dp.message.register(handle_start, CommandStart())
    
    # Обработка документов в состоянии ожидания
    dp.message.register(
        handle_documents,
        PreboardingStates.waiting_for_documents,
        F.photo | F.document
    )
    
    # Главное меню
    dp.message.register(handle_my_devices, F.text == "📱 Мое оборудование")
    dp.message.register(handle_info, F.text == "ℹ️ Инфо / Контакты")
    
    # Callback для завершения отправки документов
    dp.callback_query.register(handle_docs_complete, F.data == "docs_complete")


async def main():
    """Главная функция для запуска бота"""
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return
    
    bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    
    register_handlers(dp)
    
    logger.info("Bot started")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())

