"""Тесты для email уведомлений об удалении."""
import pytest
from unittest.mock import patch, MagicMock
from flask import url_for

from da.models import Device, DeviceType, Employee, Location, UserRole, Warehouse
from da.services.email import send_deletion_notification
from da.extensions import db


class TestEmailNotifications:
    """Тесты email уведомлений."""

    @patch('da.services.email.smtplib.SMTP_SSL')
    @patch('da.services.email.current_app')
    def test_send_deletion_notification_success(self, mock_app, mock_smtp_ssl, app, super_admin_user):
        """Тест успешной отправки email уведомления."""
        with app.app_context():
            # Настраиваем моки
            mock_app.config = {
                "SMTP_HOST": "mail.ittest-team.ru",
                "SMTP_PORT": 465,
                "SMTP_USER": "da@ittest-team.ru",
                "SMTP_PASSWORD": "test-password",
            }
            
            # Мокаем SMTP сервер
            mock_server = MagicMock()
            mock_smtp_ssl.return_value = mock_server
            
            # Вызываем функцию
            result = send_deletion_notification(
                entity_type="device",
                entity_name="Test Device",
                deleted_by="admin@ittest-team.ru",
                is_soft_delete=True,
            )
            
            # Проверяем результат
            assert result is True
            mock_smtp_ssl.assert_called_once_with("mail.ittest-team.ru", 465)
            mock_server.login.assert_called_once_with("da@ittest-team.ru", "test-password")
            mock_server.send_message.assert_called_once()
            mock_server.quit.assert_called_once()

    @patch('da.services.email.current_app')
    def test_send_deletion_notification_missing_smtp_config(self, mock_app, app):
        """Тест отправки уведомления без настроек SMTP."""
        with app.app_context():
            mock_app.config = {
                "SMTP_HOST": None,
                "SMTP_PORT": 465,
                "SMTP_USER": "da@ittest-team.ru",
                "SMTP_PASSWORD": "test-password",
            }
            
            result = send_deletion_notification(
                entity_type="device",
                entity_name="Test Device",
                deleted_by="admin@ittest-team.ru",
                is_soft_delete=True,
            )
            
            assert result is False

    @patch('da.services.email.current_app')
    def test_send_deletion_notification_no_super_admin(self, mock_app, app):
        """Тест отправки уведомления когда нет супер-админа."""
        with app.app_context():
            # Удаляем всех супер-админов
            from da.models import User, UserRole
            User.query.filter_by(role=UserRole.SUPER_ADMIN).delete()
            from da.extensions import db
            db.session.commit()
            
            mock_app.config = {
                "SMTP_HOST": "mail.ittest-team.ru",
                "SMTP_PORT": 465,
                "SMTP_USER": "da@ittest-team.ru",
                "SMTP_PASSWORD": "test-password",
            }
            
            result = send_deletion_notification(
                entity_type="device",
                entity_name="Test Device",
                deleted_by="admin@ittest-team.ru",
                is_soft_delete=True,
            )
            
            assert result is False

    @patch('da.services.email.smtplib.SMTP_SSL')
    @patch('da.services.email.current_app')
    def test_send_deletion_notification_smtp_error(self, mock_app, mock_smtp_ssl, app, super_admin_user):
        """Тест обработки ошибки SMTP."""
        with app.app_context():
            mock_app.config = {
                "SMTP_HOST": "mail.ittest-team.ru",
                "SMTP_PORT": 465,
                "SMTP_USER": "da@ittest-team.ru",
                "SMTP_PASSWORD": "test-password",
            }
            
            # Мокаем ошибку SMTP
            mock_server = MagicMock()
            mock_server.login.side_effect = Exception("SMTP authentication failed")
            mock_smtp_ssl.return_value = mock_server
            
            result = send_deletion_notification(
                entity_type="device",
                entity_name="Test Device",
                deleted_by="admin@ittest-team.ru",
                is_soft_delete=True,
            )
            
            assert result is False

    @patch('da.services.email.smtplib.SMTP')
    @patch('da.services.email.current_app')
    def test_send_deletion_notification_port_587(self, mock_app, mock_smtp, app, super_admin_user):
        """Тест отправки уведомления через порт 587 (STARTTLS)."""
        with app.app_context():
            mock_app.config = {
                "SMTP_HOST": "mail.ittest-team.ru",
                "SMTP_PORT": 587,
                "SMTP_USER": "da@ittest-team.ru",
                "SMTP_PASSWORD": "test-password",
            }
            
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            result = send_deletion_notification(
                entity_type="device",
                entity_name="Test Device",
                deleted_by="admin@ittest-team.ru",
                is_soft_delete=False,
            )
            
            assert result is True
            mock_smtp.assert_called_once_with("mail.ittest-team.ru", 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()

    def test_email_notification_on_soft_delete(self, client, app, admin_user, device, db_session):
        """Тест отправки email при мягком удалении девайса админом."""
        from unittest.mock import patch
        
        with patch('da.services.email.send_deletion_notification') as mock_send:
            mock_send.return_value = True
            
            client.post(url_for("auth.login"), data={
                "email": "admin@ittest-team.ru",
                "password": "TestPassword123!"
            })
            
            # Получаем ID девайса в контексте
            with app.app_context():
                device_obj = Device.query.filter(Device.deleted_at.is_(None)).first()
                if not device_obj:
                    # Создаем тестовый девайс
                    from da.models import DeviceType, Location, Warehouse, DeviceStatus
                    location = Location.query.first()
                    device_type = DeviceType.query.first()
                    warehouse = Warehouse.query.first()
                    device_obj = Device(
                        inventory_number="TEST-EMAIL-001",
                        model="Test Device",
                        type_id=device_type.id,
                        location_id=location.id,
                        warehouse_id=warehouse.id,
                        status=DeviceStatus.IN_STOCK,
                    )
                    db.session.add(device_obj)
                    db.session.commit()
                device_id = device_obj.id
            
            response = client.post(url_for("devices.delete_device", device_id=device_id))
            
            assert response.status_code == 302
            # Проверяем, что функция отправки была вызвана
            assert mock_send.called
            # Проверяем, что девайс помечен как удаленный
            with app.app_context():
                deleted_device = Device.query.get(device_id)
                assert deleted_device is not None
                assert deleted_device.deleted_at is not None

    def test_email_notification_on_hard_delete(self, client, app, super_admin_user, device, db_session):
        """Тест отправки email при физическом удалении девайса супер-админом."""
        from unittest.mock import patch
        
        with patch('da.services.email.send_deletion_notification') as mock_send:
            mock_send.return_value = True
            
            client.post(url_for("auth.login"), data={
                "email": "superadmin@ittest-team.ru",
                "password": "TestPassword123!"
            })
            
            # Получаем ID девайса в контексте
            with app.app_context():
                device_obj = Device.query.filter(Device.deleted_at.is_(None)).first()
                if not device_obj:
                    # Создаем тестовый девайс
                    from da.models import DeviceType, Location, Warehouse, DeviceStatus
                    location = Location.query.first()
                    device_type = DeviceType.query.first()
                    warehouse = Warehouse.query.first()
                    device_obj = Device(
                        inventory_number="TEST-EMAIL-002",
                        model="Test Device",
                        type_id=device_type.id,
                        location_id=location.id,
                        warehouse_id=warehouse.id,
                        status=DeviceStatus.IN_STOCK,
                    )
                    db.session.add(device_obj)
                    db.session.commit()
                device_id = device_obj.id
            
            response = client.post(url_for("devices.delete_device", device_id=device_id))
            
            assert response.status_code == 302
            # Проверяем, что функция отправки была вызвана
            assert mock_send.called
            # При физическом удалении девайс должен быть удален из базы
            with app.app_context():
                deleted_device = Device.query.get(device_id)
                assert deleted_device is None
