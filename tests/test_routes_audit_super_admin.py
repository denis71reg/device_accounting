"""Тесты для роутов аудита (только для супер-админа)."""
import pytest
from da.extensions import db
from da.models import AuditLog, AuditAction, User, UserRole


def test_audit_list_accessible_by_super_admin(logged_in_super_admin, app):
    """Список аудита доступен супер-администратору."""
    with app.app_context():
        # Получаем ID супер-админа из базы
        user = User.query.filter_by(email="superadmin@ittest-team.ru").first()
        user_id = user.id if user else None
        assert user_id is not None
        
        audit_log = AuditLog(
            user_id=user_id,
            action=AuditAction.CREATE,
            entity_type="device",
            entity_id=1,
            entity_name="Test Device",
        )
        db.session.add(audit_log)
        db.session.commit()

    response = logged_in_super_admin.get("/audit/")
    assert response.status_code == 200

