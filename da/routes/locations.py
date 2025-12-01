import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import AuditAction, Location
from ..services.audit import log_action
from ..utils import admin_required, can_delete_required

locations_bp = Blueprint("locations", __name__, template_folder="../templates")
logger = logging.getLogger(__name__)


@locations_bp.get("/")
@login_required
def list_locations():
    locations = Location.query.filter(Location.deleted_at.is_(None)).order_by(Location.name).all()
    return render_template("locations/list.html", locations=locations)


@locations_bp.route("/create", methods=["GET", "POST"])
@admin_required
def create_location():
    if request.method == "POST":
        location = Location(name=request.form["name"])
        db.session.add(location)
        try:
            db.session.commit()
            log_action(
                AuditAction.CREATE,
                "location",
                entity_id=location.id,
                entity_name=location.name,
            )
            flash("Локация добавлена", "success")
            logger.info("Создана локация %s (%s)", location.name, location.id)
            return redirect(url_for("locations.list_locations"))
        except IntegrityError:
            db.session.rollback()
            flash("Локация с таким названием уже существует", "danger")
            logger.warning("Ошибка создания локации: дубликат %s", location.name)
    return render_template("locations/form.html", location=None)


@locations_bp.route("/<int:location_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_location(location_id: int):
    location = Location.query.get_or_404(location_id)
    if request.method == "POST":
        old_name = location.name
        location.name = request.form["name"]
        try:
            db.session.commit()
            log_action(
                AuditAction.UPDATE,
                "location",
                entity_id=location.id,
                entity_name=location.name,
                changes={"name": {"old": old_name, "new": location.name}},
            )
            flash("Локация переименована", "success")
            logger.info("Переименована локация %s -> %s", old_name, location.name)
            return redirect(url_for("locations.list_locations"))
        except IntegrityError:
            db.session.rollback()
            flash("Локация с таким названием уже существует", "danger")
            logger.warning("Ошибка переименования локации %s: дубликат", request.form["name"])
    return render_template("locations/form.html", location=location)


@locations_bp.post("/<int:location_id>/delete")
@can_delete_required
def delete_location(location_id: int):
    from ..models import utcnow
    
    location = Location.query.get_or_404(location_id)
    if location.devices or location.employees:
        flash("Нельзя удалить локацию, пока к ней привязаны записи", "danger")
        return redirect(url_for("locations.list_locations"))
    
    from ..services.delete_handler import handle_entity_deletion
    
    success, message = handle_entity_deletion(location, "location", location.name)
    flash(message, "success")
    logger.info("Удалена локация %s (%s)", location.name, location_id)
    return redirect(url_for("locations.list_locations"))





