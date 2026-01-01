from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField
from wtforms.validators import Optional


user_types = [
    "admin",
    "oo_user",
    "ro_user",
    "coinsurance_hub_user",
    "ho_motor_tp",
    "ro_motor_tp",
    "ri_tech",
    "ri_accounts",
    "ho_technical",
]


class UpdateUserForm(FlaskForm):
    user_type = SelectField(
        "Change user type",
        choices=user_types,
        validators=[Optional()],
    )

    reset_password = BooleanField()


class UserAddForm(FlaskForm):
    ro_code = StringField(filters=[lambda x: x.strip() if x else None])
    oo_code = StringField(filters=[lambda x: x.strip() if x else None])
    username = StringField(filters=[lambda x: x.strip().lower() if x else None])
    user_type = SelectField(choices=user_types)
