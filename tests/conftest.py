import pytest

from da import create_app
from da.extensions import db
from da.models import DeviceType, Location, User, UserRole, Warehouse


@pytest.fixture
def app():
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def seed_basics(app):
    """Создаёт базовые локации и типы для тестов."""
    with app.app_context():
        location = Location(name="Test Location")
        device_type = DeviceType(name="Laptop")
        warehouse = Warehouse(name="Main Warehouse", location_id=None)
        db.session.add(location)
        db.session.flush()
        warehouse.location_id = location.id
        db.session.add_all([device_type, warehouse])
        db.session.commit()
        return {
            "location_id": location.id,
            "device_type_id": device_type.id,
            "warehouse_id": warehouse.id,
        }


@pytest.fixture
def location(app, seed_basics):
    """Создаёт локацию для тестов."""
    with app.app_context():
        return Location.query.get(seed_basics["location_id"])


@pytest.fixture
def device_type(app, seed_basics):
    """Создаёт тип девайса для тестов."""
    with app.app_context():
        return DeviceType.query.get(seed_basics["device_type_id"])


@pytest.fixture
def warehouse(app, seed_basics):
    """Создаёт склад для тестов."""
    with app.app_context():
        return Warehouse.query.get(seed_basics["warehouse_id"])


@pytest.fixture
def employee(app, location):
    """Создаёт сотрудника для тестов."""
    from da.models import Employee
    with app.app_context():
        emp = Employee(
            first_name="Test",
            last_name="Employee",
            middle_name=None,
            position="Developer",
            email="employee@ittest-team.ru",
            phone="+79991234567",
            location_id=location.id,
        )
        db.session.add(emp)
        db.session.commit()
        return emp


@pytest.fixture
def device(app, device_type, location, warehouse):
    """Создаёт девайс для тестов."""
    from da.models import Device, DeviceStatus
    with app.app_context():
        dev = Device(
            inventory_number="INV-001",
            model="Test Device",
            type_id=device_type.id,
            location_id=location.id,
            warehouse_id=warehouse.id,
            status=DeviceStatus.IN_STOCK,
        )
        db.session.add(dev)
        db.session.commit()
        return dev


@pytest.fixture
def db_session(app):
    """Фикстура для доступа к сессии БД."""
    with app.app_context():
        yield db.session


@pytest.fixture
def super_admin_user(app):
    """Создаёт супер-администратора для тестов."""
    with app.app_context():
        user = User(
            email="superadmin@ittest-team.ru",
            full_name="Super Admin",
            role=UserRole.SUPER_ADMIN,
        )
        user.set_password("TestPassword123!")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def admin_user(app):
    """Создаёт администратора для тестов."""
    with app.app_context():
        user = User(
            email="admin@ittest-team.ru",
            full_name="Admin User",
            role=UserRole.ADMIN,
        )
        user.set_password("TestPassword123!")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def regular_user(app):
    """Создаёт обычного пользователя для тестов."""
    with app.app_context():
        user = User(
            email="user@ittest-team.ru",
            full_name="Regular User",
            role=UserRole.USER,
        )
        user.set_password("TestPassword123!")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def logged_in_super_admin(app, super_admin_user):
    """Авторизует супер-администратора и возвращает отдельный клиент."""
    client = app.test_client()
    client.post(
        "/auth/login",
        data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!",
        },
        follow_redirects=True,
    )
    return client


@pytest.fixture
def logged_in_admin(app, admin_user):
    """Авторизует администратора и возвращает отдельный клиент."""
    client = app.test_client()
    client.post(
        "/auth/login",
        data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!",
        },
        follow_redirects=True,
    )
    return client


@pytest.fixture
def logged_in_user(app, regular_user):
    """Авторизует обычного пользователя и возвращает отдельный клиент."""
    client = app.test_client()
    client.post(
        "/auth/login",
        data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!",
        },
        follow_redirects=True,
    )
    return client

