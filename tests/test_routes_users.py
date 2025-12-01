"""Тесты для управления пользователями и ролями."""
import pytest
from flask import url_for

from da.models import User, UserRole


class TestUserManagement:
    """Тесты управления пользователями."""

    def test_list_users_requires_super_admin(self, client, app):
        """Только супер-админ может просматривать список пользователей."""
        with app.app_context():
            from da.models import User, UserRole
            from da.extensions import db
            
            # Создаем пользователей
            regular = User(email="user@ittest-team.ru", full_name="User", role=UserRole.USER)
            regular.set_password("pass")
            
            admin = User(email="super@ittest-team.ru", full_name="Super", role=UserRole.SUPER_ADMIN)
            admin.set_password("pass")
            
            db.session.add_all([regular, admin])
            db.session.commit()

        # Обычный пользователь
        client.post(url_for("auth.login"), data={"email": "user@ittest-team.ru", "password": "pass"})
        response = client.get(url_for("users.list_users"))
        assert response.status_code == 403

        # Выходим
        client.get(url_for("auth.logout"))

        # Супер-админ
        login_resp = client.post(url_for("auth.login"), data={"email": "super@ittest-team.ru", "password": "pass"}, follow_redirects=True)
        print(f"Login response: {login_resp.status_code}, data: {login_resp.data[:100]}")
        
        response = client.get(url_for("users.list_users"))
        print(f"List users response: {response.status_code}")
        assert response.status_code == 200
        assert "Пользователи".encode('utf-8') in response.data

    def test_set_user_role_requires_super_admin(self, client, app):
        """Только супер-админ может менять роли пользователей."""
        with app.app_context():
            from da.models import User, UserRole
            from da.extensions import db
            
            regular = User(email="user@ittest-team.ru", full_name="User", role=UserRole.USER)
            regular.set_password("pass")
            
            admin = User(email="admin@ittest-team.ru", full_name="Admin", role=UserRole.ADMIN)
            admin.set_password("pass")
            
            super_admin = User(email="super@ittest-team.ru", full_name="Super", role=UserRole.SUPER_ADMIN)
            super_admin.set_password("pass")
            
            db.session.add_all([regular, admin, super_admin])
            db.session.commit()
            
            regular_user_id = regular.id

        # Админ не может менять роли
        client.post(url_for("auth.login"), data={"email": "admin@ittest-team.ru", "password": "pass"})
        
        response = client.post(
            url_for("users.set_user_role", user_id=regular_user_id),
            data={"role": "admin"}
        )
        assert response.status_code == 403

        # Выходим
        client.get(url_for("auth.logout"))

        # Супер-админ может менять роли
        client.post(url_for("auth.login"), data={"email": "super@ittest-team.ru", "password": "pass"})
        
        response = client.post(
            url_for("users.set_user_role", user_id=regular_user_id),
            data={"role": "admin"}
        )
        assert response.status_code == 302  # Redirect
        
        # Обновляем объект из БД
        with app.app_context():
            from da.models import User, UserRole
            updated_user = User.query.get(regular_user_id)
            assert updated_user.role == UserRole.ADMIN

    def test_set_user_role_invalid_role(self, client, app, super_admin_user, regular_user):
        """Нельзя установить несуществующую роль."""
        client.post(url_for("auth.login"), data={
            "email": "superadmin@ittest-team.ru",
            "password": "TestPassword123!"
        })
        with app.app_context():
            from da.models import User
            regular_user_obj = User.query.filter_by(email="user@ittest-team.ru").first()
            regular_user_id = regular_user_obj.id
            old_role = regular_user_obj.role
        
        response = client.post(
            url_for("users.set_user_role", user_id=regular_user_id),
            data={"role": "invalid_role"}
        )
        assert response.status_code == 302
        # Роль не должна измениться
        with app.app_context():
            from da.models import User
            updated_user = User.query.get(regular_user_id)
            assert updated_user.role == old_role

    def test_new_user_defaults_to_user_role(self, client, app, db_session):
        """Новые пользователи по умолчанию получают роль USER."""
        # Создаем пользователя через регистрацию
        with app.app_context():
            from da.models import User
            # Убеждаемся, что есть хотя бы один пользователь (чтобы новый не стал супер-админом)
            if User.query.count() == 0:
                first_user = User(email="first@ittest-team.ru", full_name="First", role=UserRole.SUPER_ADMIN)
                first_user.set_password("TestPassword123!")
                db_session.add(first_user)
                db_session.commit()
        
        response = client.post(url_for("auth.register"), data={
            "email": "newuser@ittest-team.ru",
            "first_name": "New",
            "last_name": "User",
            "middle_name": "",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!",
            "phone": "+79991234567",
        })
        assert response.status_code == 302

        with app.app_context():
            user = User.query.filter_by(email="newuser@ittest-team.ru").first()
            assert user is not None
            assert user.role == UserRole.USER

    def test_first_user_becomes_super_admin(self, client, app, db_session):
        """Первый зарегистрированный пользователь становится супер-админом."""
        with app.app_context():
            from da.models import User
            # Удаляем всех существующих пользователей
            User.query.delete()
            db_session.commit()

        # Регистрируем первого пользователя
        response = client.post(url_for("auth.register"), data={
            "email": "first@ittest-team.ru",
            "first_name": "First",
            "last_name": "User",
            "middle_name": "",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!",
            "phone": "+79991234567",
        })
        assert response.status_code == 302

        with app.app_context():
            user = User.query.filter_by(email="first@ittest-team.ru").first()
            assert user is not None
            assert user.role == UserRole.SUPER_ADMIN

