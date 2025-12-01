import json
import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import AuditAction, Device, DeviceHistory, DeviceStatus, DeviceType, Employee, Location, Warehouse
from ..services import InventoryService
from ..services.audit import log_action
from ..utils import admin_required, can_delete_required

devices_bp = Blueprint("devices", __name__, template_folder="../templates")
logger = logging.getLogger(__name__)


@devices_bp.get("/")
@login_required
def list_devices():
    from sqlalchemy.orm import joinedload
    devices = (
        Device.query.filter(Device.deleted_at.is_(None))
        .options(
            joinedload(Device.type),
            joinedload(Device.location),
            joinedload(Device.owner),
            joinedload(Device.warehouse)
        )
        .order_by(Device.created_at.desc())
        .all()
    )
    return render_template("devices/list.html", devices=devices)


@devices_bp.route("/create", methods=["GET", "POST"])
@admin_required
def create_device():
    types = DeviceType.query.filter(DeviceType.deleted_at.is_(None)).order_by(DeviceType.name).all()
    locations = Location.query.filter(Location.deleted_at.is_(None)).order_by(Location.name).all()
    warehouses = Warehouse.query.filter(Warehouse.deleted_at.is_(None)).order_by(Warehouse.name).all()
    employees = Employee.query.filter(Employee.deleted_at.is_(None)).order_by(Employee.last_name, Employee.first_name, Employee.middle_name).all()
    if request.method == "POST":
        try:
            # При создании нужно выбрать склад или сотрудника для установки локации
            warehouse_id = request.form.get("warehouse_id")
            owner_id = request.form.get("owner_id")
            location_id = None
            
            # Проверка: нельзя выбрать и склад, и сотрудника одновременно
            if warehouse_id and owner_id:
                flash("Нельзя одновременно выбрать склад и сотрудника. Выберите что-то одно.", "danger")
                return render_template(
                    "devices/form.html",
                    types=types,
                    warehouses=warehouses,
                    employees=employees,
                    device=None,
                )
            
            if warehouse_id:
                warehouse = Warehouse.query.get_or_404(int(warehouse_id))
                location_id = warehouse.location.id  # Локация всегда есть у склада
            elif owner_id:
                employee = Employee.query.get_or_404(int(owner_id))
                location_id = employee.location.id  # Локация всегда есть у сотрудника
            else:
                flash("При создании девайса необходимо выбрать склад или сотрудника для установки локации", "danger")
                return render_template(
                    "devices/form.html",
                    types=types,
                    warehouses=warehouses,
                    employees=employees,
                    device=None,
                )
            
            device = InventoryService.create_device(
                request.form["inventory_number"],
                request.form["model"],
                int(request.form["type_id"]),
                location_id=location_id,
                serial_number=request.form.get("serial_number"),
                notes=request.form.get("notes"),
            )
            
            # Устанавливаем склад или сотрудника
            if warehouse_id:
                device.warehouse_id = int(warehouse_id)
                device.status = DeviceStatus.IN_STOCK
            elif owner_id:
                device.owner_id = int(owner_id)
                device.status = DeviceStatus.ASSIGNED
            db.session.commit()
            
            log_action(
                AuditAction.CREATE,
                "device",
                entity_id=device.id,
                entity_name=device.inventory_number,
                changes={"model": device.model, "type_id": device.type_id},
            )
            flash("Девайс добавлен", "success")
            logger.info("Создан девайс %s (%s)", device.inventory_number, device.id)
            return redirect(url_for("devices.list_devices"))
        except IntegrityError:
            db.session.rollback()
            flash("Инвентарный номер должен быть уникальным", "danger")
            logger.warning("Ошибка создания девайса: дубликат %s", request.form["inventory_number"])
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
            logger.error("Ошибка создания девайса: %s", str(e))
    return render_template(
        "devices/form.html",
        types=types,
        locations=locations,
        warehouses=warehouses,
        employees=employees,
        device=None,
    )


