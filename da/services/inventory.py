from __future__ import annotations

from dataclasses import dataclass
import logging

from flask import current_app

from ..extensions import db
from ..models import (
    Device,
    DeviceHistory,
    DeviceStatus,
    HistoryEvent,
    Location,
    Employee,
    DeviceType,
    Warehouse,
)

logger = logging.getLogger(__name__)


@dataclass
class InventoryService:
    @staticmethod
    def create_device(
        inventory_number: str,
        model: str,
        type_id: int,
        location_id: int | None = None,
        serial_number: str | None = None,
        notes: str | None = None,
    ) -> Device:
        device = Device(
            inventory_number=inventory_number.strip(),
            model=model.strip(),
            type_id=type_id,
            location_id=location_id,
            serial_number=serial_number.strip() if serial_number else None,
            notes=notes,
        )
        db.session.add(device)
        db.session.flush()
        InventoryService._log(device, HistoryEvent.CREATED, "Девайс добавлен")
        db.session.commit()
        logger.info("Создан девайс %s (%s)", device.inventory_number, device.id)
        return device

    @staticmethod
    def update_device(device: Device, **fields) -> Device:
        for key, value in fields.items():
            setattr(device, key, value)
        InventoryService._log(device, HistoryEvent.UPDATED, "Обновлены данные устройства")
        db.session.commit()
        logger.info("Обновлён девайс %s (%s)", device.inventory_number, device.id)
        return device

    @staticmethod
    def delete_device(device: Device) -> None:
        InventoryService._log(device, HistoryEvent.DELETED, "Девайс удален")
        db.session.delete(device)
        db.session.commit()
        logger.info("Удалён девайс %s (%s)", device.inventory_number, device.id)

    @staticmethod
    def seed_defaults() -> None:
        for name in current_app.config["DEFAULT_LOCATIONS"]:
            db.session.merge(Location(name=name))
        for name in current_app.config["DEFAULT_DEVICE_TYPES"]:
            db.session.merge(DeviceType(name=name))
        db.session.commit()
        logger.info("Базовые локации и типы девайсов синхронизированы")

    @staticmethod
    def _log(device: Device, event: HistoryEvent, note: str | None = None) -> None:
        history = DeviceHistory(
            device=device,
            event=event,
            note=note,
            from_location=device.location.name if device.location else None,
            actor=device.owner.full_name if device.owner else None,
        )
        db.session.add(history)
        logger.debug(
            "История: девайс=%s событие=%s комментарий=%s",
            device.inventory_number,
            event.value,
            note,
        )

    @staticmethod
    def import_devices_from_excel(file_stream) -> dict:
        import openpyxl

        wb = openpyxl.load_workbook(file_stream)
        sheet = wb.active

        created = 0
        updated = 0
        errors = []

        # Пропускаем заголовок
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            try:
                # Ожидаем колонки:
                # 0: Inv Number, 1: Model, 2: Type, 3: Location, 4: Serial, 5: Notes, 6: Employee
                if not row[0]:  # Пропускаем пустые строки
                    continue

                inv_num = str(row[0]).strip()
                model = str(row[1]).strip() if len(row) > 1 and row[1] else "Unknown Model"
                type_name = str(row[2]).strip() if len(row) > 2 and row[2] else "Other"
                loc_name = str(row[3]).strip() if len(row) > 3 and row[3] else "Склад"
                serial = str(row[4]).strip() if len(row) > 4 and row[4] else None
                notes = str(row[5]).strip() if len(row) > 5 and row[5] else None
                emp_name = str(row[6]).strip() if len(row) > 6 and row[6] else None

                # Находим или создаем тип и локацию
                dtype = DeviceType.query.filter_by(name=type_name).first()
                if not dtype:
                    dtype = DeviceType(name=type_name)
                    db.session.add(dtype)

                location = Location.query.filter_by(name=loc_name).first()
                if not location:
                    location = Location(name=loc_name)
                    db.session.add(location)

                # Ищем сотрудника, если указан
                owner = None
                if emp_name:
                    # Пробуем найти по email или имени
                    owner = Employee.query.filter(
                        (Employee.email == emp_name) | (Employee.full_name == emp_name)
                    ).first()

                # Ищем существующий девайс
                device = Device.query.filter_by(inventory_number=inv_num).first()

                if device:
                    device.model = model
                    device.type = dtype
                    device.serial_number = serial
                    device.notes = notes
                    
                    if owner:
                        device.owner = owner
                        device.location_id = None
                    elif location:
                        device.location = location
                        # Если переносим на локацию и сотрудника в файле нет, 
                        # то оставляем владельца как есть? Или снимаем?
                        # Для безопасности: если колонка сотрудника пустая, владельца НЕ трогаем.
                        # Только если явно указана локация Склад и нет владельца?
                        pass

                    updated += 1
                    InventoryService._log(device, HistoryEvent.UPDATED, "Импорт из Excel")
                else:
                    device = Device(
                        inventory_number=inv_num,
                        model=model,
                        type_id=dtype.id,
                        location_id=location.id if not owner else None,
                        owner_id=owner.id if owner else None,
                        serial_number=serial,
                        notes=notes
                    )
                    db.session.add(device)
                    created += 1
                    InventoryService._log(device, HistoryEvent.CREATED, "Импорт из Excel")

                db.session.flush()

            except Exception as e:
                errors.append(f"Строка {row_idx}: {str(e)}")
                logger.error(f"Ошибка импорта строки {row_idx}: {e}")

        db.session.commit()
        return {"created": created, "updated": updated, "errors": errors}






