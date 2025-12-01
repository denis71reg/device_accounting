import logging
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user

from .extensions import db
from .models import Location, UserRole

logger = logging.getLogger(__name__)


def login_required_with_role(*allowed_roles: UserRole):
    """Декоратор для проверки прав доступа по ролям"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Необходима авторизация", "warning")
                return redirect(url_for("auth.login"))
            
            if current_user.role not in allowed_roles:
                flash("У вас нет прав для выполнения этого действия", "danger")
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Декоратор для действий, требующих прав администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Необходима авторизация", "warning")
            return redirect(url_for("auth.login"))
        
        if not current_user.is_admin:
            flash("Только администраторы могут выполнять это действие", "danger")
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def super_admin_required(f):
    """Декоратор для действий, требующих прав супер-администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Необходима авторизация", "warning")
            return redirect(url_for("auth.login"))
        
        if not current_user.is_super_admin:
            flash("Только супер-администраторы могут выполнять это действие", "danger")
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def can_delete_required(f):
    """Декоратор для действий удаления (только супер-админ)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Необходима авторизация", "warning")
            return redirect(url_for("auth.login"))
        
        if not current_user.can_delete:
            flash("Удаление доступно только супер-администраторам", "danger")
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def get_or_create_location(location_name: str) -> Location:
    """
    Находит существующую локацию по имени или создает новую.
    
    Args:
        location_name: Название локации
    
    Returns:
        Location: Объект локации
    
    Raises:
        ValueError: Если название локации пустое
    """
    location_name = location_name.strip()
    if not location_name:
        raise ValueError("Название локации не может быть пустым")
    
    location = Location.query.filter_by(name=location_name).first()
    if not location:
        location = Location(name=location_name)
        db.session.add(location)
        db.session.flush()
        logger.info("Создана новая локация: %s", location_name)
    
    return location


