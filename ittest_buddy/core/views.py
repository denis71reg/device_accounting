from django.shortcuts import render, redirect
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.conf import settings
from .models import User
import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError


@staff_member_required
def broadcast_message(request):
    """Страница для отправки рассылки выбранным пользователям"""
    user_ids = request.session.get('broadcast_user_ids', [])
    user_count = request.session.get('broadcast_count', 0)

    if not user_ids:
        messages.error(request, "Не выбраны пользователи для рассылки")
        return redirect('admin:core_user_changelist')

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        
        if not message_text:
            messages.error(request, "Сообщение не может быть пустым")
            return render(request, 'admin/broadcast_form.html', {
                'user_count': user_count,
                'selected_users': User.objects.filter(id__in=user_ids)
            })

        # Получаем пользователей с telegram_id
        users = User.objects.filter(id__in=user_ids, telegram_id__isnull=False)
        
        if not users.exists():
            messages.error(request, "У выбранных пользователей нет привязанного Telegram")
            return redirect('admin:core_user_changelist')

        # Отправляем сообщения через бота
        success_count = 0
        error_count = 0
        errors = []

        if not AIOGRAM_AVAILABLE:
            messages.error(request, "Aiogram не установлен. Установите: pip install aiogram")
            return redirect('admin:core_user_changelist')
        
        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            messages.error(request, "Не настроен токен бота (TELEGRAM_BOT_TOKEN)")
            return redirect('admin:core_user_changelist')

        async def send_messages():
            nonlocal success_count, error_count
            bot = Bot(token=bot_token)
            
            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message_text
                    )
                    success_count += 1
                except TelegramBadRequest as e:
                    error_count += 1
                    errors.append(f"{user.full_name}: {str(e)}")
                except TelegramAPIError as e:
                    error_count += 1
                    errors.append(f"{user.full_name}: {str(e)}")
                except Exception as e:
                    error_count += 1
                    errors.append(f"{user.full_name}: Неизвестная ошибка - {str(e)}")
            
            await bot.session.close()

        # Запускаем асинхронную отправку
        asyncio.run(send_messages())

        # Очищаем сессию
        request.session.pop('broadcast_user_ids', None)
        request.session.pop('broadcast_count', None)

        if success_count > 0:
            messages.success(request, f"Сообщение отправлено {success_count} пользователям")
        if error_count > 0:
            messages.warning(request, f"Не удалось отправить {error_count} сообщений")
            if errors:
                for error in errors[:5]:  # Показываем первые 5 ошибок
                    messages.error(request, error)

        return redirect('admin:core_user_changelist')

    selected_users = User.objects.filter(id__in=user_ids)
    return render(request, 'admin/broadcast_form.html', {
        'user_count': user_count,
        'selected_users': selected_users,
        'title': 'Отправка сообщения',
        'opts': User._meta,
        'has_view_permission': True,
        'has_add_permission': False,
        'has_change_permission': False,
        'has_delete_permission': False,
        'has_editable_inline_admin_formsets': False,
        'is_popup': False,
        'is_nav_sidebar_enabled': True,
        'show_close': False,
    })

