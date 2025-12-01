from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        default=None, nullable=True
    )


class Location(TimestampMixin, db.Model):
    """Локации сотрудников (города, где они живут)"""
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)

    devices: Mapped[list["Device"]] = relationship("Device", back_populates="location")
    employees: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="location"
    )
    warehouses: Mapped[list["Warehouse"]] = relationship("Warehouse")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Location {self.name}>"


class Warehouse(TimestampMixin, db.Model):
    """Склады, где хранятся девайсы"""
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    address: Mapped[str | None] = mapped_column(nullable=True)
    location_id: Mapped[int] = mapped_column(
        db.ForeignKey("locations.id"), nullable=False
    )

    location: Mapped[Optional["Location"]] = relationship("Location", overlaps="warehouses")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="warehouse")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Warehouse {self.name}>"


class DeviceType(TimestampMixin, db.Model):
    __tablename__ = "device_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)

    devices: Mapped[list["Device"]] = relationship("Device", back_populates="type")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DeviceType {self.name}>"


class Employee(TimestampMixin, db.Model):
    __tablename__ = "employees"
    __table_args__ = (
        db.UniqueConstraint('first_name', 'last_name', 'middle_name', name='uq_employees_name'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    middle_name: Mapped[str | None] = mapped_column(nullable=True)
    position: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(nullable=False, unique=True)
    telegram: Mapped[str | None] = mapped_column(nullable=True, unique=True)
    location_id: Mapped[int] = mapped_column(
        db.ForeignKey("locations.id"), nullable=False
    )

    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="employees")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="owner")

    @property
    def full_name(self) -> str:
        """Формирует полное ФИО из отдельных полей."""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)

    @full_name.setter
    def full_name(self, value: str) -> None:
        """Позволяет присваивать ФИО одной строкой (для обратной совместимости)."""
        if not value:
            raise ValueError("Поле full_name не может быть пустым")
        parts = [part for part in value.strip().split() if part]
        if len(parts) < 2:
            raise ValueError("ФИО должно содержать минимум фамилию и имя")
        self.last_name = parts[0]
        self.first_name = parts[1]
        self.middle_name = " ".join(parts[2:]) if len(parts) > 2 else None

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Employee {self.full_name}>"


class DeviceStatus(enum.Enum):
    IN_STOCK = "in_stock"
    ASSIGNED = "assigned"
    RETIRED = "retired"


class Device(TimestampMixin, db.Model):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_number: Mapped[str] = mapped_column(unique=True, nullable=False)
    model: Mapped[str] = mapped_column(nullable=False)
    serial_number: Mapped[str | None]
    type_id: Mapped[int] = mapped_column(db.ForeignKey("device_types.id"), nullable=False)
    warehouse_id: Mapped[int | None] = mapped_column(db.ForeignKey("warehouses.id"), nullable=True)
    location_id: Mapped[int | None] = mapped_column(db.ForeignKey("locations.id"), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(db.ForeignKey("employees.id"), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(DeviceStatus), nullable=False, default=DeviceStatus.IN_STOCK
    )
    notes: Mapped[str | None]

    type: Mapped["DeviceType"] = relationship("DeviceType", back_populates="devices")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse", back_populates="devices")
    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="devices")
    owner: Mapped[Optional["Employee"]] = relationship("Employee", back_populates="devices")
    history_records: Mapped[list["DeviceHistory"]] = relationship(
        "DeviceHistory", back_populates="device", cascade="all, delete-orphan"
    )

    __table_args__ = (CheckConstraint("inventory_number != ''"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Device {self.inventory_number}>"


class HistoryEvent(enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    ASSIGNED = "assigned"
    RETURNED = "returned"
    TRANSFERRED = "transferred"
    RETIRED = "retired"
    DELETED = "deleted"


class DeviceHistory(db.Model):
    __tablename__ = "device_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(db.ForeignKey("devices.id"), nullable=False)
    event: Mapped[str] = mapped_column(Enum(HistoryEvent), nullable=False)
    note: Mapped[str | None]
    from_location: Mapped[str | None]
    to_location: Mapped[str | None]
    actor: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="history_records")


class UserRole(enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    full_name: Mapped[str] = mapped_column(nullable=False)
    phone: Mapped[str | None] = mapped_column(nullable=True)
    telegram: Mapped[str | None] = mapped_column(nullable=True)
    role: Mapped[str] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.USER
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", foreign_keys="AuditLog.user_id"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email}>"

    def check_password(self, password: str) -> bool:
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def set_password(self, password: str) -> None:
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)

    @property
    def can_delete(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN


class AuditAction(enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ASSIGN = "assign"
    RETURN = "return"
    TRANSFER = "transfer"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(Enum(AuditAction), nullable=False)
    entity_type: Mapped[str] = mapped_column(nullable=False)  # 'device', 'employee', 'location', etc.
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    entity_name: Mapped[str | None] = mapped_column(nullable=True)  # For deleted entities
    changes: Mapped[str | None] = mapped_column(nullable=True)  # JSON string of changes
    ip_address: Mapped[str | None] = mapped_column(nullable=True)
    user_agent: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.action.value} {self.entity_type} by {self.user.email}>"

