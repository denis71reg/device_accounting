import logging
from typing import Any, Dict, List, Optional, Tuple

from ..extensions import db
from ..models import AuditAction, Device, Location, Warehouse
from ..services.audit import log_action
from ..services.delete_handler import handle_entity_deletion

logger = logging.getLogger(__name__)


class WarehouseService:
    @staticmethod
    def get_all_warehouses_with_counts() -> List[Any]:
        """Возвращает список складов с количеством девайсов."""
        from sqlalchemy import func
        
        warehouses_query = (
            db.session.query(
                Warehouse,
                func.count(Device.id).label('device_count')
            )
            .filter(Warehouse.deleted_at.is_(None))
            .outerjoin(Device, (Device.warehouse_id == Warehouse.id) & (Device.deleted_at.is_(None)))
            .group_by(Warehouse.id)
            .order_by(Warehouse.name)
        )
        return warehouses_query.all()

    @staticmethod
    def create_warehouse(name: str, location_name: str) -> Tuple[Optional[Warehouse], Optional[str]]:
        """
        Создает новый склад.
        Возвращает кортеж (warehouse, error_message).
        """
        from ..utils import get_or_create_location
        
        if not location_name:
            return None, "Локация обязательна"
            
        try:
            location = get_or_create_location(location_name)
        except ValueError as e:
            return None, str(e)
            
        warehouse = Warehouse(name=name, location_id=location.id)
        db.session.add(warehouse)
        
        try:
            db.session.commit()
            log_action(
                AuditAction.CREATE,
                "warehouse",
                entity_id=warehouse.id,
                entity_name=warehouse.name,
                changes={"name": warehouse.name, "location_name": location.name},
            )
            logger.info("Создан склад %s (%s)", warehouse.name, warehouse.id)
            return warehouse, None
        except Exception as e:
            db.session.rollback()
            logger.warning("Ошибка создания склада: %s", str(e))
            return None, "Склад с таким названием уже существует"

    @staticmethod
    def update_warehouse(warehouse: Warehouse, name: str, location_name: str) -> Tuple[bool, Optional[str]]:
        """
        Обновляет склад.
        Возвращает кортеж (success, error_message).
        """
        if not location_name:
            return False, "Локация обязательна"

        old_data = {
            "name": warehouse.name,
            "location_name": warehouse.location.name if warehouse.location else None,
        }
        
        # Ищем или создаем локацию
        location = Location.query.filter_by(name=location_name).first()
        if not location:
            location = Location(name=location_name)
            db.session.add(location)
            db.session.flush()
            logger.info("Создана новая локация: %s", location_name)
            
        warehouse.name = name
        warehouse.location_id = location.id
        
        try:
            db.session.commit()
            
            changes = {
                "name": {"old": old_data.get("name"), "new": warehouse.name},
                "location_name": {"old": old_data.get("location_name"), "new": location.name},
            }
            # Убираем неизмененные поля
            changes = {k: v for k, v in changes.items() if v["old"] != v["new"]}
            
            if changes:
                log_action(
                    AuditAction.UPDATE,
                    "warehouse",
                    entity_id=warehouse.id,
                    entity_name=warehouse.name,
                    changes=changes,
                )
                
            logger.info("Обновлён склад %s (%s)", warehouse.name, warehouse.id)
            return True, None
        except Exception as e:
            db.session.rollback()
            logger.warning("Ошибка обновления склада %s: %s", warehouse.id, str(e))
            return False, "Склад с таким названием уже существует"

    @staticmethod
    def delete_warehouse(warehouse: Warehouse) -> Tuple[bool, str]:
        """
        Удаляет склад (soft delete).
        """
        # Проверяем, есть ли у склада привязанные девайсы (только не удаленные)
        devices_count = Device.query.filter_by(warehouse_id=warehouse.id).filter(Device.deleted_at.is_(None)).count()
        if devices_count > 0:
            logger.warning("Попытка удаления склада %s с привязанными девайсами (%s шт.)", warehouse.name, devices_count)
            return False, f"Нельзя удалить склад, пока к нему привязаны устройства ({devices_count} шт.)"
        
        success, message = handle_entity_deletion(warehouse, "warehouse", warehouse.name)
        return success, message

