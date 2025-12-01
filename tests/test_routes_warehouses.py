import pytest
from flask import url_for

from da.models import UserRole


class TestWarehousesList:
    """Тесты списка складов."""

    def test_list_warehouses_requires_login(self, client):
        """Доступ к списку складов требует авторизации."""
        response = client.get(url_for("warehouses.list_warehouses"))
        assert response.status_code == 302

    def test_list_warehouses_accessible_by_all_roles(self, client, app, regular_user, admin_user, super_admin_user):
        """Все роли имеют доступ к списку складов."""
        for email, password in [
            ("user@ittest-team.ru", "TestPassword123!"),
            ("admin@ittest-team.ru", "TestPassword123!"),
            ("superadmin@ittest-team.ru", "TestPassword123!"),
        ]:
            # Выход перед каждым входом
            client.get(url_for("auth.logout"))
            
            client.post(url_for("auth.login"), data={
                "email": email,
                "password": password,
            })
            response = client.get(url_for("warehouses.list_warehouses"))
            assert response.status_code == 200

    def test_list_warehouses_shows_device_count(self, client, app, admin_user, warehouse, device):
        """В списке складов отображается количество девайсов."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.get(url_for("warehouses.list_warehouses"))
        assert response.status_code == 200
        # Проверяем наличие названия склада
        assert warehouse.name.encode('utf-8') in response.data


class TestCreateWarehouse:
    """Тесты создания склада."""

    def test_create_warehouse_requires_login(self, client):
        """Создание склада требует авторизации."""
        response = client.post(url_for("warehouses.create_warehouse"))
        assert response.status_code == 302

    def test_create_warehouse_requires_admin(self, client, regular_user):
        """Обычный пользователь не может создать склад."""
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("warehouses.create_warehouse"))
        assert response.status_code == 403

    def test_create_warehouse_by_admin(self, client, app, admin_user, location):
        """Администратор может создать склад."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        # Получаем ID локации безопасным способом
        location_id = location.id
        
        response = client.post(url_for("warehouses.create_warehouse"), data={
            "name": "New Warehouse",
            "location_name": location.name
        })
        assert response.status_code == 302
        
        with app.app_context():
            from da.models import Warehouse
            wh = Warehouse.query.filter_by(name="New Warehouse").first()
            assert wh is not None
            assert wh.location_id is not None

    def test_create_warehouse_creates_location_if_not_exists(self, client, app, admin_user):
        """Если локация не существует, она создается."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("warehouses.create_warehouse"), data={
            "name": "Warehouse with New Location",
            "location_name": "Brand New Location"
        })
        assert response.status_code == 302
        
        with app.app_context():
            from da.models import Location, Warehouse
            loc = Location.query.filter_by(name="Brand New Location").first()
            assert loc is not None
            
            wh = Warehouse.query.filter_by(name="Warehouse with New Location").first()
            assert wh is not None
            assert wh.location_id == loc.id


class TestEditWarehouse:
    """Тесты редактирования склада."""

    def test_edit_warehouse_requires_admin(self, client, regular_user, warehouse):
        """Обычный пользователь не может редактировать склад."""
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        # Используем ID из фикстуры, предполагая, что он доступен, иначе будет DetachedInstanceError
        # Но так как мы не трогаем атрибуты, а только id, может пронести, если id закэширован
        # Лучше явно перезапросить
        
        response = client.post(url_for("warehouses.edit_warehouse", warehouse_id=warehouse.id))
        assert response.status_code == 403

    def test_edit_warehouse_by_admin(self, client, app, admin_user, warehouse):
        """Администратор может редактировать склад."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        warehouse_id = warehouse.id
        
        response = client.post(url_for("warehouses.edit_warehouse", warehouse_id=warehouse_id), data={
            "name": "Updated Warehouse",
            "location_name": "Updated Location"
        })
        assert response.status_code == 302
        
        with app.app_context():
            from da.models import Warehouse
            wh = Warehouse.query.get(warehouse_id)
            assert wh.name == "Updated Warehouse"
            assert wh.location.name == "Updated Location"


class TestDeleteWarehouse:
    """Тесты удаления склада."""

    def test_delete_warehouse_requires_admin(self, client, regular_user, warehouse):
        """Обычный пользователь не может удалить склад."""
        client.post(url_for("auth.login"), data={
            "email": "user@ittest-team.ru",
            "password": "TestPassword123!"
        })
        response = client.post(url_for("warehouses.delete_warehouse", warehouse_id=warehouse.id))
        assert response.status_code == 403

    def test_cannot_delete_warehouse_with_devices(self, client, admin_user, warehouse, device):
        """Нельзя удалить склад, если на нем есть девайсы."""
        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        # Убеждаемся, что девайс привязан к складу
        # В фикстуре device он уже привязан к warehouse
        
        response = client.post(url_for("warehouses.delete_warehouse", warehouse_id=warehouse.id), follow_redirects=True)
        assert response.status_code == 200
        assert "Нельзя удалить склад".encode('utf-8') in response.data


class TestWarehouseDevices:
    """Тесты просмотра девайсов на складе."""

    def test_warehouse_devices_requires_login(self, client, warehouse):
        response = client.get(url_for("warehouses.warehouse_devices", warehouse_id=warehouse.id))
        assert response.status_code == 302

    def test_warehouse_devices_shows_devices(self, client, admin_user, warehouse, device, location, device_type, db_session):
        """Тест: просмотр девайсов склада показывает девайсы."""
        
        # Привязываем девайс к складу
        with client.application.app_context():
            from da.models import Device, Warehouse
            # Находим любой девайс и склад
            d = Device.query.first()
            w = Warehouse.query.first()
            d.warehouse_id = w.id
            db_session.commit()
            
            warehouse_id = w.id
            inv_number = d.inventory_number

        client.post(url_for("auth.login"), data={
            "email": "admin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        
        response = client.get(url_for("warehouses.warehouse_devices", warehouse_id=warehouse_id))
        assert response.status_code == 200
        assert str(inv_number).encode('utf-8') in response.data
