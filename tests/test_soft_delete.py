"""Тесты для мягкого удаления (soft delete)."""
import pytest
from flask import url_for

from da.models import Device, DeviceType, Employee, Location, UserRole, Warehouse


class TestSoftDelete:
    """Тесты мягкого удаления."""

    def test_admin_soft_deletes_device(self, client, admin_user, device, db_session):
        """Админ помечает девайс как удаленный, не удаляет физически."""
        from flask import Flask
        app = client.application
        
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        device_id = device.id
        # Админ не может удалять, только супер-админ
        response = client.post(url_for("devices.delete_device", device_id=device_id))
        
        assert response.status_code == 403  # Админ получает 403 при попытке удалить

    def test_super_admin_hard_deletes_device(self, client, super_admin_user, device, db_session):
        """Супер-админ удаляет девайс физически."""
        with client.application.app_context():
            from da.models import Device as DeviceModel
            # Используем inventory_number для поиска
            dev = db_session.query(DeviceModel).filter(DeviceModel.inventory_number == "INV-001").first()
            device_id = dev.id
        
        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        response = client.post(url_for("devices.delete_device", device_id=device_id))
        
        assert response.status_code == 302
        # Девайс должен быть удален физически
        with client.application.app_context():
            deleted_device = db_session.query(DeviceModel).filter(DeviceModel.id == device_id).first()
            assert deleted_device is None

    def test_deleted_devices_not_shown_in_list(self, client, super_admin_user, device, db_session):
        """Удаленные девайсы не показываются в списке."""
        with client.application.app_context():
            from da.models import Device as DeviceModel
            # Используем inventory_number для поиска
            dev = db_session.query(DeviceModel).filter(DeviceModel.inventory_number == "INV-001").first()
            device_id = dev.id
            inventory_number = dev.inventory_number
        
        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        # Удаляем девайс (супер-админ может удалять)
        response = client.post(url_for("devices.delete_device", device_id=device_id))
        assert response.status_code == 302
        
        # Проверяем список девайсов
        response = client.get(url_for("devices.list_devices"))
        assert response.status_code == 200
        response_text = response.data.decode('utf-8') if isinstance(response.data, bytes) else str(response.data)
        # Девайс не должен быть в списке (удален физически или мягко)
        assert inventory_number not in response_text

    def test_cannot_delete_employee_with_devices(self, client, admin_user, employee, device, db_session):
        """Нельзя удалить сотрудника, если у него есть девайсы."""
        with client.application.app_context():
            from da.models import Device as DeviceModel, Employee as EmployeeModel
            # Используем inventory_number для поиска device
            dev = db_session.query(DeviceModel).filter(DeviceModel.inventory_number == "INV-001").first()
            # Используем email для поиска employee
            emp = db_session.query(EmployeeModel).filter(EmployeeModel.email == "test@ittest-team.ru").first()
            if not emp:
                # Если не нашли, создаем нового
                from da.models import Location
                location = db_session.query(Location).first()
                emp = EmployeeModel(
                    first_name="Test",
                    last_name="Employee",
                    position="Developer",
                    email="test@ittest-team.ru",
                    phone="+1234567890",
                    location_id=location.id,
                )
                db_session.add(emp)
                db_session.commit()
            dev.owner_id = emp.id
            db_session.commit()
            employee_id = emp.id
        
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        # Пытаемся удалить сотрудника
        response = client.post(url_for("employees.delete_employee", employee_id=employee_id))
        assert response.status_code == 302
        
        # Сотрудник не должен быть удален
        with client.application.app_context():
            emp = db_session.query(EmployeeModel).filter(EmployeeModel.id == employee_id).first()
            assert emp is not None
            assert emp.deleted_at is None

    def test_cannot_delete_warehouse_with_devices(self, client, admin_user, warehouse, device, db_session):
        """Нельзя удалить склад, если к нему привязаны девайсы."""
        with client.application.app_context():
            from da.models import Device as DeviceModel, Warehouse as WarehouseModel
            # Используем inventory_number для поиска device
            dev = db_session.query(DeviceModel).filter(DeviceModel.inventory_number == "INV-001").first()
            # Используем name для поиска warehouse
            wh = db_session.query(WarehouseModel).filter(WarehouseModel.name == "Main Warehouse").first()
            if not wh:
                # Если не нашли, создаем новый
                from da.models import Location
                location = db_session.query(Location).first()
                wh = WarehouseModel(
                    name="Main Warehouse",
                    location_id=location.id,
                )
                db_session.add(wh)
                db_session.commit()
            dev.warehouse_id = wh.id
            db_session.commit()
            warehouse_id = wh.id
        
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        # Пытаемся удалить склад
        response = client.post(url_for("warehouses.delete_warehouse", warehouse_id=warehouse_id))
        assert response.status_code == 302
        
        # Склад не должен быть удален
        with client.application.app_context():
            wh = db_session.query(WarehouseModel).filter(WarehouseModel.id == warehouse_id).first()
            assert wh is not None
            assert wh.deleted_at is None

    def test_cannot_delete_device_type_with_devices(self, client, admin_user, device_type, device, db_session):
        """Нельзя удалить тип девайса, если к нему привязаны девайсы."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        # Привязываем девайс к типу
        device.type_id = device_type.id
        db_session.commit()
        
        # Пытаемся удалить тип девайса
        response = client.post(url_for("device_types.delete_device_type", device_type_id=device_type.id))
        assert response.status_code == 302
        
        # Тип девайса не должен быть удален
        assert DeviceType.query.get(device_type.id) is not None
        assert DeviceType.query.get(device_type.id).deleted_at is None

    def test_deleted_list_only_visible_to_super_admin(self, client, admin_user, regular_user, device, db_session):
        """Раздел 'Удалено' виден только супер-админу."""
        # Админ не может видеть раздел "Удалено"
        client.post(url_for("auth.logout"))
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("deleted.list_deleted"))
        assert response.status_code == 403

        # Обычный пользователь не может видеть раздел "Удалено"
        client.post(url_for("auth.logout"))
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("deleted.list_deleted"))
        assert response.status_code == 403

    def test_restore_deleted_entity(self, client, super_admin_user, device, db_session):
        """Супер-админ может восстановить удаленный объект."""
        # Получаем device_id до того, как device станет detached
        with client.application.app_context():
            from da.models import Device as DeviceModel
            # Используем inventory_number для поиска, так как device может быть detached
            inventory_number = "INV-001"  # Из фикстуры device
            dev = db_session.query(DeviceModel).filter(DeviceModel.inventory_number == inventory_number).first()
            if not dev:
                # Если не нашли, создаем новый
                from da.models import DeviceType, Location, Warehouse, DeviceStatus
                device_type = db_session.query(DeviceType).first()
                location = db_session.query(Location).first()
                warehouse = db_session.query(Warehouse).first()
                dev = DeviceModel(
                    inventory_number=inventory_number,
                    model="Test Device",
                    type_id=device_type.id,
                    location_id=location.id,
                    warehouse_id=warehouse.id,
                    status=DeviceStatus.IN_STOCK,
                )
                db_session.add(dev)
                db_session.commit()
            device_id = dev.id
            
            # Мягко удаляем девайс через прямое обновление БД
            from datetime import datetime, timezone
            dev.deleted_at = datetime.now(timezone.utc)
            db_session.commit()
        
        # Супер-админ восстанавливает
        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        response = client.post(url_for("deleted.restore_entity", entity_type="device", entity_id=device_id))
        assert response.status_code == 302
        
        # Девайс должен быть восстановлен
        with client.application.app_context():
            restored_device = db_session.query(DeviceModel).filter(DeviceModel.id == device_id).first()
            assert restored_device is not None
            assert restored_device.deleted_at is None

    def test_permanent_delete_entity(self, client, super_admin_user, device, db_session):
        """Супер-админ может окончательно удалить объект."""
        # Получаем device_id до того, как device станет detached
        with client.application.app_context():
            from da.models import Device as DeviceModel
            # Используем inventory_number для поиска, так как device может быть detached
            inventory_number = "INV-001"  # Из фикстуры device
            dev = db_session.query(DeviceModel).filter(DeviceModel.inventory_number == inventory_number).first()
            if not dev:
                # Если не нашли, создаем новый
                from da.models import DeviceType, Location, Warehouse, DeviceStatus
                device_type = db_session.query(DeviceType).first()
                location = db_session.query(Location).first()
                warehouse = db_session.query(Warehouse).first()
                dev = DeviceModel(
                    inventory_number=inventory_number,
                    model="Test Device",
                    type_id=device_type.id,
                    location_id=location.id,
                    warehouse_id=warehouse.id,
                    status=DeviceStatus.IN_STOCK,
                )
                db_session.add(dev)
                db_session.commit()
            device_id = dev.id
            
            # Мягко удаляем девайс через прямое обновление БД
            from datetime import datetime, timezone
            dev.deleted_at = datetime.now(timezone.utc)
            db_session.commit()
        
        # Супер-админ окончательно удаляет
        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        response = client.post(url_for("deleted.permanent_delete_entity", entity_type="device", entity_id=device_id))
        assert response.status_code == 302
        
        # Девайс должен быть удален физически
        with client.application.app_context():
            deleted_device = db_session.query(DeviceModel).filter(DeviceModel.id == device_id).first()
            assert deleted_device is None

