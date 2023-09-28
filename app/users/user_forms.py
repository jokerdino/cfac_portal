from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, NumberRange


class SignupForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    emp_number = IntegerField(
        "Employee number",
        validators=[NumberRange(min=10000, max=99999), DataRequired()],
    )


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class UpdateUserForm(FlaskForm):
    is_admin = BooleanField("Make the user admin: ")
    reset_password_page = BooleanField("Enable password reset page: ")


class ResetPasswordForm(FlaskForm):
    #  username = StringField("Enter username:", validators=[DataRequired()])
    # emp_number = IntegerField("Enter employee number: ", validators=[DataRequired()])
    #  reset_code = IntegerField("Enter reset code received from admin: ", validators=[DataRequired()])
    password = PasswordField("Enter new password: ", validators=[DataRequired()])
    confirm = PasswordField(validators=[EqualTo("password", "Password mismatch")])
