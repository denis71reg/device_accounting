"""Тесты для маршрутов складов."""
import pytest
from flask import url_for

from da.models import Device, Location, Warehouse, DeviceStatus


class TestWarehousesList:
    """Тесты списка складов."""

    def test_list_warehouses_requires_login(self, client):
        """Тест: список складов требует авторизации."""
        response = client.get(url_for("warehouses.list_warehouses"))
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_list_warehouses_accessible_by_all_roles(self, client, regular_user, location, warehouse):
        """Тест: список складов доступен всем авторизованным пользователям."""
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("warehouses.list_warehouses"))
        assert response.status_code == 200
        assert warehouse.name.encode('utf-8') in response.data

    def test_list_warehouses_shows_device_count(self, client, admin_user, location, warehouse, device_type, device):
        """Тест: список складов показывает количество девайсов."""
        device.warehouse_id = warehouse.id
        device.location_id = location.id
        from da.extensions import db
        db.session.commit()

        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("warehouses.list_warehouses"))
        assert response.status_code == 200
        assert b"1" in response.data  # Количество девайсов


class TestCreateWarehouse:
    """Тесты создания склада."""

    def test_create_warehouse_requires_login(self, client):
        """Тест: создание склада требует авторизации."""
        response = client.get(url_for("warehouses.create_warehouse"))
        assert response.status_code == 302

    def test_create_warehouse_requires_admin(self, client, regular_user, location):
        """Тест: создание склада требует прав админа."""
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("warehouses.create_warehouse"))
        assert response.status_code == 403

    def test_create_warehouse_by_admin(self, client, admin_user, location):
        """Тест: админ может создать склад."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("warehouses.create_warehouse"), data={
            "name": "Новый склад",
            "location_name": location.name,
        }, follow_redirects=True)
        assert response.status_code == 200
        assert "Новый склад".encode('utf-8') in response.data

    def test_create_warehouse_creates_location_if_not_exists(self, client, admin_user):
        """Тест: создание склада создает локацию, если её нет."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("warehouses.create_warehouse"), data={
            "name": "Склад в новой локации",
            "location_name": "Новая локация",
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Проверяем, что локация создана
        new_location = Location.query.filter_by(name="Новая локация").first()
        assert new_location is not None


class TestEditWarehouse:
    """Тесты редактирования склада."""

    def test_edit_warehouse_requires_admin(self, client, regular_user, warehouse):
        """Тест: редактирование склада требует прав админа."""
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("warehouses.edit_warehouse", warehouse_id=warehouse.id))
        assert response.status_code == 403

    def test_edit_warehouse_by_admin(self, client, admin_user, warehouse, location):
        """Тест: админ может редактировать склад."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("warehouses.edit_warehouse", warehouse_id=warehouse.id), data={
            "name": "Обновленный склад",
            "location_name": location.name,
        }, follow_redirects=True)
        assert response.status_code == 200
        assert "Обновленный склад".encode('utf-8') in response.data


class TestDeleteWarehouse:
    """Тесты удаления склада."""

    def test_delete_warehouse_requires_admin(self, client, regular_user, warehouse):
        """Тест: удаление склада требует прав админа."""
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("warehouses.delete_warehouse", warehouse_id=warehouse.id))
        assert response.status_code == 403

    def test_cannot_delete_warehouse_with_devices(self, client, admin_user, warehouse, device, location, device_type, db_session):
        """Тест: нельзя удалить склад с девайсами."""
        with client.application.app_context():
            device.warehouse_id = warehouse.id
            device.location_id = location.id
            db_session.commit()

        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("warehouses.delete_warehouse", warehouse_id=warehouse.id), follow_redirects=True)
        assert response.status_code == 200
        response_text = response.data.decode('utf-8').lower()
        assert "девайс" in response_text or "удалить" in response_text


class TestWarehouseDevices:
    """Тесты просмотра девайсов склада."""

    def test_warehouse_devices_requires_login(self, client, warehouse):
        """Тест: просмотр девайсов склада требует авторизации."""
        response = client.get(url_for("warehouses.warehouse_devices", warehouse_id=warehouse.id))
        assert response.status_code == 302

    def test_warehouse_devices_shows_devices(self, client, admin_user, warehouse, device, location, device_type, db_session):
        """Тест: просмотр девайсов склада показывает девайсы."""
        with client.application.app_context():
            from da.models import Device, Warehouse
            # Получаем объекты из сессии
            dev = db_session.query(Device).filter(Device.id == device.id).first()
            wh = db_session.query(Warehouse).filter(Warehouse.id == warehouse.id).first()
            dev.warehouse_id = wh.id
            dev.location_id = location.id
            db_session.commit()
            device_id = dev.id
            warehouse_id = wh.id
            inventory_number = str(dev.inventory_number)  # Сохраняем как строку

        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("warehouses.warehouse_devices", warehouse_id=warehouse_id))
        assert response.status_code == 200
        # Проверяем, что inventory_number присутствует в ответе
        response_text = response.data.decode('utf-8') if isinstance(response.data, bytes) else str(response.data)
        assert inventory_number in response_text

