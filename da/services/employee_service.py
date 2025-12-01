import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import AuditAction, Device, Employee
from ..utils import get_or_create_location
from .audit import log_action

logger = logging.getLogger(__name__)


class EmployeeService:
    """Сервис для управления сотрудниками."""

    @staticmethod
    def normalize_email(value: str) -> str:
        return (value or "").strip().lower()

    @staticmethod
    def normalize_phone(value: str) -> str:
        return (value or "").strip()

    @staticmethod
    def normalize_telegram(value: str | None) -> str | None:
        if not value:
            return None
        sanitized = value.strip()
        if not sanitized:
            return None
        if not sanitized.startswith("@"):
            sanitized = f"@{sanitized}"
        return sanitized.lower()

    @staticmethod
    def has_duplicate(field: str, value: str | None, exclude_id: int | None = None) -> bool:
        if not value:
            return False
        column = getattr(Employee, field)
        query = Employee.query.filter(func.lower(column) == value.lower())
        if exclude_id is not None:
            query = query.filter(Employee.id != exclude_id)
        return db.session.query(query.exists()).scalar()

    @staticmethod
    def has_duplicate_name(first_name: str, last_name: str, middle_name: str | None, exclude_id: int | None = None) -> bool:
        """Проверяет, существует ли сотрудник с такой комбинацией ФИО."""
        query = Employee.query.filter(
            func.lower(Employee.first_name) == first_name.lower(),
            func.lower(Employee.last_name) == last_name.lower(),
        )
        if middle_name:
            query = query.filter(func.lower(Employee.middle_name) == middle_name.lower())
        else:
            query = query.filter(Employee.middle_name.is_(None))
        if exclude_id is not None:
            query = query.filter(Employee.id != exclude_id)
        return db.session.query(query.exists()).scalar()

    @classmethod
    def create_employee(cls, data: dict) -> Employee:
        """
        Создает нового сотрудника.
        
        Args:
            data: Словарь с данными сотрудника
            
        Returns:
            Employee: Созданный сотрудник
            
        Raises:
            ValueError: Если данные невалидны или дублируются
        """
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        middle_name = data.get("middle_name", "").strip() or None
        position = data.get("position", "").strip()
        email = cls.normalize_email(data.get("email"))
        phone = cls.normalize_phone(data.get("phone"))
        telegram = cls.normalize_telegram(data.get("telegram"))
        location_name = data.get("location_name", "").strip()

        if not first_name or not last_name:
            raise ValueError("Имя и фамилия обязательны")
        
        if not location_name:
            raise ValueError("Локация обязательна для сотрудника")

        # Ищем или создаем локацию
        location = get_or_create_location(location_name)
        location_id = location.id

        # Проверка дубликатов
        errors = []
        if cls.has_duplicate_name(first_name, last_name, middle_name):
            errors.append("Сотрудник с таким ФИО уже существует")
        if cls.has_duplicate("email", email):
            errors.append("Сотрудник с таким email уже существует")
        if cls.has_duplicate("phone", phone):
            errors.append("Сотрудник с таким телефоном уже существует")
        if telegram and cls.has_duplicate("telegram", telegram):
            errors.append("Сотрудник с таким Telegram уже существует")
        
        if errors:
            raise ValueError("\n".join(errors))

        employee = Employee(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            position=position,
            email=email,
            phone=phone,
            telegram=telegram,
            location_id=location_id,
        )
        db.session.add(employee)
        
        try:
            db.session.commit()
            log_action(
                AuditAction.CREATE,
                "employee",
                entity_id=employee.id,
                entity_name=employee.full_name,
                changes={"email": employee.email, "position": employee.position},
            )
            logger.info("Создан сотрудник %s (%s)", employee.full_name, employee.email)
            return employee
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Сотрудник с такими данными уже существует (конфликт в БД)")

    @classmethod
    def update_employee(cls, employee: Employee, data: dict) -> Employee:
        """
        Обновляет данные сотрудника.
        
        Args:
            employee: Объект сотрудника
            data: Словарь с новыми данными
            
        Returns:
            Employee: Обновленный сотрудник
            
        Raises:
            ValueError: Если данные невалидны или дублируются
        """
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        middle_name = data.get("middle_name", "").strip() or None
        position = data.get("position", "").strip()
        email = cls.normalize_email(data.get("email"))
        phone = cls.normalize_phone(data.get("phone"))
        telegram = cls.normalize_telegram(data.get("telegram"))
        location_name = data.get("location_name", "").strip()

        if not first_name or not last_name:
            raise ValueError("Имя и фамилия обязательны")
        
        if not location_name:
            raise ValueError("Локация обязательна для сотрудника")

        # Ищем или создаем локацию
        location = get_or_create_location(location_name)
        location_id = location.id

        # Проверка дубликатов
        errors = []
        if cls.has_duplicate_name(first_name, last_name, middle_name, exclude_id=employee.id):
            errors.append("Сотрудник с таким ФИО уже существует")
        if cls.has_duplicate("email", email, exclude_id=employee.id):
            errors.append("Сотрудник с таким email уже существует")
        if cls.has_duplicate("phone", phone, exclude_id=employee.id):
            errors.append("Сотрудник с таким телефоном уже существует")
        if telegram and cls.has_duplicate("telegram", telegram, exclude_id=employee.id):
            errors.append("Сотрудник с таким Telegram уже существует")
        
        if errors:
            raise ValueError("\n".join(errors))

        old_data = {
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "middle_name": employee.middle_name,
            "position": employee.position,
            "email": employee.email,
            "phone": employee.phone,
            "telegram": employee.telegram,
            "location_id": employee.location_id,
        }

        employee.first_name = first_name
        employee.last_name = last_name
        employee.middle_name = middle_name
        employee.position = position
        employee.email = email
        employee.phone = phone
        employee.telegram = telegram
        employee.location_id = location_id

        try:
            db.session.commit()
            changes = {
                k: {"old": old_data.get(k), "new": getattr(employee, k)}
                for k in old_data
                if old_data.get(k) != getattr(employee, k)
            }
            if changes:
                log_action(
                    AuditAction.UPDATE,
                    "employee",
                    entity_id=employee.id,
                    entity_name=employee.full_name,
                    changes=changes,
                )
            logger.info("Обновлены данные сотрудника %s", employee.full_name)
            return employee
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Ошибка уникальности данных при обновлении")

    @classmethod
    def import_from_excel(cls, file_content: bytes) -> tuple[int, int, list[str]]:
        """
        Импортирует сотрудников из Excel.
        
        Returns:
            tuple: (imported_count, skipped_count, errors_list)
        """
        import openpyxl
        from io import BytesIO
        
        wb = openpyxl.load_workbook(BytesIO(file_content))
        ws = wb.active
        
        # Пропускаем заголовок
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        
        imported = 0
        skipped = 0
        errors = []
        
        if not rows:
            return 0, 0, ["Файл пуст или содержит только заголовки"]
            
        for row_num, row in enumerate(rows, start=2):
            if not any(row):
                continue
            
            try:
                # Парсим данные
                last_name = str(row[0]).strip() if row[0] else None
                first_name = str(row[1]).strip() if row[1] else None
                middle_name = str(row[2]).strip() if row[2] and str(row[2]).strip() else None
                position = str(row[3]).strip() if row[3] else None
                email = cls.normalize_email(str(row[4])) if row[4] else None
                phone = cls.normalize_phone(str(row[5])) if row[5] else None
                telegram = cls.normalize_telegram(str(row[6]) if row[6] else None)
                location_name = str(row[7]).strip() if row[7] else None
                
                # Валидация
                row_errors = []
                if not last_name or not first_name:
                    row_errors.append("отсутствуют имя или фамилия")
                if not position:
                    row_errors.append("отсутствует должность")
                if not email:
                    row_errors.append("отсутствует email")
                if not phone:
                    row_errors.append("отсутствует телефон")
                if not location_name:
                    row_errors.append("отсутствует локация")
                
                if row_errors:
                    errors.append(f"Строка {row_num}: " + ", ".join(row_errors))
                    skipped += 1
                    continue
                
                # Проверка дубликатов
                if cls.has_duplicate_name(first_name, last_name, middle_name):
                    errors.append(f"Строка {row_num}: сотрудник {last_name} {first_name} уже существует")
                    skipped += 1
                    continue
                
                if cls.has_duplicate("email", email):
                    errors.append(f"Строка {row_num}: email {email} уже используется")
                    skipped += 1
                    continue
                
                if cls.has_duplicate("phone", phone):
                    errors.append(f"Строка {row_num}: телефон {phone} уже используется")
                    skipped += 1
                    continue
                
                if telegram and cls.has_duplicate("telegram", telegram):
                    errors.append(f"Строка {row_num}: Telegram {telegram} уже используется")
                    skipped += 1
                    continue
                
                # Локация
                try:
                    location = get_or_create_location(location_name)
                except ValueError as e:
                    errors.append(f"Строка {row_num}: {str(e)}")
                    skipped += 1
                    continue
                
                # Создание
                employee = Employee(
                    first_name=first_name,
                    last_name=last_name,
                    middle_name=middle_name,
                    position=position,
                    email=email,
                    phone=phone,
                    telegram=telegram,
                    location_id=location.id,
                )
                
                db.session.add(employee)
                db.session.flush() # Чтобы получить ID
                
                log_action(
                    AuditAction.CREATE,
                    "employee",
                    entity_id=employee.id,
                    entity_name=employee.full_name,
                    changes={"email": email, "position": position, "imported": True},
                )
                
                imported += 1
                
            except Exception as e:
                errors.append(f"Строка {row_num}: ошибка обработки - {str(e)}")
                skipped += 1
                logger.exception("Ошибка импорта сотрудника из строки %s", row_num)
                continue
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Ошибка коммита при импорте сотрудников: %s", str(e))
            raise ValueError(f"Ошибка сохранения данных: {str(e)}")
            
        return imported, skipped, errors

