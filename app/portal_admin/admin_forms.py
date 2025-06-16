from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField
from wtforms.validators import Optional


class UpdateUserForm(FlaskForm):
    user_type = SelectField(
        "Change user type",
        choices=["admin", "oo_user", "ro_user", "coinsurance_hub_user"],
        validators=[Optional()],
    )

    reset_password = BooleanField("Reset password")


class UserAddForm(FlaskForm):
    ro_code = StringField()
    oo_code = StringField()
    username = StringField()
    user_type = SelectField(
        choices=[
            "admin",
            "oo_user",
            "ro_user",
            "coinsurance_hub_user",
            "ho_motor_tp",
            "ri_tech",
            "ri_accounts",
            "ho_fire",
        ],
    )
