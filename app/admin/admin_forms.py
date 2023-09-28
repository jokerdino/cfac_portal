from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField


class UpdateUserForm(FlaskForm):
    # select field to change type of user
    change_user_type = SelectField(
        "Change user type",
        choices=["admin", "oo_user", "ro_user", "coinsurance_hub_user"],
    )
    #  is_admin = BooleanField("Make the user admin: ")
    reset_password_page = BooleanField("Enable password reset page: ")
