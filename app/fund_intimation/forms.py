from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional, Regexp, ValidationError


class FundIntimationForm(FlaskForm):
    regional_office_code = StringField(validators=[DataRequired()])
    operating_office_code = StringField(validators=[DataRequired()])
    type_of_disbursement = SelectField(
        choices=[
            "Brokerage / Commission / Reward / Incentive",
            "Claim disbursement",
            "TPA service charges",
            "Premium refund / Excess Premium refund",
            "Coinsurance disbursement",
            "Reinsurance disbursement",
            "Misc disbursement",
            "Admin charges disbursement",
        ],
        validators=[DataRequired()],
        render_kw={"onchange": "toggleClaimDetails()"},
    )
    nature_of_recipient = SelectField(
        choices=[
            "Broker",
            "Claimant",
            "Coinsurer",
            "Contractor",
            "Court",
            "Customer",
            "Dealer",
            "Employee",
            "External resource",
            "Financier",
            "Hospital",
            "Intermediary",
            "Landlord",
            "Office",
            "Reinsurer",
            "Reinsurer broker",
            "TPA",
            "Vendor",
            "Workshop",
        ],
        validators=[DataRequired()],
    )
    name_of_recipient = StringField(validators=[DataRequired()])
    purpose_of_disbursement = TextAreaField(validators=[Optional()])
    claim_number = StringField()
    coinsurance_involved = BooleanField(
        validators=[Optional()],
        render_kw={
            "class": "is-large-checkbox",
            "onchange": "toggleCoinsuranceDetails()",
        },
    )
    coinsurance_details = TextAreaField()

    transaction_id = StringField(
        "Transaction ID",
        validators=[
            Optional(),
            Length(min=16, max=16),
            Regexp(r"^\d+$", message="Transaction ID field must contain only numbers."),
        ],
    )
    transaction_date = DateField(validators=[Optional()])
    transaction_amount = DecimalField(validators=[DataRequired()])

    expected_date_of_disbursement = DateField(validators=[Optional()])

    regional_office_remarks = TextAreaField(validators=[Optional()])

    def validate_claim_number(self, field):
        if self.type_of_disbursement.data == "Claim" and not field.data:
            raise ValidationError("Claim number is required.")

    def validate_coinsurance_details(self, field):
        if self.coinsurance_involved.data and not field.data:
            raise ValidationError("Coinsurance details are required.")


class FundIntimationFormRO(FundIntimationForm):
    regional_office_code = StringField(
        render_kw={"readonly": True}, validators=[DataRequired()]
    )


class FundIntimationFormOO(FundIntimationFormRO):
    operating_office_code = StringField(
        render_kw={"readonly": True}, validators=[DataRequired()]
    )
