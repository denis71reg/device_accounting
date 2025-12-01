import json
import logging
from types import SimpleNamespace

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import AuditAction, Device, Employee, Location
from ..services.audit import log_action
from ..utils import admin_required, can_delete_required
from ..utils import get_or_create_location

employees_bp = Blueprint("employees", __name__, template_folder="../templates")
logger = logging.getLogger(__name__)


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _normalize_phone(value: str) -> str:
    return (value or "").strip()


def _normalize_telegram(value: str | None) -> str | None:
    if not value:
        return None
    sanitized = value.strip()
    if not sanitized:
        return None
    if not sanitized.startswith("@"):
        sanitized = f"@{sanitized}"
    return sanitized.lower()


def _parse_location_id(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _has_duplicate(field: str, value: str | None, exclude_id: int | None = None) -> bool:
    if not value:
        return False
    column = getattr(Employee, field)
    query = Employee.query.filter(func.lower(column) == value.lower())
    if exclude_id is not None:
        query = query.filter(Employee.id != exclude_id)
    return db.session.query(query.exists()).scalar()


def _has_duplicate_name(first_name: str, last_name: str, middle_name: str | None, exclude_id: int | None = None) -> bool:
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


def _form_employee_namespace(**data) -> SimpleNamespace:
    return SimpleNamespace(**data)


@employees_bp.get("/")
@login_required
def list_employees():
    # Загружаем сотрудников с подсчетом девайсов
    employees_query = (
        db.session.query(
            Employee,
            func.count(Device.id).label('device_count')
        )
        .filter(Employee.deleted_at.is_(None))
        .outerjoin(Device, (Device.owner_id == Employee.id) & (Device.deleted_at.is_(None)))
        .group_by(Employee.id)
        .order_by(Employee.last_name, Employee.first_name, Employee.middle_name)
    )
    employees_with_counts = employees_query.all()
    return render_template(
        "employees/list.html",
        employees_with_counts=employees_with_counts,
    )


@employees_bp.route("/create", methods=["GET", "POST"])
@admin_required
def create_employee():
    if request.method == "POST":
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        middle_name = request.form.get("middle_name", "").strip() or None
        position = request.form["position"].strip()
        email = _normalize_email(request.form["email"])
        phone = _normalize_phone(request.form["phone"])
        telegram = _normalize_telegram(request.form.get("telegram"))
        location_name = request.form.get("location_name", "").strip()
        
        if not first_name or not last_name:
            flash("Имя и фамилия обязательны", "danger")
            temp_employee = _form_employee_namespace(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                position=position,
                email=email,
                phone=phone,
                telegram=telegram,
                location_id=None,
            )
            return render_template(
                "employees/form.html", employee=temp_employee
            )
        
        if not location_name:
            flash("Локация обязательна для сотрудника", "danger")
            temp_employee = _form_employee_namespace(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                position=position,
                email=email,
                phone=phone,
                telegram=telegram,
                location_id=None,
            )
            return render_template(
                "employees/form.html", employee=temp_employee
            )
        
        # Ищем или создаем локацию
        try:
            location = get_or_create_location(location_name)
            location_id = location.id
        except ValueError as e:
            flash(str(e), "danger")
            temp_employee = _form_employee_namespace(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                position=position,
                email=email,
                phone=phone,
                telegram=telegram,
                location_id=None,
            )
            return render_template("employees/form.html", employee=temp_employee)

        duplicate_errors = []
        if _has_duplicate_name(first_name, last_name, middle_name):
            duplicate_errors.append("Сотрудник с таким ФИО уже существует")
        if _has_duplicate("email", email):
            duplicate_errors.append("Сотрудник с таким email уже существует")
        if _has_duplicate("phone", phone):
            duplicate_errors.append("Сотрудник с таким телефоном уже существует")
        if telegram and _has_duplicate("telegram", telegram):
            duplicate_errors.append("Сотрудник с таким Telegram уже существует")

        if duplicate_errors:
            for message in duplicate_errors:
                flash(message, "danger")
            temp_employee = _form_employee_namespace(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                position=position,
                email=email,
                phone=phone,
                telegram=telegram,
                location_id=location_id,
            )
            return render_template(
                "employees/form.html", employee=temp_employee
            )

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
            flash("Сотрудник добавлен", "success")
            logger.info("Создан сотрудник %s (%s)", employee.full_name, employee.email)
            return redirect(url_for("employees.list_employees"))
        except IntegrityError:
            db.session.rollback()
            flash("Сотрудник с такими данными уже существует", "danger")
            logger.warning("Ошибка создания сотрудника: дубликат %s", email)
    return render_template("employees/form.html", employee=None)


@employees_bp.route("/<int:employee_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_employee(employee_id: int):
    employee = Employee.query.get_or_404(employee_id)
    if request.method == "POST":
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        middle_name = request.form.get("middle_name", "").strip() or None
        position = request.form["position"].strip()
        email = _normalize_email(request.form["email"])
        phone = _normalize_phone(request.form["phone"])
        telegram = _normalize_telegram(request.form.get("telegram"))
        location_name = request.form.get("location_name", "").strip()
        
        if not first_name or not last_name:
            flash("Имя и фамилия обязательны", "danger")
            temp_employee = _form_employee_namespace(
                id=employee.id,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                position=position,
                email=email,
                phone=phone,
                telegram=telegram,
                location_id=None,
            )
            return render_template(
                "employees/form.html", employee=temp_employee
            )
        
        if not location_name:
            flash("Локация обязательна для сотрудника", "danger")
            temp_employee = _form_employee_namespace(
                id=employee.id,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                position=position,
                email=email,
                phone=phone,
                telegram=telegram,
                location_id=None,
            )
            return render_template(
                "employees/form.html", employee=temp_employee
            )
        
        # Ищем или создаем локацию
        try:
            location = get_or_create_location(location_name)
            location_id = location.id
        except ValueError as e:
            flash(str(e), "danger")
            temp_employee = _form_employee_namespace(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                position=position,
                email=email,
                phone=phone,
                telegram=telegram,
                location_id=None,
            )
            return render_template("employees/form.html", employee=temp_employee)

        duplicate_errors = []
        if _has_duplicate_name(first_name, last_name, middle_name, employee_id):
            duplicate_errors.append("Сотрудник с таким ФИО уже существует")
        if _has_duplicate("email", email, employee_id):
            duplicate_errors.append("Сотрудник с таким email уже существует")
        if _has_duplicate("phone", phone, employee_id):
            duplicate_errors.append("Сотрудник с таким телефоном уже существует")
        if telegram and _has_duplicate("telegram", telegram, employee_id):
            duplicate_errors.append("Сотрудник с таким Telegram уже существует")

        if duplicate_errors:
            for message in duplicate_errors:
                flash(message, "danger")
            temp_employee = _form_employee_namespace(
                id=employee.id,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                position=position,
                email=email,
                phone=phone,
                telegram=telegram,
                location_id=location_id,
            )
            return render_template(
                "employees/form.html", employee=temp_employee
            )

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
            log_action(
                AuditAction.UPDATE,
                "employee",
                entity_id=employee.id,
                entity_name=employee.full_name,
                changes=changes,
            )
            flash("Данные обновлены", "success")
            logger.info("Обновлены данные сотрудника %s", employee.full_name)
            return redirect(url_for("employees.list_employees"))
        except IntegrityError:
            db.session.rollback()
            flash("Ошибка: email/телефон должны быть уникальны", "danger")
            logger.warning("Ошибка обновления сотрудника %s: конфликт уникальности", employee.full_name)
    return render_template("employees/form.html", employee=employee)


@employees_bp.post("/<int:employee_id>/delete")
@admin_required
def delete_employee(employee_id: int):
    from ..models import Device, utcnow
    
    employee = Employee.query.get_or_404(employee_id)
    # Проверяем, есть ли у сотрудника привязанные девайсы (только не удаленные)
    devices_count = Device.query.filter_by(owner_id=employee_id).filter(Device.deleted_at.is_(None)).count()
    if devices_count > 0:
        flash(f"Нельзя удалить сотрудника, пока у него есть привязанные девайсы ({devices_count} шт.)", "danger")
        logger.warning("Попытка удаления сотрудника %s с привязанными девайсами (%s шт.)", employee.full_name, devices_count)
        return redirect(url_for("employees.list_employees"))
    
    from ..services.delete_handler import handle_entity_deletion
    
    success, message = handle_entity_deletion(employee, "employee", employee.full_name)
    flash(message, "success")
    return redirect(url_for("employees.list_employees"))


@employees_bp.get("/<int:employee_id>/devices")
@login_required
def employee_devices(employee_id: int):
    """Просмотр девайсов сотрудника."""
    employee = Employee.query.get_or_404(employee_id)
    devices = (
        Device.query
        .filter_by(owner_id=employee_id)
        .order_by(Device.created_at.desc())
        .all()
    )
    return render_template(
        "employees/devices.html",
        employee=employee,
        devices=devices,
    )


@employees_bp.route("/import", methods=["GET", "POST"])
@admin_required
def import_employees():
    """Импорт сотрудников из Excel файла."""
    if request.method == "GET":
        return render_template("employees/import.html")
    
    if "file" not in request.files:
        flash("Файл не выбран", "danger")
        return render_template("employees/import.html")
    
    file = request.files["file"]
    if file.filename == "":
        flash("Файл не выбран", "danger")
        return render_template("employees/import.html")
    
    if not file.filename.endswith((".xlsx", ".xls")):
        flash("Поддерживаются только файлы Excel (.xlsx, .xls)", "danger")
        return render_template("employees/import.html")
    
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
            return render_template("employees/import.html")
        
        imported = 0
        skipped = 0
        errors = []
        
        for row_num, row in enumerate(rows, start=2):
            # Пропускаем пустые строки
            if not any(row):
                continue
            
            try:
                # Парсим данные из строки
                last_name = str(row[0]).strip() if row[0] else None
                first_name = str(row[1]).strip() if row[1] else None
                middle_name = str(row[2]).strip() if row[2] and str(row[2]).strip() else None
                position = str(row[3]).strip() if row[3] else None
                email = _normalize_email(str(row[4])) if row[4] else None
                phone = _normalize_phone(str(row[5])) if row[5] else None
                telegram = _normalize_telegram(str(row[6]) if row[6] else None)
                location_name = str(row[7]).strip() if row[7] else None
                
                # Валидация обязательных полей
                if not last_name or not first_name:
                    errors.append(f"Строка {row_num}: отсутствуют имя или фамилия")
                    skipped += 1
                    continue
                
                if not position:
                    errors.append(f"Строка {row_num}: отсутствует должность")
                    skipped += 1
                    continue
                
                if not email:
                    errors.append(f"Строка {row_num}: отсутствует email")
                    skipped += 1
                    continue
                
                if not phone:
                    errors.append(f"Строка {row_num}: отсутствует телефон")
                    skipped += 1
                    continue
                
                if not location_name:
                    errors.append(f"Строка {row_num}: отсутствует локация")
                    skipped += 1
                    continue
                
                # Проверка дубликатов
                if _has_duplicate_name(first_name, last_name, middle_name):
                    errors.append(f"Строка {row_num}: сотрудник {last_name} {first_name} уже существует")
                    skipped += 1
                    continue
                
                if _has_duplicate("email", email):
                    errors.append(f"Строка {row_num}: email {email} уже используется")
                    skipped += 1
                    continue
                
                if _has_duplicate("phone", phone):
                    errors.append(f"Строка {row_num}: телефон {phone} уже используется")
                    skipped += 1
                    continue
                
                if telegram and _has_duplicate("telegram", telegram):
                    errors.append(f"Строка {row_num}: Telegram {telegram} уже используется")
                    skipped += 1
                    continue
                
                # Создаем или находим локацию
                try:
                    location = get_or_create_location(location_name)
                except ValueError as e:
                    errors.append(f"Строка {row_num}: {str(e)}")
                    skipped += 1
                    continue
                
                # Создаем сотрудника
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
                db.session.flush()
                
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
        
        # Коммитим все изменения
        db.session.commit()
        
        # Формируем сообщение
        if imported > 0:
            flash(f"Импортировано сотрудников: {imported}", "success")
        if skipped > 0:
            flash(f"Пропущено строк: {skipped}", "warning")
        if errors:
            # Сохраняем ошибки в сессию для отображения
            flash(f"Ошибки при импорте ({len(errors)}):", "danger")
            for error in errors[:10]:  # Показываем первые 10 ошибок
                flash(error, "danger")
            if len(errors) > 10:
                flash(f"... и еще {len(errors) - 10} ошибок", "danger")
        
        logger.info("Импорт сотрудников: добавлено %s, пропущено %s", imported, skipped)
        return redirect(url_for("employees.list_employees"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при чтении файла: {str(e)}", "danger")
        logger.exception("Ошибка импорта сотрудников из Excel")
        return render_template("employees/import.html")





