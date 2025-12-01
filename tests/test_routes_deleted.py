"""Тесты для маршрутов удаленных объектов."""
import pytest
from flask import url_for
from datetime import datetime, timezone

from da.models import Device, DeviceType, Employee, Location, Warehouse
from da.extensions import db


class TestDeletedList:
    """Тесты списка удаленных объектов."""

    def test_list_deleted_requires_login(self, client):
        """Тест: список удаленных объектов требует авторизации."""
        response = client.get(url_for("deleted.list_deleted"))
        assert response.status_code == 302

    def test_list_deleted_requires_super_admin(self, client, admin_user):
        """Тест: список удаленных объектов доступен только супер-админу."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("deleted.list_deleted"))
        assert response.status_code == 403

    def test_list_deleted_accessible_by_super_admin(self, client, super_admin_user, device, location, warehouse, db_session):
        """Тест: супер-админ может просматривать удаленные объекты."""
        # Мягко удаляем девайс
        with client.application.app_context():
            device.deleted_at = datetime.now(timezone.utc)
            db_session.commit()

        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("deleted.list_deleted"))
        assert response.status_code == 200
        # Получаем inventory_number в контексте
        with client.application.app_context():
            device_obj = Device.query.get(device.id)
            if device_obj:
                assert device_obj.inventory_number.encode('utf-8') in response.data


class TestRestoreEntity:
    """Тесты восстановления удаленных объектов."""

    def test_restore_entity_requires_super_admin(self, client, admin_user, device, location, warehouse, db_session):
        """Тест: восстановление требует прав супер-админа."""
        with client.application.app_context():
            device.deleted_at = datetime.now(timezone.utc)
            db_session.commit()

        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        # Получаем ID девайса в контексте
        with client.application.app_context():
            device_obj = Device.query.get(device.id)
            device_id = device_obj.id if device_obj else device.id
        response = client.post(url_for("deleted.restore_entity", entity_type="device", entity_id=device_id))
        assert response.status_code == 403

    def test_restore_entity_by_super_admin(self, client, super_admin_user, device, location, warehouse, db_session):
        """Тест: супер-админ может восстановить удаленный объект."""
        with client.application.app_context():
            device.deleted_at = datetime.now(timezone.utc)
            db_session.commit()

        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        # Получаем ID девайса в контексте
        with client.application.app_context():
            device_obj = Device.query.get(device.id)
            device_id = device_obj.id if device_obj else device.id
        
        response = client.post(
            url_for("deleted.restore_entity", entity_type="device", entity_id=device_id),
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Проверяем, что девайс восстановлен
        with client.application.app_context():
            restored_device = Device.query.get(device_id)
            assert restored_device is not None
            assert restored_device.deleted_at is None


class TestPermanentDeleteEntity:
    """Тесты окончательного удаления объектов."""

    def test_permanent_delete_requires_super_admin(self, client, admin_user, device, location, warehouse, db_session):
        """Тест: окончательное удаление требует прав супер-админа."""
        with client.application.app_context():
            device.deleted_at = datetime.now(timezone.utc)
            db_session.commit()

        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        # Получаем ID девайса в контексте
        with client.application.app_context():
            device_obj = Device.query.get(device.id)
            device_id = device_obj.id if device_obj else device.id
        response = client.post(url_for("deleted.permanent_delete_entity", entity_type="device", entity_id=device_id))
        assert response.status_code == 403

    def test_permanent_delete_by_super_admin(self, client, super_admin_user, device, location, warehouse, db_session):
        """Тест: супер-админ может окончательно удалить объект."""
        with client.application.app_context():
            device.deleted_at = datetime.now(timezone.utc)
            device_id = device.id
            db_session.commit()

        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        # Получаем ID девайса в контексте
        with client.application.app_context():
            device_obj = Device.query.get(device.id)
            device_id = device_obj.id if device_obj else device.id
        
        response = client.post(
            url_for("deleted.permanent_delete_entity", entity_type="device", entity_id=device_id),
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Проверяем, что девайс удален
        with client.application.app_context():
            deleted_device = Device.query.get(device_id)
            assert deleted_device is None

