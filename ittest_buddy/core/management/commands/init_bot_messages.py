"""
Management команда для создания начальных сообщений бота
"""
from django.core.management.base import BaseCommand
from core.models import BotMessage


class Command(BaseCommand):
    help = 'Создать начальные сообщения бота (BotMessage)'

    def handle(self, *args, **options):
        messages_data = [
            {
                'slug': 'welcome_msg',
                'description': 'Приветствие новичка',
                'text': '👋 Добро пожаловать в IT Test!\n\nМы рады, что вы присоединяетесь к нашей команде.'
            },
            {
                'slug': 'docs_request',
                'description': 'Список необходимых документов',
                'text': '📄 Пожалуйста, отправьте следующие документы:\n- Паспорт (первая страница + прописка)\n- ИНН\n- СНИЛС\n- Трудовая книжка (если есть)\n\nВы можете отправить файлы фотографиями или документами.'
            },
            {
                'slug': 'vpn_instruction',
                'description': 'Инструкция по VPN',
                'text': '🔐 <b>VPN</b>\n\nДля подключения к VPN используй бота: @outline_ittest_bot'
            },
            {
                'slug': 'email_instruction',
                'description': 'Инструкция по почте/подписи',
                'text': '📧 <b>Почта и Подпись</b>\n\nПроверь свою корпоративную почту и настрой подпись согласно стандартам компании.'
            },
            {
                'slug': 'lunch_tula_tomorrow',
                'description': 'Сообщение про обед (Тула, до 12:00)',
                'text': '🍽 <b>Обед (Тула)</b>\n\nЗапишись на завтра в боте: @ittest_tula_dinner_bot'
            },
            {
                'slug': 'lunch_tula_closed',
                'description': 'Сообщение про обед (Тула, после 12:00)',
                'text': '🍽 <b>Обед (Тула)</b>\n\nНа завтра запись закрыта. Сохрани бота на будущее: @ittest_tula_dinner_bot'
            },
            {
                'slug': 'lunch_spb_today',
                'description': 'Сообщение про обед (СПб, до 14:30)',
                'text': '🍽 <b>Обед (СПб)</b>\n\nЗапишись на сегодня в боте: @ittest_spb_dinner_bot'
            },
            {
                'slug': 'lunch_spb_closed',
                'description': 'Сообщение про обед (СПб, после 14:30)',
                'text': '🍽 <b>Обед (СПб)</b>\n\nНа сегодня опоздал. Сохрани бота на будущее: @ittest_spb_dinner_bot'
            },
            {
                'slug': 'return_device_text',
                'description': 'Текст про сдачу оборудования',
                'text': 'Не используешь — сдай'
            },
            {
                'slug': 'info_contacts',
                'description': 'Информация и контакты',
                'text': 'ℹ️ Информация и контакты:\n\nПо вопросам обращайтесь к HR.\nEmail: hr@ittest-team.ru'
            },
        ]

        created_count = 0
        updated_count = 0

        for msg_data in messages_data:
            message, created = BotMessage.objects.get_or_create(
                slug=msg_data['slug'],
                defaults={
                    'description': msg_data['description'],
                    'text': msg_data['text']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Создано сообщение: {msg_data['slug']}")
                )
            else:
                # Обновляем описание и текст, если изменились
                updated = False
                if message.description != msg_data['description']:
                    message.description = msg_data['description']
                    updated = True
                if message.text != msg_data['text']:
                    message.text = msg_data['text']
                    updated = True
                if updated:
                    message.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"↻ Обновлено сообщение: {msg_data['slug']}")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"→ Пропущено (уже существует): {msg_data['slug']}")
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Создано: {created_count}, обновлено: {updated_count}, всего: {len(messages_data)}'
            )
        )







