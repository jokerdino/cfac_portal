from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, EmailField, IntegerField
from wtforms.validators import DataRequired, NumberRange


class ContactsForm(FlaskForm):

    office_code = StringField(validators=[DataRequired()])
    office_name = StringField(validators=[DataRequired()])
    zone = SelectField(
        validators=[DataRequired()],
        choices=["North", "South", "East", "West", "Head Office"],
    )
    name = StringField("Employee name", validators=[DataRequired()])
    employee_number = IntegerField(
        validators=[NumberRange(min=10000, max=99999), DataRequired()],
    )

    role = SelectField(
        choices=[
            "Regional Accountant",
            "Second Officer",
            "GST Nodal officer",
            "Regional Manager-Accounts",
            "Regional Incharge",
            "Head Office",
            "Coinsurance Hub - Incharge",
            "Coinsurance Hub - Officer",
        ],
        validators=[DataRequired()],
    )
    designation = SelectField(
        choices=[
            "Admin Officer",
            "Assistant Manager",
            "Deputy Manager",
            "Manager",
            "Chief Manager",
            "Regional Manager",
            "Deputy General Manager",
        ],
        validators=[DataRequired()],
    )
    email_address = EmailField(validators=[DataRequired()])
    mobile_number = StringField(validators=[DataRequired()])
