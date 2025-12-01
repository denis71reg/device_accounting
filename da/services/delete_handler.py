"""Обработчик удаления сущностей с единой логикой."""
import logging

from flask_login import current_user
from sqlalchemy.orm import DeclarativeBase

from .soft_delete import hard_delete_entity, soft_delete_entity

logger = logging.getLogger(__name__)


def handle_entity_deletion(
    entity: DeclarativeBase,
    entity_type: str,
    entity_name: str | None = None,
    redirect_url: str | None = None,
) -> tuple[bool, str]:
    """
    Универсальная функция для обработки удаления сущности.
    
    Args:
        entity: Сущность для удаления
        entity_type: Тип сущности (для аудита и email)
        entity_name: Имя сущности (если None, будет получено автоматически)
        redirect_url: URL для редиректа (не используется, но может быть полезен)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if entity_name is None:
        entity_name = (
            getattr(entity, "name", None)
            or getattr(entity, "full_name", None)
            or getattr(entity, "inventory_number", None)
            or str(entity.id)
        )
    
    # Если супер-админ - удаляем физически, если админ - помечаем как удаленное
    if current_user.is_super_admin:
        success, message = hard_delete_entity(
            entity, entity_type, entity_name, current_user.email
        )
    else:
        # Админ - мягкое удаление
        success, message = soft_delete_entity(entity, entity_type, current_user, entity_name)
    
    return success, message
