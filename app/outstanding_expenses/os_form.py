from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    TextAreaField,
    SelectField,
    StringField,
    SubmitField,
    HiddenField,
)
from wtforms.validators import (
    DataRequired,
    Optional,
    ValidationError,
    Regexp,
)


class OutstandingExpensesForm(FlaskForm):
    str_regional_office_code = StringField(
        "Enter Regional Office",
        validators=[DataRequired()],
    )
    str_operating_office_code = StringField(
        "Enter Operating Office",
        validators=[DataRequired()],
    )

    str_party_type = SelectField(
        "Select Party type",
        choices=["Landlord", "Vendor", "Contractor", "Employee", "Others"],
        validators=[DataRequired()],
    )
    str_party_name = StringField("Enter Party name", validators=[DataRequired()])
    str_party_id = StringField("Enter Party ID", validators=[DataRequired()])

    float_gross_amount = DecimalField(
        "Enter gross outstanding amount",
        validators=[DataRequired()],
        render_kw={"onkeyup": "calculateSum()"},
    )

    bool_tds_involved = BooleanField(
        "Whether TDS is involved",
        validators=[Optional()],
        render_kw={"class": "is-large-checkbox"},
    )
    str_section = SelectField(
        "Select section",
        choices=[
            "Salaries u/s 192",
            "Rent u/s 194I",
            "Interest u/s 194A",
            "Commission u/s 194D",
            "Contractors u/s 194C",
            "Other Insurance commission u/s 194H",
            "Professional charges u/s 194J",
            "Purchase of goods u/s 194Q",
        ],
        validators=[Optional()],
        render_kw={
            "disabled": "disabled",
        },
    )
    float_tds_amount = DecimalField(
        "Enter TDS amount",
        validators=[Optional()],
        render_kw={
            "onkeyup": "calculateSum()",
            "disabled": "disabled",
        },
    )
    str_pan_number = StringField(
        "Enter PAN number",
        validators=[
            Optional(),
            Regexp(
                "^[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}$",
                message="Not a valid PAN number.",
            ),
        ],
        filters=[lambda x: x.upper() if x else None],
        render_kw={
            "disabled": "disabled",
        },
    )

    str_nature_of_payment = SelectField(
        "Select nature of payment",
        choices=[
            "ADVERTISEMENT & PUBLICITY",
            "AUDIT FEES",
            "AUDITORS TRAVELLING EXPENSES",
            "BINDING CHARGES",
            "BUSINESS ASSOCIATE-CONVEYANCE EXPENSES REIMBURSEMENT",
            "BUSINESS ASSOCIATE-MONTHLY REMUNERATION",
            "BUSINESS ASSOCIATE-PROFIT INCENTIVE",
            "BUSINESS ASSOCIATE-TELEPHONE EXP REIMBURSEMENT",
            "BUSINESS ASSOCIATE-VOLUME ALLOWANCE",
            "ELECTRICITY CHARGES",
            "EXPENSES ON CO-OWNED PROP-OFFICE",
            "EXPENSES ON CO-OWNED PROP-RESI",
            "INSURANCE PREMIUM OTHER THAN ON VEHICLES",
            "INTERNET CHARGES-OFFICE",
            "INTERNET CHARGES-RESIDENCE",
            "LEAVE TRAVEL SUBSIDY-CLASS 1",
            "LEAVE TRAVEL SUBSIDY-CLASS 2",
            "LEAVE TRAVEL SUBSIDY-CLASS 3",
            "LEAVE TRAVEL SUBSIDY-CLASS 4",
            "LEGAL EXPENSES",
            "MEETING AND CONFERENCE EXPENSES-OTHERS",
            "OFFICE UPKEEP AND MAINTENANCE",
            "OUTSOURCHING-Guest House Caretakers",
            "OUTSOURCING- Driver for Company Pool car",
            "OUTSOURCING-Gardeners",
            "OUTSOURCING-Helper for Caretaker",
            "OUTSOURCING-House Keeping Services",
            "OUTSOURCING-Learning Center facilities management including Canteen",
            "OUTSOURCING-Record Management including claim files",
            "OUTSOURCING-Security Services",
            "OUTSOURCING-Transit Camp Caretakers",
            "PERIODICALS AND NEWSPAPERS",
            "PHOTOCOPYING EXPENSES",
            "POSTAGE/SPEED POST/COURIER/TELEGRAMS/TEXLEX CHRGES",
            "PRINTING EXPENSES",
            "PROFESSIONAL CHARGES",
            "RATES & TAXES-CO.OWNED PROPERTY-OFICE BLDG",
            "RATES & TAXES-CO.OWNED PROPERTY-RESI. BLDG",
            "REIMBURSEMENT OF EXPENSES TO MO INCHARGE",
            "REIMBURSEMENT OF PERSONAL LEASE",
            "RENT PAID - OTHERS",
            "RENT PAID-COMPANY LEASE",
            "RENT PAID-OFFICE",
            "RENT PAID-RESIDENCE",
            "RENT PAID-TRANSIT CAMP/GUEST HOUSE",
            "STATIONERY EXPENSES",
            "TAX CONSULTANTS FEES",
            "TELEPHONE EXPENSES-OFFICE",
            "TELEPHONE EXPENSES-RESIDENCE",
            "TRAVELLING EXPENSES-CLASS 1",
            "TRAVELLING EXPENSES-CLASS 2",
            "TRAVELLING EXPENSES-CLASS 3",
            "TRAVELLING EXPENSES-CLASS 4",
            "UMEX EXPENSES FOR INDIVIDUAL AGENTS OUT OF POCKET EXPENSES",
            "UMEX EXPENSES FOR INDIVIDUAL AGENTS REWARD BENEFITS",
            "MOTOR CAR EXPNS-OIL&FUEL-CONV.SCHEME",
            "MOTOR CAR EXPNS-OIL&FUEL-POOL CARS",
            "OTHERS",
        ],
        validators=[DataRequired()],
    )
    str_narration = TextAreaField(
        "Enter narration for outstanding expenses",
        validators=[DataRequired()],
    )

    date_payment_date = DateField(
        "Enter date of payment (if already paid)",
        validators=[Optional()],
        render_kw={"min": "2024-04-01"},
    )
    float_net_amount = HiddenField()

    def validate_float_gross_amount(self, field):
        if self.float_tds_amount.data:
            if field.data <= self.float_tds_amount.data:
                raise ValidationError(
                    "Outstanding amount must be higher than TDS amount."
                )

    def validate_date_payment_date(self, field):
        if field.data < date(2024, 4, 1):
            raise ValidationError("Payment date cannot be earlier than 01/04/2024.")
        if field.data > date.today():
            raise ValidationError("Payment date cannot be future date.")

    def validate_bool_tds_involved(form, field):
        if field.data:
            if not form.str_section.data:
                raise ValidationError("Please enter section details.")
            if not form.str_pan_number.data:
                raise ValidationError("Please enter PAN number.")
            if not form.float_tds_amount.data:
                raise ValidationError("Please enter TDS amount.")

    def validate(self, extra_validators=None):
        """Override default validate() to compute str_period automatically"""
        # Run the default validations first
        if not super().validate(extra_validators=extra_validators):
            return False

        # Compute the hidden field value

        self.float_net_amount.data = (self.float_gross_amount.data or 0) - (
            self.float_tds_amount.data or 0
        )
        return True


class DeleteOSForm(FlaskForm):
    delete_button = SubmitField("Delete")
