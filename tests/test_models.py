from da.extensions import db
from da.models import Device, DeviceType, Employee, Location


def test_employee_creation(app):
    with app.app_context():
        location = Location(name="HQ")
        db.session.add(location)
        db.session.flush()

        employee = Employee(
            first_name="Test",
            last_name="User",
            middle_name=None,
            position="QA",
            email="test@ittest-team.ru",
            phone="+7700000000",
            telegram="@testuser",
            location_id=location.id,
        )
        db.session.add(employee)
        db.session.commit()

        saved = Employee.query.filter_by(email="test@ittest-team.ru").one()
        assert saved.first_name == "Test"
        assert saved.last_name == "User"
        assert saved.full_name == "User Test"  # Property формирует "Фамилия Имя"
        assert saved.location.name == "HQ"


def test_device_creation(app):
    with app.app_context():
        location = Location(name="Office")
        device_type = DeviceType(name="Laptop")
        db.session.add_all([location, device_type])
        db.session.flush()

        device = Device(
            inventory_number="INV-1",
            model="MacBook",
            type_id=device_type.id,
            location_id=location.id,
        )
        db.session.add(device)
        db.session.commit()

        saved = Device.query.filter_by(inventory_number="INV-1").one()
        assert saved.model == "MacBook"
        assert saved.location.name == "Office"

