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






