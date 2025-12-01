"""Тесты для просмотра девайсов сотрудника."""
import pytest
from da.extensions import db
from da.models import Device, DeviceType, Employee, Location, Warehouse, DeviceStatus


class TestEmployeeDevices:
    """Тесты для просмотра девайсов сотрудника."""

    def test_employee_devices_requires_login(self, client, app):
        """Просмотр девайсов требует авторизации."""
        with app.app_context():
            location = Location(name="Test Location")
            db.session.add(location)
            db.session.flush()
            employee = Employee(
                first_name="Test",
                last_name="Employee",
                position="QA",
                email="test@ittest-team.ru",
                phone="+7700000000",
                location_id=location.id,
            )
            db.session.add(employee)
            db.session.commit()
            employee_id = employee.id

        response = client.get(f"/employees/{employee_id}/devices")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_employee_devices_accessible_by_all_roles(
        self, logged_in_user, logged_in_admin, logged_in_super_admin, app
    ):
        """Просмотр девайсов доступен всем авторизованным пользователям."""
        with app.app_context():
            location = Location(name="Test Location")
            device_type = DeviceType(name="Laptop")
            db.session.add_all([location, device_type])
            db.session.flush()
            warehouse = Warehouse(name="Main Warehouse", location_id=location.id)
            employee = Employee(
                first_name="Test",
                last_name="Employee",
                position="QA",
                email="test@ittest-team.ru",
                phone="+7700000000",
                location_id=location.id,
            )
            db.session.add_all([warehouse, employee])
            db.session.commit()

            device = Device(
                inventory_number="INV-001",
                model="MacBook Pro",
                type_id=device_type.id,
                warehouse_id=warehouse.id,
                owner_id=employee.id,
                status=DeviceStatus.ASSIGNED,
            )
            db.session.add(device)
            db.session.commit()
            employee_id = employee.id

        for client in [logged_in_user, logged_in_admin, logged_in_super_admin]:
            response = client.get(f"/employees/{employee_id}/devices")
            assert response.status_code == 200
            assert b"Employee Test" in response.data or b"Test Employee" in response.data
            assert b"INV-001" in response.data

    def test_employee_devices_empty_list(self, logged_in_user, app):
        """Отображение пустого списка девайсов."""
        with app.app_context():
            location = Location(name="Test Location")
            db.session.add(location)
            db.session.flush()
            employee = Employee(
                first_name="Test",
                last_name="Employee",
                position="QA",
                email="test@ittest-team.ru",
                phone="+7700000000",
                location_id=location.id,
            )
            db.session.add(employee)
            db.session.commit()
            employee_id = employee.id

        response = logged_in_user.get(f"/employees/{employee_id}/devices")
        assert response.status_code == 200
        assert b"Employee Test" in response.data or b"Test Employee" in response.data
        assert "нет назначенных девайсов".encode('utf-8') in response.data

    def test_employee_devices_shows_count(self, logged_in_user, app):
        """Отображается правильное количество девайсов."""
        with app.app_context():
            location = Location(name="Test Location")
            device_type = DeviceType(name="Laptop")
            db.session.add_all([location, device_type])
            db.session.flush()
            warehouse = Warehouse(name="Main Warehouse", location_id=location.id)
            employee = Employee(
                first_name="Test",
                last_name="Employee",
                position="QA",
                email="test@ittest-team.ru",
                phone="+7700000000",
                location_id=location.id,
            )
            db.session.add_all([warehouse, employee])
            db.session.commit()

            # Создаем 3 девайса
            for i in range(3):
                device = Device(
                    inventory_number=f"INV-00{i+1}",
                    model=f"Device {i+1}",
                    type_id=device_type.id,
                    warehouse_id=warehouse.id,
                    owner_id=employee.id,
                    status=DeviceStatus.ASSIGNED,
                )
                db.session.add(device)
            db.session.commit()
            employee_id = employee.id

        response = logged_in_user.get(f"/employees/{employee_id}/devices")
        assert response.status_code == 200
        # Проверяем, что отображается количество
        assert "Список девайсов (3)".encode('utf-8') in response.data

