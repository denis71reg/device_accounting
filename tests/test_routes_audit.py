"""Тесты для роутов аудита."""
import pytest
from da.extensions import db
from da.models import AuditLog, AuditAction


class TestAuditList:
    """Тесты для списка аудита."""

    def test_audit_list_requires_login(self, client):
        """Список аудита требует авторизации."""
        response = client.get("/audit/")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_audit_list_requires_super_admin(
        self, logged_in_user, logged_in_admin, app
    ):
        """Список аудита доступен только супер-администраторам."""
        # Обычный пользователь не может видеть аудит
        response = logged_in_user.get("/audit/")
        assert response.status_code == 403
        
        # Админ не может видеть аудит
        response = logged_in_admin.get("/audit/")
        assert response.status_code == 403

