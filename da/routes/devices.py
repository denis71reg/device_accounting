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
            # Обновляем основные поля (локация не изменяется вручную)
            InventoryService.update_device(
                device,
                inventory_number=request.form["inventory_number"],
                model=request.form["model"],
                type_id=int(request.form["type_id"]),
                serial_number=request.form.get("serial_number"),
                notes=request.form.get("notes"),
            )
            
            # Обрабатываем перемещение - девайс всегда должен быть привязан к складу или сотруднику
            warehouse_id = request.form.get("warehouse_id")
            owner_id = request.form.get("owner_id")
            transfer_changes = {}
            
            # Проверка: нельзя выбрать и склад, и сотрудника одновременно
            if warehouse_id and owner_id:
                flash("Нельзя одновременно выбрать склад и сотрудника. Выберите что-то одно.", "danger")
                return render_template(
                    "devices/form.html",
                    device=device,
                    types=types,
                    locations=locations,
                    warehouses=warehouses,
                    employees=employees,
                )
            
            # Если ничего не выбрано, проверяем, есть ли уже привязка
            if not warehouse_id and not owner_id:
                # Если у девайса уже есть склад или сотрудник, оставляем как есть
                if not device.warehouse_id and not device.owner_id:
                    flash("Девайс должен быть привязан к складу или сотруднику", "danger")
                    return render_template(
                        "devices/form.html",
                        device=device,
                        types=types,
                        locations=locations,
                        warehouses=warehouses,
                        employees=employees,
                    )
                # Если у девайса уже есть привязка - ничего не меняем
                pass
            # Перемещение на склад
            elif warehouse_id:
                warehouse = Warehouse.query.get_or_404(int(warehouse_id))
                old_owner = device.owner
                old_warehouse = device.warehouse
                old_location = device.location
                device.warehouse = warehouse
                device.owner = None
                device.location = warehouse.location  # Локация автоматически из склада
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
                flash(f"Девайс перемещен на склад: {warehouse.name} (локация: {warehouse.location.name})", "success")
            
            # Перемещение сотруднику
            elif owner_id:
                employee = Employee.query.get_or_404(int(owner_id))
                old_owner = device.owner
                old_warehouse = device.warehouse
                old_location = device.location
                device.owner = employee
                device.warehouse = None
                device.location = employee.location  # Локация автоматически из сотрудника
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
                flash(f"Девайс выдан сотруднику: {employee.full_name} (локация: {employee.location.name})", "success")
            
            # Логируем обновление основных полей
            changes = {
                k: {"old": old_data.get(k), "new": getattr(device, k)}
                for k in old_data
                if old_data.get(k) != getattr(device, k) and k not in ("warehouse_id", "owner_id")
            }
            if changes:
                log_action(
                    AuditAction.UPDATE,
                    "device",
                    entity_id=device.id,
                    entity_name=device.inventory_number,
                    changes=changes,
                )
            
            if not warehouse_id and not owner_id:
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
    
    return render_template(
        "devices/form.html",
        device=device,
        types=types,
        locations=locations,
        warehouses=warehouses,
        employees=employees,
    )


