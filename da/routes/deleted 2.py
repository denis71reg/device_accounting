import logging

from flask import Blueprint, render_template, url_for
from flask_login import login_required

from ..extensions import db
from ..models import Device, DeviceType, Employee, Location, Warehouse
from ..utils import super_admin_required

deleted_bp = Blueprint("deleted", __name__, template_folder="../templates")
logger = logging.getLogger(__name__)


@deleted_bp.get("/")
@super_admin_required
def list_deleted():
    """Список всех удаленных объектов (только для супер-админа)"""
    # Получаем все удаленные объекты
    deleted_devices = Device.query.filter(Device.deleted_at.isnot(None)).order_by(Device.deleted_at.desc()).all()
    deleted_employees = Employee.query.filter(Employee.deleted_at.isnot(None)).order_by(Employee.deleted_at.desc()).all()
    deleted_warehouses = Warehouse.query.filter(Warehouse.deleted_at.isnot(None)).order_by(Warehouse.deleted_at.desc()).all()
    deleted_locations = Location.query.filter(Location.deleted_at.isnot(None)).order_by(Location.deleted_at.desc()).all()
    deleted_device_types = DeviceType.query.filter(DeviceType.deleted_at.isnot(None)).order_by(DeviceType.deleted_at.desc()).all()
    
    return render_template(
        "deleted/list.html",
        deleted_devices=deleted_devices,
        deleted_employees=deleted_employees,
        deleted_warehouses=deleted_warehouses,
        deleted_locations=deleted_locations,
        deleted_device_types=deleted_device_types,
    )


@deleted_bp.post("/restore/<entity_type>/<int:entity_id>")
@super_admin_required
def restore_entity(entity_type: str, entity_id: int):
    """Восстановление удаленного объекта"""
    from flask import flash, redirect
    
    entity_map = {
        "device": Device,
        "employee": Employee,
        "warehouse": Warehouse,
        "location": Location,
        "device_type": DeviceType,
    }
    
    if entity_type not in entity_map:
        flash("Неизвестный тип объекта", "danger")
        return redirect(url_for("deleted.list_deleted"))
    
    model = entity_map[entity_type]
    entity = model.query.get_or_404(entity_id)
    
    if not entity.deleted_at:
        flash("Объект не был удален", "warning")
        return redirect(url_for("deleted.list_deleted"))
    
    entity.deleted_at = None
    db.session.commit()
    
    entity_name = getattr(entity, "name", None) or getattr(entity, "full_name", None) or getattr(entity, "inventory_number", None) or str(entity_id)
    flash(f"{entity_type} '{entity_name}' восстановлен", "success")
    logger.info("Восстановлен %s %s (%s)", entity_type, entity_id, entity_name)
    return redirect(url_for("deleted.list_deleted"))


@deleted_bp.post("/permanent-delete/<entity_type>/<int:entity_id>")
@super_admin_required
def permanent_delete_entity(entity_type: str, entity_id: int):
    """Окончательное удаление объекта (только для супер-админа)"""
    from flask import flash, redirect
    
    entity_map = {
        "device": Device,
        "employee": Employee,
        "warehouse": Warehouse,
        "location": Location,
        "device_type": DeviceType,
    }
    
    if entity_type not in entity_map:
        flash("Неизвестный тип объекта", "danger")
        return redirect(url_for("deleted.list_deleted"))
    
    model = entity_map[entity_type]
    entity = model.query.get_or_404(entity_id)
    
    if not entity.deleted_at:
        flash("Объект не был удален, используйте обычное удаление", "warning")
        return redirect(url_for("deleted.list_deleted"))
    
    entity_name = getattr(entity, "name", None) or getattr(entity, "full_name", None) or getattr(entity, "inventory_number", None) or str(entity_id)
    
    # Используем hard_delete_entity для отправки уведомления и удаления
    from ..services.soft_delete import hard_delete_entity
    from flask_login import current_user
    deleted_by_email = current_user.email if current_user.is_authenticated else "system"
    success, message = hard_delete_entity(entity, entity_type, entity_name, deleted_by_email)
    
    flash(message, "success")
    logger.info("Окончательно удален %s %s (%s)", entity_type, entity_id, entity_name)
    return redirect(url_for("deleted.list_deleted"))

