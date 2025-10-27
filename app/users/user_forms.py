from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, NumberRange


class SignupForm(FlaskForm):
    username = StringField(validators=[DataRequired()])
    password = PasswordField(validators=[DataRequired()])
    employee_number = IntegerField(
        validators=[NumberRange(min=10000, max=99999), DataRequired()],
    )


class LoginForm(FlaskForm):
    username = StringField(
        validators=[DataRequired()],
        filters=[lambda x: x.strip().lower() if x else None],
    )
    password = PasswordField(validators=[DataRequired()])


class UpdateUserForm(FlaskForm):
    is_admin = BooleanField("Make the user admin: ")
    reset_password_page = BooleanField("Enable password reset page: ")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Enter new password: ", validators=[DataRequired()])
    confirm = PasswordField(validators=[EqualTo("password", "Password mismatch")])
