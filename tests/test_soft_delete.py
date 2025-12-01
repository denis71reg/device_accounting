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
        
        # Получаем ID девайса безопасно
        with client.application.app_context():
            from da.models import Device as DeviceModel
            d = DeviceModel.query.first()
            device_id = d.id
            # Сбрасываем deleted_at
            if d.deleted_at:
                d.deleted_at = None
                db_session.commit()
    
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
    
        # Удаляем девайс
        response = client.post(url_for("devices.delete_device", device_id=device_id))
        assert response.status_code == 302
        
        with client.application.app_context():
            from da.models import Device as DeviceModel
            # Проверяем, что девайс помечен как удаленный
            dev = db_session.query(DeviceModel).filter(DeviceModel.id == device_id).first()
            assert dev is not None
            assert dev.deleted_at is not None

    def test_super_admin_hard_deletes_device(self, client, super_admin_user, device, db_session):
        """Супер-админ удаляет девайс физически."""
        # Получаем ID девайса безопасно
        with client.application.app_context():
            from da.models import Device as DeviceModel
            d = DeviceModel.query.first()
            device_id = d.id
            d.deleted_at = None
            db_session.commit()
    
        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
    
        # Удаляем девайс
        response = client.post(url_for("devices.delete_device", device_id=device_id))
        assert response.status_code == 302
        
        with client.application.app_context():
            from da.models import Device as DeviceModel
            # Проверяем, что девайс удален физически
            dev = db_session.query(DeviceModel).filter(DeviceModel.id == device_id).first()
            assert dev is None

    def test_deleted_devices_not_shown_in_list(self, client, super_admin_user, device, db_session):
        """Удаленные девайсы не показываются в списке."""
        with client.application.app_context():
            from da.models import Device as DeviceModel
            dev = db_session.query(DeviceModel).first()
            device_id = dev.id
            inventory_number = str(dev.inventory_number)
            # Сбрасываем удаление
            dev.deleted_at = None
            db_session.commit()
    
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
        
        response_text = response.data.decode('utf-8')
        # Проверяем отсутствие ссылки на редактирование этого девайса
        assert f"/devices/{device_id}/edit" not in response_text

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
        
        response = client.post(url_for("employees.delete_employee", employee_id=employee_id), follow_redirects=True)
        assert response.status_code == 200
        assert "нельзя удалить" in response.data.decode('utf-8').lower()

    def test_cannot_delete_warehouse_with_devices(self, client, admin_user, warehouse, device, db_session):
        """Нельзя удалить склад, если на нем есть девайсы."""
        with client.application.app_context():
            from da.models import Device as DeviceModel, Warehouse as WarehouseModel
            dev = db_session.query(DeviceModel).filter(DeviceModel.inventory_number == "INV-001").first()
            wh = db_session.query(WarehouseModel).filter(WarehouseModel.name == "Main Warehouse").first()
            dev.warehouse_id = wh.id
            # Сбрасываем владельца, чтобы девайс был на складе
            dev.owner_id = None
            db_session.commit()
            warehouse_id = wh.id
        
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        response = client.post(url_for("warehouses.delete_warehouse", warehouse_id=warehouse_id), follow_redirects=True)
        assert response.status_code == 200
        assert "нельзя удалить" in response.data.decode('utf-8').lower()

    def test_cannot_delete_device_type_with_devices(self, client, admin_user, device_type, device, db_session):
        """Нельзя удалить тип девайса, если к нему привязаны девайсы."""
        with client.application.app_context():
            from da.models import Device as DeviceModel, DeviceType as DeviceTypeModel
            dev = db_session.query(DeviceModel).filter(DeviceModel.inventory_number == "INV-001").first()
            dt = db_session.query(DeviceTypeModel).filter(DeviceTypeModel.name == "Laptop").first()
            dev.type_id = dt.id
            db_session.commit()
            type_id = dt.id
        
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        # Пытаемся удалить тип девайса
        response = client.post(url_for("device_types.delete_device_type", device_type_id=type_id), follow_redirects=True)
        assert response.status_code == 200
        assert "нельзя удалить" in response.data.decode('utf-8').lower()
        
        # Проверяем, что тип не удален
        with client.application.app_context():
            # Получаем заново, чтобы проверить статус
            dt = db_session.query(DeviceTypeModel).get(type_id)
            assert dt is not None
            assert dt.deleted_at is None

    def test_deleted_list_only_visible_to_super_admin(self, client, regular_user, admin_user, super_admin_user):
        """Список удаленных объектов доступен только супер-админу."""
        # Обычный пользователь
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("deleted.list_deleted"))
        assert response.status_code == 403
        
        # Админ
        client.get(url_for("auth.logout"))
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("deleted.list_deleted"))
        assert response.status_code == 403
        
        # Супер-админ
        client.get(url_for("auth.logout"))
        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("deleted.list_deleted"))
        assert response.status_code == 200

    def test_restore_deleted_entity(self, client, super_admin_user, device, db_session):
        """Супер-админ может восстановить удаленную сущность."""
        with client.application.app_context():
            from da.models import Device as DeviceModel
            dev = db_session.query(DeviceModel).filter(DeviceModel.inventory_number == "INV-001").first()
            device_id = dev.id
            inventory_number = str(dev.inventory_number)
            
            # Сначала удаляем мягко (имитируем)
            from da.models import utcnow
            dev.deleted_at = utcnow()
            db_session.commit()
        
        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        response = client.post(url_for("deleted.restore_entity", entity_type="device", entity_id=device_id))
        assert response.status_code == 302
        
        with client.application.app_context():
            from da.models import Device as DeviceModel
            dev = db_session.query(DeviceModel).get(device_id)
            assert dev.deleted_at is None

    def test_permanent_delete_entity(self, client, super_admin_user, device, db_session):
        """Супер-админ может удалить сущность навсегда из корзины."""
        with client.application.app_context():
            from da.models import Device as DeviceModel
            dev = db_session.query(DeviceModel).filter(DeviceModel.inventory_number == "INV-001").first()
            device_id = dev.id
            
            # Сначала удаляем мягко
            from da.models import utcnow
            dev.deleted_at = utcnow()
            db_session.commit()
        
        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        response = client.post(url_for("deleted.permanent_delete_entity", entity_type="device", entity_id=device_id))
        assert response.status_code == 302
        
        with client.application.app_context():
            from da.models import Device as DeviceModel
            dev = db_session.query(DeviceModel).get(device_id)
            assert dev is None
