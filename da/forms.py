from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Войти")


class RegistrationForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    first_name = StringField("Имя", validators=[DataRequired(), Length(min=1, max=50)])
    last_name = StringField("Фамилия", validators=[DataRequired(), Length(min=1, max=50)])
    middle_name = StringField("Отчество", validators=[Length(max=50)])
    phone = StringField("Телефон", validators=[DataRequired()])
    telegram = StringField("Telegram", validators=[])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=8)])
    password_confirm = PasswordField(
        "Подтвердите пароль",
        validators=[DataRequired(), EqualTo("password", message="Пароли не совпадают")],
    )
    submit = SubmitField("Зарегистрироваться")

    def validate_email(self, field):
        if not field.data.endswith("@ittest-team.ru"):
            raise ValidationError("Регистрация доступна только для сотрудников @ittest-team.ru")

