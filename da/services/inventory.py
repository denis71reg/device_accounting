from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from flask import current_app

from ..extensions import db
from ..models import (
    AuditAction,
    Device,
    DeviceHistory,
    DeviceStatus,
    DeviceType,
    Employee,
    HistoryEvent,
    Location,
    Warehouse,
)
from .audit import log_action

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
        # Используем старый логгер для совместимости, если нужно, но лучше переходить на AuditLog
        # InventoryService._log(device, HistoryEvent.CREATED, "Девайс добавлен")
        db.session.commit()
        logger.info("Создан девайс %s (%s)", device.inventory_number, device.id)
        return device

    @staticmethod
    def update_device(device: Device, **fields) -> Device:
        for key, value in fields.items():
            setattr(device, key, value)
        # InventoryService._log(device, HistoryEvent.UPDATED, "Обновлены данные устройства")
        db.session.commit()
        logger.info("Обновлён девайс %s (%s)", device.inventory_number, device.id)
        return device

    @staticmethod
    def delete_device(device: Device) -> None:
        # InventoryService._log(device, HistoryEvent.DELETED, "Девайс удален")
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
        """
        Deprecated: Используйте log_action из services.audit
        Оставлено для обратной совместимости, если где-то используется старая история
        """
        history = DeviceHistory(
            device=device,
            event=event,
            note=note,
            from_location=device.location.name if device.location else None,
            actor=device.owner.full_name if device.owner else None,
        )
        db.session.add(history)

    @staticmethod
    def update_device_and_transfer(
        device: Device,
        updated_fields: dict[str, Any],
        warehouse_id: int | str | None = None,
        owner_id: int | str | None = None,
    ) -> None:
        """
        Обновляет данные девайса и обрабатывает перемещение между складами/сотрудниками.
        """
        # 1. Обновляем основные поля
        InventoryService.update_device(device, **updated_fields)
        
        # 2. Обрабатываем перемещение
        if not warehouse_id and not owner_id:
            # Если ничего не выбрано, проверяем текущее состояние
            # Если у девайса уже есть склад или сотрудник, оставляем как есть
            # Если нет - выбрасываем ошибку (или оставляем на совести контроллера, но тут жесткая проверка)
            # В оригинале было: if not device.warehouse_id and not device.owner_id: flash error
            # Здесь просто выходим, если ничего не передано, предполагая что изменений трансфера нет
            return

        # Валидация: нельзя выбрать и то, и другое
        if warehouse_id and owner_id:
             raise ValueError("Нельзя одновременно выбрать склад и сотрудника")

        transfer_changes = {}
        
        # Перемещение на склад
        if warehouse_id:
            warehouse = Warehouse.query.get(int(warehouse_id))
            if not warehouse:
                 raise ValueError(f"Склад {warehouse_id} не найден")
                 
            old_owner = device.owner
            old_warehouse = device.warehouse
            old_location = device.location
            
            # Пропускаем, если девайс уже на этом складе
            if device.warehouse_id == warehouse.id:
                return

            device.warehouse = warehouse
            device.owner = None
            device.location = warehouse.location
            device.status = DeviceStatus.IN_STOCK
            
            transfer_changes["warehouse"] = {
                "old": old_warehouse.name if old_warehouse else None,
                "new": warehouse.name,
            }
            transfer_changes["location"] = {
                "old": old_location.name if old_location else None,
                "new": warehouse.location.name,
            }
            if old_owner:
                transfer_changes["owner"] = {
                    "old": old_owner.full_name,
                    "new": None,
                }
                
            log_action(
                AuditAction.TRANSFER,
                "device",
                entity_id=device.id,
                entity_name=device.inventory_number,
                changes={
                    **transfer_changes,
                    "action": "Перемещен на склад",
                    "warehouse_name": warehouse.name,
                },
            )

        # Перемещение сотруднику
        elif owner_id:
            employee = Employee.query.get(int(owner_id))
            if not employee:
                raise ValueError(f"Сотрудник {owner_id} не найден")
            
            # Пропускаем, если девайс уже у этого сотрудника
            if device.owner_id == employee.id:
                return

            old_owner = device.owner
            old_warehouse = device.warehouse
            old_location = device.location
            
            device.owner = employee
            device.warehouse = None
            device.location = employee.location
            device.status = DeviceStatus.ASSIGNED
            
            transfer_changes["owner"] = {
                "old": old_owner.full_name if old_owner else None,
                "new": employee.full_name,
            }
            transfer_changes["location"] = {
                "old": old_location.name if old_location else None,
                "new": employee.location.name,
            }
            if old_warehouse:
                transfer_changes["warehouse"] = {
                    "old": old_warehouse.name,
                    "new": None,
                }
                
            log_action(
                AuditAction.ASSIGN,
                "device",
                entity_id=device.id,
                entity_name=device.inventory_number,
                changes={
                    **transfer_changes,
                    "action": "Выдан сотруднику",
                    "employee_name": employee.full_name,
                },
            )
            
        db.session.commit()

    @staticmethod
    def import_devices_from_excel(file_content: bytes) -> Dict[str, Any]:
        """
        Импортирует девайсы из Excel файла.
        Возвращает словарь со статистикой: {'imported': int, 'skipped': int, 'errors': List[str]}
        """
        wb = openpyxl.load_workbook(BytesIO(file_content))
        ws = wb.active
        
        # Пропускаем заголовок (первая строка)
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        
        result = {
            'imported': 0,
            'skipped': 0,
            'errors': []
        }
        
        if not rows:
            return result
        
        for row_num, row in enumerate(rows, start=2):
            # Пропускаем пустые строки
            if not any(row):
                continue
            
            try:
                # Парсим данные из строки
                # Ожидаемые колонки: Инвентарный номер, Модель, Тип, Серийный номер, Склад/Сотрудник, Локация, Примечания
                inventory_number = str(row[0]).strip() if row[0] else None
                model = str(row[1]).strip() if row[1] else None
                type_name = str(row[2]).strip() if row[2] else None
                serial_number = str(row[3]).strip() if row[3] else None
                owner_or_warehouse = str(row[4]).strip() if row[4] else None
                location_name = str(row[5]).strip() if row[5] else None
                notes = str(row[6]).strip() if row[6] else None
                
                # Валидация обязательных полей
                if not inventory_number:
                    result['errors'].append(f"Строка {row_num}: отсутствует инвентарный номер")
                    result['skipped'] += 1
                    continue
                
                if not model:
                    result['errors'].append(f"Строка {row_num}: отсутствует модель")
                    result['skipped'] += 1
                    continue
                
                if not type_name:
                    result['errors'].append(f"Строка {row_num}: отсутствует тип девайса")
                    result['skipped'] += 1
                    continue
                
                # Проверка дубликата инвентарного номера
                if Device.query.filter_by(inventory_number=inventory_number).filter(Device.deleted_at.is_(None)).first():
                    result['errors'].append(f"Строка {row_num}: девайс с инвентарным номером {inventory_number} уже существует")
                    result['skipped'] += 1
                    continue
                
                # Находим тип девайса
                device_type = DeviceType.query.filter(DeviceType.name.ilike(type_name)).filter(DeviceType.deleted_at.is_(None)).first()
                if not device_type:
                    result['errors'].append(f"Строка {row_num}: тип девайса '{type_name}' не найден")
                    result['skipped'] += 1
                    continue
                
                # Определяем локацию и владельца/склад
                location_id = None
                warehouse_id = None
                owner_id = None
                status = DeviceStatus.IN_STOCK
                
                if location_name:
                    location = Location.query.filter(Location.name.ilike(location_name)).filter(Location.deleted_at.is_(None)).first()
                    if location:
                        location_id = location.id
                    else:
                        result['errors'].append(f"Строка {row_num}: локация '{location_name}' не найдена")
                        result['skipped'] += 1
                        continue
                
                if owner_or_warehouse:
                    # Пробуем найти сотрудника по ФИО
                    name_parts = owner_or_warehouse.strip().split()
                    if len(name_parts) >= 2:
                        last_name = name_parts[0]
                        first_name = name_parts[1]
                        
                        query = Employee.query.filter(
                            Employee.last_name.ilike(last_name),
                            Employee.first_name.ilike(first_name)
                        ).filter(Employee.deleted_at.is_(None))
                        
                        employee = query.first()
                        
                        if employee:
                            owner_id = employee.id
                            if not location_id:
                                location_id = employee.location_id
                            status = DeviceStatus.ASSIGNED
                        else:
                            # Пробуем найти склад
                            warehouse = Warehouse.query.filter(Warehouse.name.ilike(owner_or_warehouse)).filter(Warehouse.deleted_at.is_(None)).first()
                            if warehouse:
                                warehouse_id = warehouse.id
                                if not location_id:
                                    location_id = warehouse.location_id
                                status = DeviceStatus.IN_STOCK
                            else:
                                result['errors'].append(f"Строка {row_num}: не найден сотрудник или склад '{owner_or_warehouse}'")
                                result['skipped'] += 1
                                continue
                    else:
                        # Пробуем найти склад
                        warehouse = Warehouse.query.filter(Warehouse.name.ilike(owner_or_warehouse)).filter(Warehouse.deleted_at.is_(None)).first()
                        if warehouse:
                            warehouse_id = warehouse.id
                            if not location_id:
                                location_id = warehouse.location_id
                            status = DeviceStatus.IN_STOCK
                        else:
                            result['errors'].append(f"Строка {row_num}: не найден склад '{owner_or_warehouse}'")
                            result['skipped'] += 1
                            continue
                
                if not location_id:
                    result['errors'].append(f"Строка {row_num}: не удалось определить локацию")
                    result['skipped'] += 1
                    continue
                
                # Создаем девайс
                device = Device(
                    inventory_number=inventory_number,
                    model=model,
                    type_id=device_type.id,
                    serial_number=serial_number if serial_number else None,
                    warehouse_id=warehouse_id,
                    owner_id=owner_id,
                    location_id=location_id,
                    status=status,
                    notes=notes,
                )
                
                db.session.add(device)
                db.session.flush()
                
                log_action(
                    AuditAction.CREATE,
                    "device",
                    entity_id=device.id,
                    entity_name=device.inventory_number,
                    changes={"model": model, "type_id": device_type.id, "imported": True},
                )
                
                result['imported'] += 1
                
            except Exception as e:
                result['errors'].append(f"Строка {row_num}: ошибка обработки - {str(e)}")
                result['skipped'] += 1
                logger.exception("Ошибка импорта девайса из строки %s", row_num)
                continue
        
        # Коммитим все изменения
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
            
        return result
