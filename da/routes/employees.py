import logging
from types import SimpleNamespace

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func

from ..extensions import db
from ..models import Device, Employee
from ..services import EmployeeService
from ..utils import admin_required

employees_bp = Blueprint("employees", __name__, template_folder="../templates")
logger = logging.getLogger(__name__)


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
        try:
            EmployeeService.create_employee(request.form)
            flash("Сотрудник добавлен", "success")
            return redirect(url_for("employees.list_employees"))
        except ValueError as e:
            flash(str(e), "danger")
            temp_employee = _form_employee_namespace(
                first_name=request.form.get("first_name"),
                last_name=request.form.get("last_name"),
                middle_name=request.form.get("middle_name"),
                position=request.form.get("position"),
                email=request.form.get("email"),
                phone=request.form.get("phone"),
                telegram=request.form.get("telegram"),
                location_id=None, # Сложно восстановить ID без запроса, но форма сохраняет значения
            )
            return render_template("employees/form.html", employee=temp_employee)
            
    return render_template("employees/form.html", employee=None)


@employees_bp.route("/<int:employee_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_employee(employee_id: int):
    employee = Employee.query.get_or_404(employee_id)
    if request.method == "POST":
        try:
            EmployeeService.update_employee(employee, request.form)
            flash("Данные обновлены", "success")
            return redirect(url_for("employees.list_employees"))
        except ValueError as e:
            flash(str(e), "danger")
            # В случае ошибки отображаем форму с данными из реквеста или оставляем старые?
            # Flask-WTF делает это лучше, но здесь мы вручную.
            # Оставим объект employee как есть, но flash покажет ошибку.
            # Для лучшего UX можно было бы подставить введенные данные.
            pass
            
    return render_template("employees/form.html", employee=employee)


@employees_bp.post("/<int:employee_id>/delete")
@admin_required
def delete_employee(employee_id: int):
    from ..models import Device
    
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
        file_content = file.read()
        imported, skipped, errors = EmployeeService.import_from_excel(file_content)
        
        # Формируем сообщение
        if imported > 0:
            flash(f"Импортировано сотрудников: {imported}", "success")
        if skipped > 0:
            flash(f"Пропущено строк: {skipped}", "warning")
        if errors:
            flash(f"Ошибки при импорте ({len(errors)}):", "danger")
            for error in errors[:10]:
                flash(error, "danger")
            if len(errors) > 10:
                flash(f"... и еще {len(errors) - 10} ошибок", "danger")
        
        return redirect(url_for("employees.list_employees"))
        
    except ValueError as e:
        flash(str(e), "danger")
        return render_template("employees/import.html")
    except Exception as e:
        flash(f"Неизвестная ошибка: {str(e)}", "danger")
        logger.exception("Ошибка импорта сотрудников")
        return render_template("employees/import.html")
