import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import AuditAction, Location, Warehouse
from ..services.audit import log_action
from ..utils import admin_required, can_delete_required
from ..utils import get_or_create_location

warehouses_bp = Blueprint("warehouses", __name__, template_folder="../templates")
logger = logging.getLogger(__name__)


@warehouses_bp.get("/")
@login_required
def list_warehouses():
    from sqlalchemy import func
    from ..models import Device
    
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
    warehouses_with_counts = warehouses_query.all()
    return render_template("warehouses/list.html", warehouses_with_counts=warehouses_with_counts)


@warehouses_bp.route("/create", methods=["GET", "POST"])
@admin_required
def create_warehouse():
    if request.method == "POST":
        name = request.form["name"].strip()
        location_name = request.form["location_name"].strip()
        
        if not location_name:
            flash("Локация обязательна", "danger")
            return render_template("warehouses/form.html", warehouse=None)
        
        # Ищем или создаем локацию
        try:
            location = get_or_create_location(location_name)
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("warehouses/form.html", warehouse=None)
        
        warehouse = Warehouse(
            name=name,
            location_id=location.id,
        )
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
            flash("Склад добавлен", "success")
            logger.info("Создан склад %s (%s)", warehouse.name, warehouse.id)
            return redirect(url_for("warehouses.list_warehouses"))
        except IntegrityError:
            db.session.rollback()
            flash("Склад с таким названием уже существует", "danger")
            logger.warning("Ошибка создания склада: дубликат %s", name)
    return render_template("warehouses/form.html", warehouse=None)


@warehouses_bp.route("/<int:warehouse_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_warehouse(warehouse_id: int):
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    if request.method == "POST":
        old_data = {
            "name": warehouse.name,
            "location_name": warehouse.location.name if warehouse.location else None,
        }
        location_name = request.form["location_name"].strip()
        
        if not location_name:
            flash("Локация обязательна", "danger")
            return render_template("warehouses/form.html", warehouse=warehouse)
        
        # Ищем или создаем локацию
        location = Location.query.filter_by(name=location_name).first()
        if not location:
            location = Location(name=location_name)
            db.session.add(location)
            db.session.flush()
            logger.info("Создана новая локация: %s", location_name)
        
        warehouse.name = request.form["name"].strip()
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
            flash("Склад обновлен", "success")
            logger.info("Обновлён склад %s (%s)", warehouse.name, warehouse_id)
            return redirect(url_for("warehouses.list_warehouses"))
        except IntegrityError:
            db.session.rollback()
            flash("Склад с таким названием уже существует", "danger")
            logger.warning("Ошибка обновления склада %s: дубликат", warehouse_id)
    return render_template("warehouses/form.html", warehouse=warehouse)


@warehouses_bp.post("/<int:warehouse_id>/delete")
@admin_required
def delete_warehouse(warehouse_id: int):
    from ..models import Device, utcnow
    
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    # Проверяем, есть ли у склада привязанные девайсы (только не удаленные)
    devices_count = Device.query.filter_by(warehouse_id=warehouse_id).filter(Device.deleted_at.is_(None)).count()
    if devices_count > 0:
        flash(f"Нельзя удалить склад, пока к нему привязаны устройства ({devices_count} шт.)", "danger")
        logger.warning("Попытка удаления склада %s с привязанными девайсами (%s шт.)", warehouse.name, devices_count)
        return redirect(url_for("warehouses.list_warehouses"))
    
    from ..services.delete_handler import handle_entity_deletion
    
    success, message = handle_entity_deletion(warehouse, "warehouse", warehouse.name)
    flash(message, "success")
    return redirect(url_for("warehouses.list_warehouses"))


@warehouses_bp.get("/<int:warehouse_id>/devices")
@login_required
def warehouse_devices(warehouse_id: int):
    """Просмотр девайсов склада."""
    from ..models import Device
    
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    devices = (
        Device.query
        .filter_by(warehouse_id=warehouse_id)
        .order_by(Device.created_at.desc())
        .all()
    )
    return render_template(
        "warehouses/devices.html",
        warehouse=warehouse,
        devices=devices,
    )

