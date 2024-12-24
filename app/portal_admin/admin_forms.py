from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField
from wtforms.validators import Optional


class UpdateUserForm(FlaskForm):
    user_type = SelectField(
        "Change user type",
        choices=["admin", "oo_user", "ro_user", "coinsurance_hub_user"],
        validators=[Optional()],
    )

    reset_password = BooleanField("Reset password")
