import json
import logging
from typing import Any, Optional

from flask import request
from flask_login import current_user

from ..extensions import db
from ..models import AuditAction, AuditLog

logger = logging.getLogger(__name__)


def log_action(
    action: AuditAction,
    entity_type: str,
    entity_id: Optional[int] = None,
    entity_name: Optional[str] = None,
    changes: Optional[dict[str, Any]] = None,
) -> None:
    """Логирует действие пользователя в audit log"""
    if not current_user.is_authenticated:
        return

    # Только супер-админы могут видеть логи, но логируем действия всех
    audit_log = AuditLog(
        user_id=current_user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        changes=json.dumps(changes, ensure_ascii=False) if changes else None,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )

    db.session.add(audit_log)
    db.session.commit()
    logger.info(
        "AUDIT %s entity=%s(%s) user=%s",
        action.value,
        entity_type,
        entity_id,
        current_user.email,
    )


def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = 100,
) -> list[AuditLog]:
    """Получает записи audit log с фильтрацией"""
    query = AuditLog.query.order_by(AuditLog.created_at.desc())

    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    if entity_id:
        query = query.filter_by(entity_id=entity_id)

    return query.limit(limit).all()


