import logging

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..forms import LoginForm, RegistrationForm
from ..models import User, UserRole

auth_bp = Blueprint("auth", __name__, template_folder="../templates")
logger = logging.getLogger(__name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=True)
            next_page = request.args.get("next")
            flash("Вы успешно вошли в систему", "success")
            logger.info("Пользователь %s вошёл в систему", user.email)
            return redirect(next_page or url_for("dashboard.index"))
        else:
            flash("Неверный email или пароль", "danger")
            logger.warning("Неудачная попытка входа для %s", form.email.data)

    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Проверяем, не существует ли уже пользователь с таким email
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("Пользователь с таким email уже зарегистрирован", "danger")
            logger.warning("Попытка повторной регистрации %s", form.email.data)
            return render_template("auth/register.html", form=form)
        
        try:
            # Проверяем, есть ли уже пользователи в системе
            is_first_user = User.query.count() == 0
            
            # Формируем full_name из отдельных полей
            name_parts = [form.last_name.data.strip(), form.first_name.data.strip()]
            if form.middle_name.data and form.middle_name.data.strip():
                name_parts.append(form.middle_name.data.strip())
            full_name = " ".join(name_parts)
            
            user = User(
                email=form.email.data,
                full_name=full_name,
                phone=form.phone.data or None,
                telegram=form.telegram.data or None,
            )
            # Первый пользователь автоматически становится супер-админом
            if is_first_user:
                user.role = UserRole.SUPER_ADMIN
                flash("Регистрация успешна! Вы стали первым пользователем и получили права супер-администратора.", "success")
                logger.info("Создан первый пользователь %s как супер-админ", user.email)
            else:
                flash("Регистрация успешна! Теперь вы можете войти.", "success")
                logger.info("Зарегистрирован новый пользователь %s", user.email)
            
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for("auth.login"))
        except IntegrityError:
            db.session.rollback()
            flash("Пользователь с таким email уже существует", "danger")
            logger.exception("Ошибка регистрации - дубликат email %s", form.email.data)
            return render_template("auth/register.html", form=form)
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Registration error")
            flash(f"Ошибка при регистрации: {str(e)}", "danger")
            return render_template("auth/register.html", form=form)

    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    # Сохраняем данные пользователя ДО выхода, так как после logout_user() current_user становится анонимным
    user_email = "unknown"
    try:
        if current_user.is_authenticated:
            user_email = getattr(current_user, 'email', 'unknown')
    except (AttributeError, TypeError, RuntimeError):
        pass
    
    # Выполняем выход
    logout_user()
    
    # Flash сообщение и логирование
    flash("Вы вышли из системы", "info")
    if user_email != "unknown":
        logger.info("Пользователь %s вышел из системы", user_email)
    
    # Редирект на страницу входа
    return redirect(url_for("auth.login"))

