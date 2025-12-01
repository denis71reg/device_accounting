"""Тесты для маршрутов типов девайсов."""
import pytest
from flask import url_for

from da.models import Device, DeviceType, Location, Warehouse, DeviceStatus


class TestDeviceTypesList:
    """Тесты списка типов девайсов."""

    def test_list_device_types_requires_login(self, client):
        """Тест: список типов девайсов требует авторизации."""
        response = client.get(url_for("device_types.list_device_types"))
        assert response.status_code == 302

    def test_list_device_types_accessible_by_all_roles(self, client, regular_user, device_type):
        """Тест: список типов девайсов доступен всем авторизованным пользователям."""
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("device_types.list_device_types"))
        assert response.status_code == 200
        assert device_type.name.encode('utf-8') in response.data

    def test_list_device_types_shows_device_count(self, client, admin_user, device_type, device, location, warehouse):
        """Тест: список типов девайсов показывает количество девайсов."""
        device.type_id = device_type.id
        device.warehouse_id = warehouse.id
        device.location_id = location.id
        from da.extensions import db
        db.session.commit()

        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("device_types.list_device_types"))
        assert response.status_code == 200
        assert b"1" in response.data  # Количество девайсов


class TestCreateDeviceType:
    """Тесты создания типа девайса."""

    def test_create_device_type_requires_login(self, client):
        """Тест: создание типа девайса требует авторизации."""
        response = client.get(url_for("device_types.create_device_type"))
        assert response.status_code == 302

    def test_create_device_type_requires_admin(self, client, regular_user):
        """Тест: создание типа девайса требует прав админа."""
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("device_types.create_device_type"))
        assert response.status_code == 403

    def test_create_device_type_by_admin(self, client, admin_user):
        """Тест: админ может создать тип девайса."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("device_types.create_device_type"), data={
            "name": "Новый тип",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert "Новый тип".encode('utf-8') in response.data


class TestEditDeviceType:
    """Тесты редактирования типа девайса."""

    def test_edit_device_type_requires_admin(self, client, regular_user, device_type):
        """Тест: редактирование типа девайса требует прав админа."""
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("device_types.edit_device_type", device_type_id=device_type.id))
        assert response.status_code == 403

    def test_edit_device_type_by_admin(self, client, admin_user, device_type):
        """Тест: админ может редактировать тип девайса."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("device_types.edit_device_type", device_type_id=device_type.id), data={
            "name": "Обновленный тип",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert "Обновленный тип".encode('utf-8') in response.data


class TestDeleteDeviceType:
    """Тесты удаления типа девайса."""

    def test_delete_device_type_requires_admin(self, client, regular_user, device_type):
        """Тест: удаление типа девайса требует прав админа."""
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("device_types.delete_device_type", device_type_id=device_type.id))
        assert response.status_code == 403

    def test_cannot_delete_device_type_with_devices(self, client, admin_user, device_type, device, location, warehouse):
        """Тест: нельзя удалить тип девайса с девайсами."""
        device.type_id = device_type.id
        device.warehouse_id = warehouse.id
        device.location_id = location.id
        from da.extensions import db
        db.session.commit()

        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("device_types.delete_device_type", device_type_id=device_type.id), follow_redirects=True)
        assert response.status_code == 200
        response_text = response.data.decode('utf-8').lower()
        assert "девайс" in response_text or "удалить" in response_text

