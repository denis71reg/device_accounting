"""Утилиты для мягкого удаления (soft delete)."""
import logging

from sqlalchemy.orm import DeclarativeBase

from ..extensions import db
from ..models import AuditAction, utcnow
from .audit import log_action
from . import email

logger = logging.getLogger(__name__)


def soft_delete_entity(
    entity: DeclarativeBase,
    entity_type: str,
    current_user,
    entity_name: str | None = None,
) -> tuple[bool, str]:
    """
    Помечает сущность как удаленную (мягкое удаление).
    
    Args:
        entity: Сущность для удаления
        entity_type: Тип сущности (для аудита)
        current_user: Текущий пользователь
        entity_name: Имя сущности (для аудита), если None - будет получено автоматически
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if entity_name is None:
        entity_name = getattr(entity, "name", None) or getattr(entity, "full_name", None) or getattr(entity, "inventory_number", None) or str(entity.id)
    
    entity_id = entity.id
    
    # Помечаем как удаленное
    entity.deleted_at = utcnow()
    db.session.commit()
    
    log_action(
        AuditAction.DELETE,
        entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        changes={"deleted_by": current_user.email, "soft_delete": True},
    )
    
    # Отправляем уведомление на email
    try:
        email.send_deletion_notification(
            entity_type=entity_type,
            entity_name=entity_name,
            deleted_by=current_user.email,
            is_soft_delete=True,
        )
    except Exception as e:
        logger.error("Ошибка при отправке уведомления об удалении: %s", str(e), exc_info=True)
    
    message = f"{entity_type} '{entity_name}' перемещен в раздел 'Удалено'"
    logger.info("%s %s (%s) помечен как удаленный админом %s", entity_type, entity_name, entity_id, current_user.email)
    
    return True, message


def hard_delete_entity(
    entity: DeclarativeBase,
    entity_type: str,
    entity_name: str | None = None,
    deleted_by_email: str | None = None,
) -> tuple[bool, str]:
    """
    Физически удаляет сущность из базы данных.
    
    Args:
        entity: Сущность для удаления
        entity_type: Тип сущности (для аудита)
        entity_name: Имя сущности (для аудита), если None - будет получено автоматически
        deleted_by_email: Email пользователя, который удалил объект (если None, будет получен из current_user)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if entity_name is None:
        entity_name = getattr(entity, "name", None) or getattr(entity, "full_name", None) or getattr(entity, "inventory_number", None) or str(entity.id)
    
    entity_id = entity.id
    
    # Получаем email пользователя
    if deleted_by_email is None:
        try:
            from flask_login import current_user
            deleted_by_email = current_user.email if current_user.is_authenticated else "system"
        except Exception:
            deleted_by_email = "system"
    
    db.session.delete(entity)
    db.session.commit()
    
    log_action(
        AuditAction.DELETE,
        entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
    )
    
    # Отправляем уведомление на email
    try:
        email.send_deletion_notification(
            entity_type=entity_type,
            entity_name=entity_name,
            deleted_by=deleted_by_email,
            is_soft_delete=False,
        )
    except Exception as e:
        logger.error("Ошибка при отправке уведомления об удалении: %s", str(e), exc_info=True)
    
    message = f"{entity_type} '{entity_name}' удален"
    logger.info("Удалён %s %s (%s) супер-админом", entity_type, entity_name, entity_id)
    
    return True, message

