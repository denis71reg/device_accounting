"""Тесты для роутов управления локациями."""
import pytest
from da.extensions import db
from da.models import Location


class TestLocationsList:
    """Тесты для списка локаций."""

    def test_list_locations_requires_login(self, client):
        """Список локаций требует авторизации."""
        response = client.get("/locations/")
        assert response.status_code == 302
        assert "/auth/login" in response.location

    def test_list_locations_accessible_by_all_roles(
        self, logged_in_user, logged_in_admin, logged_in_super_admin, app
    ):
        """Список локаций доступен всем авторизованным пользователям."""
        with app.app_context():
            location = Location(name="Test Location")
            db.session.add(location)
            db.session.commit()

        for client in [logged_in_user, logged_in_admin, logged_in_super_admin]:
            response = client.get("/locations/")
            assert response.status_code == 200
            assert b"Test Location" in response.data


class TestCreateLocation:
    """Тесты для создания локаций."""

    def test_create_location_requires_admin(self, logged_in_user):
        """Создание локации требует прав администратора."""
        response = logged_in_user.post(
            "/locations/create",
            data={"name": "New Location"},
        )
        assert response.status_code == 403

    def test_create_location_by_admin(self, logged_in_admin, app):
        """Администратор может создавать локации."""
        response = logged_in_admin.post(
            "/locations/create",
            data={"name": "New Location"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            location = Location.query.filter_by(name="New Location").first()
            assert location is not None

    def test_create_location_duplicate_name(self, logged_in_admin, app):
        """Нельзя создать локацию с дублирующимся именем."""
        with app.app_context():
            location = Location(name="Duplicate Location")
            db.session.add(location)
            db.session.commit()

        response = logged_in_admin.post(
            "/locations/create",
            data={"name": "Duplicate Location"},
        )
        assert response.status_code == 200
        assert "уже существует".encode('utf-8') in response.data or "уже используется".encode('utf-8') in response.data


class TestEditLocation:
    """Тесты для редактирования локаций."""

    def test_edit_location_requires_admin(self, logged_in_user, app):
        """Редактирование требует прав администратора."""
        with app.app_context():
            location = Location(name="Test Location")
            db.session.add(location)
            db.session.commit()
            location_id = location.id

        response = logged_in_user.get(f"/locations/{location_id}/edit")
        assert response.status_code == 403

    def test_edit_location_by_admin(self, logged_in_admin, app):
        """Администратор может редактировать локации."""
        with app.app_context():
            location = Location(name="Test Location")
            db.session.add(location)
            db.session.commit()
            location_id = location.id

        response = logged_in_admin.post(
            f"/locations/{location_id}/edit",
            data={"name": "Updated Location"},
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            location = Location.query.get(location_id)
            assert location.name == "Updated Location"


class TestDeleteLocation:
    """Тесты для удаления локаций."""

    def test_delete_location_requires_super_admin(self, logged_in_admin, app):
        """Удаление требует прав супер-администратора."""
        with app.app_context():
            location = Location(name="Test Location")
            db.session.add(location)
            db.session.commit()
            location_id = location.id

        response = logged_in_admin.post(f"/locations/{location_id}/delete")
        assert response.status_code == 403

    def test_delete_location_by_super_admin(self, logged_in_super_admin, app):
        """Супер-администратор может удалять локации."""
        with app.app_context():
            location = Location(name="Test Location")
            db.session.add(location)
            db.session.commit()
            location_id = location.id

        response = logged_in_super_admin.post(
            f"/locations/{location_id}/delete", follow_redirects=True
        )
        assert response.status_code == 200

        with app.app_context():
            location = Location.query.get(location_id)
            assert location is None

