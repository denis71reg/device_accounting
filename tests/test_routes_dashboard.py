"""Тесты для роутов дашборда."""
import pytest
from da.extensions import db
from da.models import Device, DeviceType, Warehouse


class TestDashboard:
    """Тесты для главной страницы."""

    def test_dashboard_requires_login(self, client):
        """Дашборд требует авторизации."""
        response = client.get("/")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_dashboard_accessible_by_all_roles(
        self, logged_in_user, logged_in_admin, logged_in_super_admin, app, location, device_type, warehouse
    ):
        """Дашборд доступен всем авторизованным пользователям."""
        with app.app_context():
            device = Device(
                inventory_number="INV-DASH-001",
                model="MacBook Pro",
                type_id=device_type.id,
                warehouse_id=warehouse.id,
            )
            db.session.add(device)
            db.session.commit()

        for client in [logged_in_user, logged_in_admin, logged_in_super_admin]:
            response = client.get("/")
            assert response.status_code == 200
            assert b"INV-DASH-001" in response.data

