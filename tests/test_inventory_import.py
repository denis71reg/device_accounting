import pytest
from io import BytesIO
import openpyxl
from unittest.mock import patch, MagicMock
from da.services import InventoryService
from da.models import Device, DeviceType, Location, Warehouse, Employee, DeviceStatus

@pytest.fixture
def excel_file_factory():
    def _create_excel(rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        # Заголовки
        ws.append(["Инвентарный номер", "Модель", "Тип", "Серийный номер", "Владелец/Склад", "Локация", "Примечания"])
        for row in rows:
            ws.append(row)
        
        out = BytesIO()
        wb.save(out)
        out.seek(0)
        return out.read()
    return _create_excel

class TestInventoryImport:
    
    def test_import_success(self, app, db_session, excel_file_factory, admin_user):
        """Тест успешного импорта девайсов"""
        
        # Подготовка данных
        with app.app_context():
            laptop_type = DeviceType(name="Laptop")
            monitor_type = DeviceType(name="Monitor")
            location = Location(name="Office")
            warehouse = Warehouse(name="Main Warehouse", location=location)
            employee = Employee(first_name="John", last_name="Doe", location=location, position="Developer", email="john@example.com", phone="+79990000000")
            
            db_session.add_all([laptop_type, monitor_type, location, warehouse, employee])
            db_session.commit()
            
            # Создаем Excel
            rows = [
                ["INV-IMP-001", "MacBook Pro", "Laptop", "SN123", "Main Warehouse", "", "Note 1"],
                ["INV-IMP-002", "Dell Monitor", "Monitor", "SN456", "Doe John", "", "Note 2"],
            ]
            file_content = excel_file_factory(rows)
            
            # Мокаем current_user для log_action
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.email = "admin@test.com"
            mock_user.is_authenticated = True
            
            with patch("da.services.audit.current_user", mock_user):
                result = InventoryService.import_devices_from_excel(file_content)
            
            assert result['imported'] == 2
            assert result['skipped'] == 0
            assert len(result['errors']) == 0
            
            # Проверка в БД
            d1 = Device.query.filter_by(inventory_number="INV-IMP-001").first()
            assert d1 is not None
            assert d1.model == "MacBook Pro"
            assert d1.warehouse_id == warehouse.id
            assert d1.status == DeviceStatus.IN_STOCK
            
            d2 = Device.query.filter_by(inventory_number="INV-IMP-002").first()
            assert d2 is not None
            assert d2.model == "Dell Monitor"
            assert d2.owner_id == employee.id
            assert d2.status == DeviceStatus.ASSIGNED

    def test_import_with_errors(self, app, db_session, excel_file_factory, admin_user):
        """Тест импорта с ошибками (дубликаты, нет типа и т.д.)"""
        
        with app.app_context():
            laptop_type = DeviceType(name="Laptop")
            location = Location(name="Office")
            db_session.add_all([laptop_type, location])
            db_session.commit()
            
            # Создаем существующий девайс
            existing_device = Device(
                inventory_number="INV-EXIST", 
                model="Old", 
                type_id=laptop_type.id,
                location_id=location.id
            )
            db_session.add(existing_device)
            db_session.commit()
            
            rows = [
                ["", "No Inv Num", "Laptop", "", "Office", "", ""], # Нет инвентарного
                ["INV-EXIST", "Duplicate", "Laptop", "", "Office", "Office", ""], # Дубликат
                ["INV-NEW", "No Type", "UnknownType", "", "Office", "Office", ""], # Нет типа
                ["INV-OK", "Good Device", "Laptop", "", "", "Office", ""] # OK (только локация)
            ]
            file_content = excel_file_factory(rows)
            
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.email = "admin@test.com"
            mock_user.is_authenticated = True
            
            with patch("da.services.audit.current_user", mock_user):
                result = InventoryService.import_devices_from_excel(file_content)
                
            assert result['imported'] == 1
            assert result['skipped'] == 3
            assert len(result['errors']) == 3
            assert "отсутствует инвентарный номер" in result['errors'][0]
            assert "уже существует" in str(result['errors'][1])
            assert "тип девайса 'UnknownType' не найден" in str(result['errors'][2])
            
            assert Device.query.filter_by(inventory_number="INV-OK").first() is not None


