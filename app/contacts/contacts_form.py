from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, EmailField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange


class ContactsForm(FlaskForm):
    name = StringField("Enter name")
    employee_number = IntegerField(
        "Enter employee number",
        validators=[NumberRange(min=10000, max=99999), DataRequired()],
    )

    office_code = StringField("Enter Office code")
    office_name = StringField("Enter Office name")
    zone = SelectField(
        "Select zone", choices=["North", "South", "East", "West", "Head Office"]
    )
    designation = SelectField(
        "Select designation",
        choices=[
            "Admin Officer",
            "Assistant Manager",
            "Deputy Manager",
            "Manager",
            "Chief Manager",
            "Regional Manager",
            "Deputy General Manager",
        ],
    )
    role = SelectField(
        "Select role",
        choices=[
            "Regional Accountant",
            "Second Officer",
            "Regional Manager-Accounts",
            "Regional Incharge",
            "Head Office",
            "Coinsurance Hub",
        ],
    )
    email_address = EmailField("Enter email address")
    mobile_number = StringField("Enter mobile number")
