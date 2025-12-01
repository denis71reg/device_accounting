"""Сервис для отправки email-уведомлений."""
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from flask import current_app

logger = logging.getLogger(__name__)


def send_deletion_notification(
    entity_type: str,
    entity_name: str,
    deleted_by: str,
    is_soft_delete: bool = False,
) -> bool:
    """
    Отправляет уведомление супер-админу о удалении объекта.
    
    Args:
        entity_type: Тип удаленного объекта (device, employee, warehouse, etc.)
        entity_name: Название удаленного объекта
        deleted_by: Email пользователя, который удалил объект
        is_soft_delete: True если это мягкое удаление, False если физическое
    
    Returns:
        bool: True если письмо отправлено успешно, False в противном случае
    """
    try:
        # Получаем настройки SMTP из конфигурации
        smtp_host = current_app.config.get("SMTP_HOST")
        smtp_port = current_app.config.get("SMTP_PORT", 587)
        smtp_user = current_app.config.get("SMTP_USER")
        smtp_password = current_app.config.get("SMTP_PASSWORD")
        
        # Отправитель всегда da@ittest-team.ru
        smtp_from = "da@ittest-team.ru"
        
        # Проверяем, что все необходимые настройки SMTP есть
        if not all([smtp_host, smtp_user, smtp_password]):
            logger.warning("SMTP настройки не полностью настроены, уведомление не отправлено")
            return False
        
        # Получаем email супер-админа из базы
        from ..models import User, UserRole
        super_admin = User.query.filter_by(role=UserRole.SUPER_ADMIN).first()
        if not super_admin:
            logger.warning("Супер-админ не найден в базе, уведомление не отправлено")
            return False
        
        recipient_email = super_admin.email
        
        # Создаем сообщение
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = recipient_email
        msg["Subject"] = f"Уведомление об удалении: {entity_type}"
        
        # Формируем тело письма
        delete_type = "помечен как удаленный" if is_soft_delete else "удален окончательно"
        delete_time = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M:%S UTC")
        
        # Переводим типы сущностей на русский
        entity_type_ru = {
            "device": "Девайс",
            "employee": "Сотрудник",
            "warehouse": "Склад",
            "location": "Локация",
            "device_type": "Тип девайса",
        }.get(entity_type, entity_type)
        
        body = f"""Уважаемый администратор!

В системе Device Accounting был {delete_type} объект:

Тип: {entity_type_ru}
Название: {entity_name}
Удален пользователем: {deleted_by}
Дата и время удаления: {delete_time}
Тип удаления: {"Мягкое удаление (можно восстановить)" if is_soft_delete else "Окончательное удаление"}

Вы можете просмотреть удаленные объекты в разделе "Удалено" системы.

---
Это автоматическое уведомление от системы Device Accounting.
"""
        
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        # Отправляем письмо
        try:
            # Порт 465 использует SSL/TLS с самого начала
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                # Порт 587 и другие используют STARTTLS
                server = smtplib.SMTP(smtp_host, smtp_port)
                if smtp_port == 587:
                    server.starttls()
            
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info("Уведомление об удалении отправлено на %s", recipient_email)
            return True
        except Exception as e:
            logger.error("Ошибка при отправке email уведомления: %s", str(e), exc_info=True)
            return False
            
    except Exception as e:
        logger.error("Ошибка при подготовке email уведомления: %s", str(e), exc_info=True)
        return False