@devices_bp.post("/<int:device_id>/delete")
@can_delete_required
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
        import openpyxl
        from io import BytesIO
        
        # Читаем файл в память
        file_content = file.read()
        wb = openpyxl.load_workbook(BytesIO(file_content))
        ws = wb.active
        
        # Пропускаем заголовок (первая строка)
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        
        if not rows:
            flash("Файл пуст или содержит только заголовки", "warning")
            types = DeviceType.query.filter(DeviceType.deleted_at.is_(None)).order_by(DeviceType.name).all()
            warehouses = Warehouse.query.filter(Warehouse.deleted_at.is_(None)).order_by(Warehouse.name).all()
            employees = Employee.query.filter(Employee.deleted_at.is_(None)).order_by(Employee.last_name, Employee.first_name, Employee.middle_name).all()
            return render_template("devices/import.html", types=types, warehouses=warehouses, employees=employees)
        
        imported = 0
        skipped = 0
        errors = []
        
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
                    errors.append(f"Строка {row_num}: отсутствует инвентарный номер")
                    skipped += 1
                    continue
                
                if not model:
                    errors.append(f"Строка {row_num}: отсутствует модель")
                    skipped += 1
                    continue
                
                if not type_name:
                    errors.append(f"Строка {row_num}: отсутствует тип девайса")
                    skipped += 1
                    continue
                
                # Проверка дубликата инвентарного номера
                if Device.query.filter_by(inventory_number=inventory_number).filter(Device.deleted_at.is_(None)).first():
                    errors.append(f"Строка {row_num}: девайс с инвентарным номером {inventory_number} уже существует")
                    skipped += 1
                    continue
                
                # Находим тип девайса
                device_type = DeviceType.query.filter(DeviceType.name.ilike(type_name)).filter(DeviceType.deleted_at.is_(None)).first()
                if not device_type:
                    errors.append(f"Строка {row_num}: тип девайса '{type_name}' не найден")
                    skipped += 1
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
                        errors.append(f"Строка {row_num}: локация '{location_name}' не найдена")
                        skipped += 1
                        continue
                
                if owner_or_warehouse:
                    # Пробуем найти сотрудника по ФИО
                    name_parts = owner_or_warehouse.strip().split()
                    if len(name_parts) >= 2:
                        last_name = name_parts[0]
                        first_name = name_parts[1]
                        middle_name = name_parts[2] if len(name_parts) > 2 else None
                        
                        employee = Employee.query.filter(
                            Employee.last_name.ilike(last_name),
                            Employee.first_name.ilike(first_name)
                        ).filter(Employee.deleted_at.is_(None)).first()
                        
                        if employee:
                            owner_id = employee.id
                            location_id = employee.location_id
                            status = DeviceStatus.ASSIGNED
                        else:
                            # Пробуем найти склад
                            warehouse = Warehouse.query.filter(Warehouse.name.ilike(owner_or_warehouse)).filter(Warehouse.deleted_at.is_(None)).first()
                            if warehouse:
                                warehouse_id = warehouse.id
                                location_id = warehouse.location_id
                                status = DeviceStatus.IN_STOCK
                            else:
                                errors.append(f"Строка {row_num}: не найден сотрудник или склад '{owner_or_warehouse}'")
                                skipped += 1
                                continue
                    else:
                        # Пробуем найти склад
                        warehouse = Warehouse.query.filter(Warehouse.name.ilike(owner_or_warehouse)).filter(Warehouse.deleted_at.is_(None)).first()
                        if warehouse:
                            warehouse_id = warehouse.id
                            location_id = warehouse.location_id
                            status = DeviceStatus.IN_STOCK
                        else:
                            errors.append(f"Строка {row_num}: не найден склад '{owner_or_warehouse}'")
                            skipped += 1
                            continue
                
                if not location_id:
                    errors.append(f"Строка {row_num}: не удалось определить локацию")
                    skipped += 1
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
                
                imported += 1
                
            except Exception as e:
                errors.append(f"Строка {row_num}: ошибка обработки - {str(e)}")
                skipped += 1
                logger.exception("Ошибка импорта девайса из строки %s", row_num)
                continue
        
        # Коммитим все изменения
        db.session.commit()
        
        # Формируем сообщение
        if imported > 0:
            flash(f"Импортировано девайсов: {imported}", "success")
        if skipped > 0:
            flash(f"Пропущено строк: {skipped}", "warning")
        if errors:
            # Сохраняем ошибки в сессию для отображения
            flash(f"Ошибки при импорте ({len(errors)}):", "danger")
            for error in errors[:10]:  # Показываем первые 10 ошибок
                flash(error, "danger")
            if len(errors) > 10:
                flash(f"... и еще {len(errors) - 10} ошибок", "danger")
        
        logger.info("Импорт девайсов: добавлено %s, пропущено %s", imported, skipped)
        return redirect(url_for("devices.list_devices"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при чтении файла: {str(e)}", "danger")
        logger.exception("Ошибка импорта девайсов из Excel")
        types = DeviceType.query.filter(DeviceType.deleted_at.is_(None)).order_by(DeviceType.name).all()
        warehouses = Warehouse.query.filter(Warehouse.deleted_at.is_(None)).order_by(Warehouse.name).all()
        employees = Employee.query.filter(Employee.deleted_at.is_(None)).order_by(Employee.last_name, Employee.first_name, Employee.middle_name).all()
        return render_template("devices/import.html", types=types, warehouses=warehouses, employees=employees)

