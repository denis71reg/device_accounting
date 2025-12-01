from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid


class UserStatus(models.TextChoices):
    PRE_HIRE = 'pre_hire', 'Кандидат (ждет документы)'
    READY_TO_START = 'ready_to_start', 'Документы сданы (ждет даты выхода)'
    ACTIVE = 'active', 'Работает'
    ALUMNI = 'alumni', 'Уволен'


class Location(models.TextChoices):
    TULA = 'tula', 'Тула'
    SPB = 'spb', 'Санкт-Петербург'
    REMOTE = 'remote', 'Удаленка'


class User(models.Model):
    """Расширенная модель сотрудника/кандидата"""
    telegram_id = models.BigIntegerField(
        unique=True, 
        null=True, 
        blank=True,
        verbose_name='Telegram ID'
    )
    username = models.CharField(
        max_length=255,
        verbose_name='Никнейм',
        help_text='@username в Telegram'
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name='ФИО'
    )
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.PRE_HIRE,
        verbose_name='Статус'
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата выхода на работу'
    )
    location = models.CharField(
        max_length=20,
        choices=Location.choices,
        verbose_name='Офис'
    )
    role = models.CharField(
        max_length=255,
        verbose_name='Должность',
        help_text='Например: Dev, QA, PM'
    )
    reinvite_token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name='Токен перепривязки'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создан'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлен'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} (@{self.username})"

    def clean(self):
        if self.status == UserStatus.ACTIVE and not self.start_date:
            raise ValidationError('Для активного сотрудника должна быть указана дата выхода на работу')


class Device(models.Model):
    """Оборудование компании"""
    name = models.CharField(
        max_length=255,
        verbose_name='Название',
        help_text='Например: MacBook Pro 16 M1'
    )
    inventory_number = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Инвентарный номер'
    )
    holder = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devices',
        verbose_name='Владелец'
    )
    issued_at = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата выдачи'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создан'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлен'
    )

    class Meta:
        verbose_name = 'Устройство'
        verbose_name_plural = 'Устройства'
        ordering = ['-issued_at', 'name']

    def __str__(self):
        holder_str = f" ({self.holder.full_name})" if self.holder else " (на складе)"
        return f"{self.name} - {self.inventory_number}{holder_str}"


class BotMessage(models.Model):
    """Сообщения бота для редактирования через админку (CMS)"""
    slug = models.SlugField(
        unique=True,
        verbose_name='Технический код',
        help_text='Например: welcome_msg, lunch_tula_instruction'
    )
    text = models.TextField(
        verbose_name='Текст сообщения',
        help_text='Поддерживает HTML/Markdown'
    )
    description = models.CharField(
        max_length=255,
        verbose_name='Описание',
        help_text='Пометка для админа, например: "Текст приветствия новичка"'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создан'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлен'
    )

    class Meta:
        verbose_name = 'Сообщение бота'
        verbose_name_plural = 'Сообщения бота'
        ordering = ['slug']

    def __str__(self):
        return f"{self.slug} - {self.description}"




