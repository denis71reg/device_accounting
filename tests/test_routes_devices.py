"""Тесты для роутов управления устройствами."""
import pytest
from da.extensions import db
from da.models import Device, DeviceType, Employee, Location, DeviceStatus, Warehouse, AuditLog


class TestDevicesList:
    """Тесты для списка устройств."""

    def test_list_devices_requires_login(self, client):
        """Список устройств требует авторизации."""
        response = client.get("/devices/")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_list_devices_accessible_by_all_roles(
        self, logged_in_user, logged_in_admin, logged_in_super_admin, app
    ):
        """Список устройств доступен всем авторизованным пользователям."""
        with app.app_context():
            device_type = DeviceType(name="Laptop")
            location = Location(name="Test Location")
            db.session.add_all([device_type, location])
            db.session.commit()

            device = Device(
                inventory_number="INV-001",
                model="MacBook Pro",
                type_id=device_type.id,
                location_id=location.id,
            )
            db.session.add(device)
            db.session.commit()

        for client in [logged_in_user, logged_in_admin, logged_in_super_admin]:
            response = client.get("/devices/")
            assert response.status_code == 200
            assert b"INV-001" in response.data


class TestCreateDevice:
    """Тесты для создания устройств."""

    def test_create_device_requires_admin(self, logged_in_user, app):
        """Создание устройства требует прав администратора."""
        with app.app_context():
            device_type = DeviceType(name="Laptop")
            location = Location(name="Test Location")
            db.session.add_all([device_type, location])
            db.session.commit()

        response = logged_in_user.post(
            "/devices/create",
            data={
                "inventory_number": "INV-002",
                "model": "MacBook Air",
                "type_id": 1,
                "location_id": 1,
            },
        )
        assert response.status_code == 403

    def test_create_device_by_admin(self, logged_in_admin, app):
        """Администратор может создавать устройства."""
        with app.app_context():
            device_type = DeviceType(name="Laptop")
            location = Location(name="Test Location")
            db.session.add_all([device_type, location])
            db.session.flush()
            warehouse = Warehouse(name="Test Warehouse", location_id=location.id)
            db.session.add(warehouse)
            db.session.commit()
            type_id = device_type.id
            warehouse_id = warehouse.id

        response = logged_in_admin.post(
            "/devices/create",
            data={
                "inventory_number": "INV-003",
                "model": "MacBook Air",
                "type_id": type_id,
                "warehouse_id": warehouse_id,
                "owner_id": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            device = Device.query.filter_by(inventory_number="INV-003").first()
            assert device is not None
            assert device.model == "MacBook Air"
            assert device.status == DeviceStatus.IN_STOCK


class TestEditDevice:
    """Тесты для редактирования устройств."""

    def test_edit_device_requires_admin(self, logged_in_user, app):
        """Редактирование требует прав администратора."""
        with app.app_context():
            device_type = DeviceType(name="Laptop")
            location = Location(name="Test Location")
            db.session.add_all([device_type, location])
            db.session.flush()  # Получаем ID перед созданием устройства
            device = Device(
                inventory_number="INV-004",
                model="MacBook Pro",
                type_id=device_type.id,
                location_id=location.id,
            )
            db.session.add(device)
            db.session.commit()
            device_id = device.id

        response = logged_in_user.get(f"/devices/{device_id}/edit")
        assert response.status_code == 403

    def test_edit_device_by_admin(self, logged_in_admin, app):
        """Администратор может редактировать устройства."""
        with app.app_context():
            device_type = DeviceType(name="Laptop")
            location = Location(name="Test Location")
            db.session.add_all([device_type, location])
            db.session.flush()  # Получаем ID перед созданием устройства
            device = Device(
                inventory_number="INV-005",
                model="MacBook Pro",
                type_id=device_type.id,
                location_id=location.id,
            )
            db.session.add(device)
            db.session.commit()
            device_id = device.id
            type_id = device_type.id
            location_id = location.id

        response = logged_in_admin.post(
            f"/devices/{device_id}/edit",
            data={
                "inventory_number": "INV-005",
                "model": "MacBook Pro M2",
                "type_id": type_id,
                "location_id": location_id,
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            device = Device.query.get(device_id)
            assert device.model == "MacBook Pro M2"


class TestDeleteDevice:
    """Тесты для удаления устройств."""

    def test_delete_device_requires_admin(self, logged_in_user, app):
        """Удаление требует прав администратора."""
        with app.app_context():
            device_type = DeviceType(name="Laptop")
            location = Location(name="Test Location")
            db.session.add_all([device_type, location])
            db.session.flush()  # Получаем ID перед созданием устройства
            device = Device(
                inventory_number="INV-006",
                model="MacBook Pro",
                type_id=device_type.id,
                location_id=location.id,
            )
            db.session.add(device)
            db.session.commit()
            device_id = device.id

        response = logged_in_user.post(f"/devices/{device_id}/delete")
        assert response.status_code == 403

    def test_delete_device_by_admin(self, logged_in_admin, app):
        """Администратор может удалять устройства (soft delete)."""
        with app.app_context():
            device_type = DeviceType(name="Laptop")
            location = Location(name="Test Location")
            db.session.add_all([device_type, location])
            db.session.flush()  # Получаем ID перед созданием устройства
            device = Device(
                inventory_number="INV-007",
                model="MacBook Pro",
                type_id=device_type.id,
                location_id=location.id,
            )
            db.session.add(device)
            db.session.commit()
            device_id = device.id

        response = logged_in_admin.post(
            f"/devices/{device_id}/delete", follow_redirects=True
        )
        assert response.status_code == 200

        with app.app_context():
            device = db.session.get(Device, device_id)
            assert device.deleted_at is not None


class TestDeviceTransfer:
    """Тесты для перемещения устройств."""

    def test_transfer_to_warehouse(self, logged_in_admin, app):
        """Перемещение девайса на склад через форму редактирования."""
        with app.app_context():
            device_type = DeviceType(name="Laptop")
            location = Location(name="Test Location")
            db.session.add_all([device_type, location])
            db.session.flush()
            warehouse = Warehouse(name="Main Warehouse", location_id=location.id)
            db.session.add(warehouse)
            db.session.commit()

            device = Device(
                inventory_number="INV-001",
                model="MacBook Pro",
                type_id=device_type.id,
                location_id=location.id,
            )
            db.session.add(device)
            db.session.commit()
            device_id = device.id
            type_id = device_type.id
            loc_id = location.id
            wh_id = warehouse.id

        response = logged_in_admin.post(
            f"/devices/{device_id}/edit",
            data={
                "inventory_number": "INV-001",
                "model": "MacBook Pro",
                "type_id": type_id,
                "location_id": loc_id,
                "warehouse_id": wh_id,
                "owner_id": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            device = Device.query.get(device_id)
            assert device.warehouse_id == warehouse.id
            assert device.owner_id is None
            assert device.status == DeviceStatus.IN_STOCK

    def test_transfer_to_employee(self, logged_in_admin, app):
        """Перемещение девайса сотруднику через форму редактирования."""
        with app.app_context():
            device_type = DeviceType(name="Laptop")
            location = Location(name="Test Location")
            db.session.add_all([device_type, location])
            db.session.flush()
            employee = Employee(
                first_name="Test",
                last_name="Employee",
                position="Developer",
                email="test@ittest-team.ru",
                phone="+1234567890",
                location_id=location.id,
            )
            db.session.add(employee)
            db.session.commit()

            device = Device(
                inventory_number="INV-002",
                model="MacBook Pro",
                type_id=device_type.id,
                location_id=location.id,
            )
            db.session.add(device)
            db.session.commit()
            device_id = device.id
            type_id = device_type.id
            loc_id = location.id
            emp_id = employee.id

        response = logged_in_admin.post(
            f"/devices/{device_id}/edit",
            data={
                "inventory_number": "INV-002",
                "model": "MacBook Pro",
                "type_id": type_id,
                "location_id": loc_id,
                "warehouse_id": "",
                "owner_id": emp_id,
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            device = Device.query.get(device_id)
            assert device.owner_id == employee.id
            assert device.warehouse_id is None
            assert device.status == DeviceStatus.ASSIGNED


class TestDeviceHistory:
    """Тесты для истории устройств."""

    def test_device_history_requires_login(self, client, app):
        """Просмотр истории требует авторизации."""
        with app.app_context():
            device_type = DeviceType(name="Laptop")
            location = Location(name="Test Location")
            db.session.add_all([device_type, location])
            db.session.commit()

            device = Device(
                inventory_number="INV-001",
                model="MacBook Pro",
                type_id=device_type.id,
                location_id=location.id,
            )
            db.session.add(device)
            db.session.commit()
            device_id = device.id

        response = client.get(f"/devices/{device_id}/history")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_device_history_shows_audit_logs(self, logged_in_admin, app):
        """История показывает записи из AuditLog."""
        from da.models import User

        with app.app_context():
            device_type = DeviceType(name="Laptop")
            location = Location(name="Test Location")
            db.session.add_all([device_type, location])
            db.session.commit()

            device = Device(
                inventory_number="INV-001",
                model="MacBook Pro",
                type_id=device_type.id,
                location_id=location.id,
            )
            db.session.add(device)
            db.session.commit()
            device_id = device.id

            # Получаем первого пользователя из базы (admin из фикстуры)
            user = User.query.first()
            assert user is not None, "Пользователь должен существовать из фикстуры"

            # Создаем запись в AuditLog
            from da.models import AuditAction
            audit_log = AuditLog(
                user_id=user.id,
                action=AuditAction.CREATE,
                entity_type="device",
                entity_id=device_id,
                entity_name="INV-001",
                changes='{"model": "MacBook Pro"}',
            )
            db.session.add(audit_log)
            db.session.commit()

        response = logged_in_admin.get(f"/devices/{device_id}/history")
        assert response.status_code == 200
        assert b"INV-001" in response.data
        assert "История действий".encode('utf-8') in response.data

