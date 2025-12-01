import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import AuditAction, Device, DeviceType
from ..services.audit import log_action
from ..utils import admin_required, can_delete_required

device_types_bp = Blueprint("device_types", __name__, template_folder="../templates")
logger = logging.getLogger(__name__)


@device_types_bp.get("/")
@login_required
def list_device_types():
    device_types = DeviceType.query.filter(DeviceType.deleted_at.is_(None)).order_by(DeviceType.name).all()
    # Подсчитываем количество девайсов для каждого типа
    types_with_counts = []
    for device_type in device_types:
        device_count = Device.query.filter_by(type_id=device_type.id).filter(Device.deleted_at.is_(None)).count()
        types_with_counts.append((device_type, device_count))
    return render_template("device_types/list.html", types_with_counts=types_with_counts)


@device_types_bp.route("/create", methods=["GET", "POST"])
@admin_required
def create_device_type():
    if request.method == "POST":
        name = request.form["name"].strip()
        
        if not name:
            flash("Название типа обязательно", "danger")
            return render_template("device_types/form.html", device_type=None)
        
        device_type = DeviceType(name=name)
        db.session.add(device_type)
        try:
            db.session.commit()
            log_action(
                AuditAction.CREATE,
                "device_type",
                entity_id=device_type.id,
                entity_name=device_type.name,
                changes={"name": name},
            )
            flash("Тип девайса добавлен", "success")
            logger.info("Создан тип девайса %s (%s)", device_type.name, device_type.id)
            return redirect(url_for("device_types.list_device_types"))
        except IntegrityError:
            db.session.rollback()
            flash("Тип девайса с таким названием уже существует", "danger")
            logger.warning("Ошибка создания типа девайса: дубликат %s", name)
    return render_template("device_types/form.html", device_type=None)


@device_types_bp.route("/<int:device_type_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_device_type(device_type_id: int):
    device_type = DeviceType.query.get_or_404(device_type_id)
    if request.method == "POST":
        old_name = device_type.name
        name = request.form["name"].strip()
        
        if not name:
            flash("Название типа обязательно", "danger")
            return render_template("device_types/form.html", device_type=device_type)
        
        device_type.name = name
        try:
            db.session.commit()
            changes = {}
            if old_name != name:
                changes = {"name": {"old": old_name, "new": name}}
            if changes:
                log_action(
                    AuditAction.UPDATE,
                    "device_type",
                    entity_id=device_type.id,
                    entity_name=device_type.name,
                    changes=changes,
                )
            flash("Тип девайса обновлен", "success")
            logger.info("Обновлён тип девайса %s (%s)", device_type.name, device_type_id)
            return redirect(url_for("device_types.list_device_types"))
        except IntegrityError:
            db.session.rollback()
            flash("Тип девайса с таким названием уже существует", "danger")
            logger.warning("Ошибка обновления типа девайса %s: дубликат", name)
    return render_template("device_types/form.html", device_type=device_type)


@device_types_bp.post("/<int:device_type_id>/delete")
@admin_required
def delete_device_type(device_type_id: int):
    from ..models import utcnow
    
    device_type = DeviceType.query.get_or_404(device_type_id)
    
    # Проверка на наличие привязанных девайсов (только не удаленные)
    device_count = Device.query.filter_by(type_id=device_type_id).filter(Device.deleted_at.is_(None)).count()
    if device_count > 0:
        flash(f"Нельзя удалить тип девайса, пока к нему привязаны девайсы ({device_count} шт.)", "danger")
        logger.warning("Попытка удаления типа девайса %s с привязанными девайсами (%s шт.)", device_type.name, device_count)
        return redirect(url_for("device_types.list_device_types"))
    
    from ..services.delete_handler import handle_entity_deletion
    
    success, message = handle_entity_deletion(device_type, "device_type", device_type.name)
    flash(message, "success")
    return redirect(url_for("device_types.list_device_types"))