@devices_bp.route("/<int:device_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_device(device_id: int):
    device = Device.query.get_or_404(device_id)
    
    # Исправляем некорректное состояние: если у девайса есть и склад, и сотрудник
    if device.warehouse_id and device.owner_id:
        # Приоритет у сотрудника - убираем склад
        device.warehouse_id = None
        device.status = DeviceStatus.ASSIGNED
        db.session.commit()
        logger.warning("Исправлено некорректное состояние девайса %s: убран склад, оставлен сотрудник", device_id)
    
    types = DeviceType.query.filter(DeviceType.deleted_at.is_(None)).order_by(DeviceType.name).all()
    locations = Location.query.filter(Location.deleted_at.is_(None)).order_by(Location.name).all()
    warehouses = Warehouse.query.filter(Warehouse.deleted_at.is_(None)).order_by(Warehouse.name).all()
    employees = Employee.query.filter(Employee.deleted_at.is_(None)).order_by(Employee.last_name, Employee.first_name, Employee.middle_name).all()
    
    if request.method == "POST":
        old_data = {
            "inventory_number": device.inventory_number,
            "model": device.model,
            "type_id": device.type_id,
            "location_id": device.location_id,
            "warehouse_id": device.warehouse_id,
            "owner_id": device.owner_id,
        }
        try:
            # Формируем словарь полей для обновления
            updated_fields = {
                "inventory_number": request.form["inventory_number"],
                "model": request.form["model"],
                "type_id": int(request.form["type_id"]),
                "serial_number": request.form.get("serial_number"),
                "notes": request.form.get("notes"),
            }
            
            InventoryService.update_device_and_transfer(
                device,
                updated_fields,
                warehouse_id=request.form.get("warehouse_id"),
                owner_id=request.form.get("owner_id")
            )
            
            flash("Девайс обновлен", "success")
            logger.info("Обновлён девайс %s (%s)", device.inventory_number, device_id)
            return redirect(url_for("devices.list_devices"))
            
        except IntegrityError:
            db.session.rollback()
            flash("Инвентарный номер должен быть уникальным", "danger")
            logger.warning("Ошибка обновления девайса %s: дубликат номера", request.form["inventory_number"])
        except ValueError as e:
            db.session.rollback()
            flash(f"Ошибка: {str(e)}", "danger")
            logger.error("Ошибка обновления девайса %s: %s", device_id, str(e))
        except IntegrityError:
            db.session.rollback()
            flash("Инвентарный номер должен быть уникальным", "danger")
            logger.warning("Ошибка обновления девайса %s: дубликат номера", request.form["inventory_number"])
        except ValueError as e:
            db.session.rollback()
            flash(f"Ошибка: {str(e)}", "danger")
            logger.error("Ошибка обновления девайса %s: %s", device_id, str(e))
    
    return render_template(
        "devices/form.html",
        device=device,
        types=types,
        locations=locations,
        warehouses=warehouses,
        employees=employees,
    )


@devices_bp.post("/<int:device_id>/delete")
@admin_required
def delete_device(device_id: int):
    from ..services.delete_handler import handle_entity_deletion
    
    device = Device.query.get_or_404(device_id)
    success, message = handle_entity_deletion(device, "device", device.inventory_number)
    flash(message, "success")
    return redirect(url_for("devices.list_devices"))




@devices_bp.get("/<int:device_id>/history")
@login_required
def device_history(device_id: int):
    from ..models import AuditLog
    device = Device.query.get_or_404(device_id)
    # Получаем все записи из AuditLog для этого девайса
    audit_logs_raw = (
        AuditLog.query.filter_by(entity_type="device", entity_id=device_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    # Парсим JSON изменения для каждого лога
    audit_logs = []
    for log in audit_logs_raw:
        parsed_changes = None
        if log.changes:
            try:
                parsed_changes = json.loads(log.changes)
            except (json.JSONDecodeError, TypeError):
                parsed_changes = log.changes
        audit_logs.append({
            'log': log,
            'changes': parsed_changes,
        })
    return render_template(
        "devices/history.html",
        device=device,
        audit_logs=audit_logs,
    )


@devices_bp.route("/import", methods=["GET", "POST"])
@admin_required
def import_devices():
    """Импорт девайсов из Excel файла."""
    if request.method == "GET":
        types = DeviceType.query.filter(DeviceType.deleted_at.is_(None)).order_by(DeviceType.name).all()
        warehouses = Warehouse.query.filter(Warehouse.deleted_at.is_(None)).order_by(Warehouse.name).all()
        employees = Employee.query.filter(Employee.deleted_at.is_(None)).order_by(Employee.last_name, Employee.first_name, Employee.middle_name).all()
        return render_template("devices/import.html", types=types, warehouses=warehouses, employees=employees)
    
    if "file" not in request.files:
        flash("Файл не выбран", "danger")
        types = DeviceType.query.filter(DeviceType.deleted_at.is_(None)).order_by(DeviceType.name).all()
        warehouses = Warehouse.query.filter(Warehouse.deleted_at.is_(None)).order_by(Warehouse.name).all()
        employees = Employee.query.filter(Employee.deleted_at.is_(None)).order_by(Employee.last_name, Employee.first_name, Employee.middle_name).all()
        return render_template("devices/import.html", types=types, warehouses=warehouses, employees=employees)
    
    file = request.files["file"]
    if file.filename == "":
        flash("Файл не выбран", "danger")
        types = DeviceType.query.filter(DeviceType.deleted_at.is_(None)).order_by(DeviceType.name).all()
        warehouses = Warehouse.query.filter(Warehouse.deleted_at.is_(None)).order_by(Warehouse.name).all()
        employees = Employee.query.filter(Employee.deleted_at.is_(None)).order_by(Employee.last_name, Employee.first_name, Employee.middle_name).all()
        return render_template("devices/import.html", types=types, warehouses=warehouses, employees=employees)
    
    if not file.filename.endswith((".xlsx", ".xls")):
        flash("Поддерживаются только файлы Excel (.xlsx, .xls)", "danger")
        types = DeviceType.query.filter(DeviceType.deleted_at.is_(None)).order_by(DeviceType.name).all()
        warehouses = Warehouse.query.filter(Warehouse.deleted_at.is_(None)).order_by(Warehouse.name).all()
        employees = Employee.query.filter(Employee.deleted_at.is_(None)).order_by(Employee.last_name, Employee.first_name, Employee.middle_name).all()
        return render_template("devices/import.html", types=types, warehouses=warehouses, employees=employees)
    
    try:
        # Читаем файл в память
        file_content = file.read()
        
        # Делегируем логику импорта сервису
        result = InventoryService.import_devices_from_excel(file_content)
        
        # Формируем сообщения для пользователя на основе результата
        if result['imported'] > 0:
            flash(f"Импортировано девайсов: {result['imported']}", "success")
        
        if result['skipped'] > 0:
            flash(f"Пропущено строк: {result['skipped']}", "warning")
            
        if result['errors']:
            flash(f"Ошибки при импорте ({len(result['errors'])}):", "danger")
            for error in result['errors'][:10]:  # Показываем первые 10 ошибок
                flash(error, "danger")
            if len(result['errors']) > 10:
                flash(f"... и еще {len(result['errors']) - 10} ошибок", "danger")
                
        return redirect(url_for("devices.list_devices"))
        
    except Exception as e:
        # В сервисе уже есть обработка, но если что-то упало совсем неожиданно
        flash(f"Ошибка при импорте: {str(e)}", "danger")
        logger.exception("Неожиданная ошибка при импорте девайсов")
        types = DeviceType.query.filter(DeviceType.deleted_at.is_(None)).order_by(DeviceType.name).all()
        warehouses = Warehouse.query.filter(Warehouse.deleted_at.is_(None)).order_by(Warehouse.name).all()
        employees = Employee.query.filter(Employee.deleted_at.is_(None)).order_by(Employee.last_name, Employee.first_name, Employee.middle_name).all()
        return render_template("devices/import.html", types=types, warehouses=warehouses, employees=employees)

