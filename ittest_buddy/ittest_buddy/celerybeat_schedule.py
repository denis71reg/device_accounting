"""
Расписание задач Celery Beat
"""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'send-day-one-onboarding': {
        'task': 'bot.tasks.send_day_one_onboarding',
        'schedule': crontab(hour=9, minute=0),  # Каждый день в 09:00
    },
}







