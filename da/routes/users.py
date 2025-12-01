import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..models import UserRole
from ..utils import admin_required, super_admin_required
from ..services.user_service import UserService

users_bp = Blueprint("users", __name__, template_folder="../templates")
logger = logging.getLogger(__name__)


@users_bp.get("/")
@super_admin_required
def list_users():
    users = UserService.get_all_users()
    return render_template("users/list.html", users=users)


@users_bp.post("/<int:user_id>/set-role")
@super_admin_required
def set_user_role(user_id: int):
    new_role = request.form.get("role")
    success, message = UserService.set_user_role(user_id, new_role)
    
    flash(message, "success" if success else "danger")
    return redirect(url_for("users.list_users"))


@users_bp.post("/<int:user_id>/delete")
@admin_required
def delete_user(user_id: int):
    """Удаление пользователя (доступно админам и супер-админам)."""
    success, message = UserService.delete_user(user_id, current_user)
    flash(message, "success" if success else "danger")
    return redirect(url_for("users.list_users"))
