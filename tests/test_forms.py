"""Тесты для форм и валидации."""
import pytest
from da.forms import LoginForm, RegistrationForm
from da.models import User
from da.extensions import db


class TestLoginForm:
    """Тесты для формы входа."""

    def test_login_form_valid(self, app):
        """Валидная форма входа."""
        with app.app_context():
            form = LoginForm(data={
                "email": "test@ittest-team.ru",
                "password": "TestPassword123!",
            })
            assert form.validate()

    def test_login_form_missing_email(self, app):
        """Форма входа требует email."""
        with app.app_context():
            form = LoginForm(data={
                "password": "TestPassword123!",
            })
            assert not form.validate()

    def test_login_form_missing_password(self, app):
        """Форма входа требует пароль."""
        with app.app_context():
            form = LoginForm(data={
                "email": "test@ittest-team.ru",
            })
            assert not form.validate()


class TestRegistrationForm:
    """Тесты для формы регистрации."""

    def test_registration_form_valid(self, app):
        """Валидная форма регистрации."""
        with app.app_context():
            form = RegistrationForm(data={
                "email": "newuser@ittest-team.ru",
                "first_name": "New",
                "last_name": "User",
                "middle_name": "",
                "phone": "+7700000000",
                "telegram": "@newuser",
                "password": "TestPassword123!",
                "password_confirm": "TestPassword123!",
            })
            assert form.validate()

    def test_registration_form_invalid_domain(self, app):
        """Форма регистрации отклоняет неверный домен."""
        with app.app_context():
            form = RegistrationForm(data={
                "email": "user@gmail.com",
                "first_name": "New",
                "last_name": "User",
                "middle_name": "",
                "phone": "+7700000000",
                "telegram": "@newuser",
                "password": "TestPassword123!",
                "password_confirm": "TestPassword123!",
            })
            assert not form.validate()
            assert "ittest-team.ru" in str(form.email.errors[0]).lower()

    def test_registration_form_password_mismatch(self, app):
        """Форма регистрации требует совпадения паролей."""
        with app.app_context():
            form = RegistrationForm(data={
                "email": "newuser@ittest-team.ru",
                "first_name": "New",
                "last_name": "User",
                "middle_name": "",
                "phone": "+7700000000",
                "telegram": "@newuser",
                "password": "TestPassword123!",
                "password_confirm": "DifferentPassword123!",
            })
            assert not form.validate()

    def test_registration_form_missing_fields(self, app):
        """Форма регистрации требует все поля."""
        with app.app_context():
            form = RegistrationForm(data={
                "email": "newuser@ittest-team.ru",
            })
            assert not form.validate()

