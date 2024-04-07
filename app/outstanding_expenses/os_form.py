from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FileField,
    DecimalField,
    IntegerField,
    TextAreaField,
    SelectField,
    StringField,
)
from wtforms.validators import DataRequired, Optional, NumberRange


class OutstandingExpensesForm(FlaskForm):
    regional_office_code = StringField(
        "Enter Regional Office Code",
        validators=[Optional()],  # , NumberRange(min=100, max=700000)],
    )
    operating_office_code = StringField(
        "Enter Operating Office Code",
        validators=[Optional()],  # , NumberRange(min=100, max=700000)],
    )

    party_type = SelectField(
        "Select party type",
        choices=["Landlord", "Vendor", "Contractor"],
        validators=[DataRequired()],
    )
    party_name = StringField("Enter name of party", validators=[DataRequired()])
    party_id = StringField("Enter party ID", validators=[DataRequired()])

    gross_amount = DecimalField(
        "Enter gross outstanding amount", validators=[DataRequired()]
    )

    bool_tds_involved = BooleanField("Whether TDS is involved", validators=[Optional()])
    section = SelectField(
        "Select section",
        choices=["Rent", "Interest", "Commission", "Contractors"],
        validators=[Optional()],
    )
    tds_amount = DecimalField("Enter TDS amount", validators=[Optional()])
    pan_number = StringField("Enter PAN number", validators=[Optional()])

    nature_of_payment = SelectField(
        "Select nature of payment",
        choices=[
            "Rent - Office premises",
            "Rent - Employee residence",
            "Outsourcing expenses",
            "Office upkeep and maintenance",
            "Telephone expenses",
            "Printing expenses",
            "Other office expenses",
            "Audit fees",
            "Internet charges",
            "Electricity charges",
            "Local conveyance",
            "Periodicals and newspapers",
            "Stationery expenses",
            "Courier expenses",
            "Conveyance scheme - petrol expenses",
        ],
        validators=[DataRequired()],
    )
    narration = TextAreaField(
        "Enter narration for outstanding expenses", validators=[DataRequired()]
    )
