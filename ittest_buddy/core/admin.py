from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, Device, BotMessage


class UserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'username', 'status', 'location', 'role', 'start_date', 'reinvite_link')
    list_filter = ('status', 'location', 'role')
    search_fields = ('username', 'full_name', 'telegram_id')
    readonly_fields = ('telegram_id', 'reinvite_token', 'created_at', 'updated_at', 'reinvite_link_display')
    fieldsets = (
        ('Основная информация', {
            'fields': ('username', 'full_name', 'status', 'location', 'role', 'start_date')
        }),
        ('Telegram', {
            'fields': ('telegram_id', 'reinvite_token', 'reinvite_link_display')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def reinvite_link(self, obj):
        if obj.reinvite_token:
            from django.conf import settings
            bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'ittest_buddy_bot')
            url = f"https://t.me/{bot_username}?start=reinvite_{obj.reinvite_token}"
            return format_html('<a href="{}" target="_blank">Открыть ссылку</a>', url)
        return "-"

    reinvite_link.short_description = "Ссылка перепривязки"

    def reinvite_link_display(self, obj):
        if obj.reinvite_token:
            from django.conf import settings
            bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'ittest_buddy_bot')
            url = f"https://t.me/{bot_username}?start=reinvite_{obj.reinvite_token}"
            return format_html('<a href="{}" target="_blank">{}</a><br><small>{}</small>', 
                             url, url, "Скопируйте эту ссылку и отправьте сотруднику")
        return "Токен не сгенерирован. Используйте действие 'Сгенерировать ссылку перепривязки'"

    reinvite_link_display.short_description = "Ссылка перепривязки"

    actions = ['generate_reinvite_token', 'send_broadcast']

    def generate_reinvite_token(self, request, queryset):
        import uuid
        for user in queryset:
            user.reinvite_token = uuid.uuid4()
            user.save()
        self.message_user(request, f"Ссылки перепривязки сгенерированы для {queryset.count()} пользователей")

    generate_reinvite_token.short_description = "Сгенерировать ссылку перепривязки"

    def send_broadcast(self, request, queryset):
        # Сохраняем ID выбранных пользователей в сессии
        user_ids = list(queryset.values_list('id', flat=True))
        request.session['broadcast_user_ids'] = user_ids
        request.session['broadcast_count'] = len(user_ids)
        from django.urls import reverse
        from django.shortcuts import redirect
        return redirect(reverse('admin:broadcast_message'))

    send_broadcast.short_description = "Отправить сообщение выбранным"


class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'inventory_number', 'holder', 'issued_at')
    list_filter = ('issued_at',)
    search_fields = ('name', 'inventory_number', 'holder__full_name')
    autocomplete_fields = ('holder',)
    date_hierarchy = 'issued_at'


class BotMessageAdmin(admin.ModelAdmin):
    list_display = ('slug', 'description', 'preview')
    search_fields = ('slug', 'description', 'text')
    readonly_fields = ('slug',)

    def preview(self, obj):
        preview_text = obj.text[:100] + "..." if len(obj.text) > 100 else obj.text
        return format_html('<div style="max-width: 400px;">{}</div>', preview_text)

    preview.short_description = "Предпросмотр"


admin.site.register(User, UserAdmin)
admin.site.register(Device, DeviceAdmin)
admin.site.register(BotMessage, BotMessageAdmin)

# Настройка админки
admin.site.site_header = "IT Test Buddy - Админка"
admin.site.site_title = "IT Test Buddy"
admin.site.index_title = "Управление системой"

