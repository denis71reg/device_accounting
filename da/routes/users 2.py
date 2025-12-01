import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import User, UserRole
from ..utils import admin_required, super_admin_required
from ..services.delete_handler import handle_entity_deletion

users_bp = Blueprint("users", __name__, template_folder="../templates")
logger = logging.getLogger(__name__)


@users_bp.get("/")
@super_admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("users/list.html", users=users)


@users_bp.post("/<int:user_id>/set-role")
@super_admin_required
def set_user_role(user_id: int):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    
    if not new_role or new_role not in [r.value for r in UserRole]:
        flash("Неверная роль", "danger")
        return redirect(url_for("users.list_users"))
    
    old_role = user.role
    user.role = UserRole(new_role)
    
    try:
        db.session.commit()
        flash(f"Роль пользователя {user.full_name} изменена с {old_role.value} на {new_role}", "success")
        logger.info("Роль пользователя %s изменена с %s на %s", user.email, old_role.value, new_role)
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при изменении роли: {str(e)}", "danger")
        logger.exception("Ошибка при изменении роли пользователя %s", user_id)
    
    return redirect(url_for("users.list_users"))


@users_bp.post("/<int:user_id>/delete")
@admin_required
def delete_user(user_id: int):
    """Удаление пользователя (доступно админам и супер-админам)."""
    from flask_login import current_user
    
    user = User.query.get_or_404(user_id)
    
    # Нельзя удалить самого себя
    if user.id == current_user.id:
        flash("Нельзя удалить самого себя", "danger")
        return redirect(url_for("users.list_users"))
    
    # Супер-админ может удалить любого, админ - только обычных пользователей
    if not current_user.is_super_admin and user.is_admin:
        flash("Админы не могут удалять других админов и супер-админов", "danger")
        return redirect(url_for("users.list_users"))
    
    user_email = user.email
    user_name = user.full_name
    
    success, message = handle_entity_deletion(user, "user", user_name)
    flash(message, "success" if success else "danger")
    logger.info("Пользователь %s удален пользователем %s", user_email, current_user.email)
    
    return redirect(url_for("users.list_users"))

