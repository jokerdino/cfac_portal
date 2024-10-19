from flask_wtf import FlaskForm
from flask_wtf.file import FileField, MultipleFileField, FileAllowed, FileRequired
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    IntegerField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Optional, Regexp, ValidationError

coinsurer_list = [
    "National",
    "New India",
    "Oriental",
    "Acko",
    "Aditya Birla Health",
    "Apollo Munich",
    "Bajaj Allianz",
    "Bharti AXA",
    "Chola MS",
    "Cigna TTK",
    "Edelweiss",
    "Future Generali",
    "Government Insurance Fund",
    "Go Digit",
    "HDFC Ergo",
    "ICICI Lombard",
    "Iffco Tokio",
    "Kerala State Insurance Department",
    "Kotak General",
    "L&T",
    "Liberty Videocon",
    "Magma",
    "Max Bupa",
    "Raheja QBE",
    "Reliance General",
    "Religare",
    "Royal Sundaram",
    "SBI General",
    "Shriram General",
    "Star Health",
    "TATA AIG",
    "Universal Sompo",
]

status_list = [
    "To be reviewed by coinsurance hub",
    "Needs clarification from RO or OO",
    "To be approved in GC Core",
    "To be settled",
    "Settled",
    "No longer valid",
]


class QueryForm(FlaskForm):
    coinsurer_name = SelectMultipleField(
        "Name of coinsurer", choices=sorted(coinsurer_list)
    )
    status = SelectMultipleField("Select status", choices=status_list)

    submit = SubmitField("Submit")


class CoinsuranceForm(FlaskForm):

    regional_office_code = StringField("Regional office code")
    oo_code = StringField("Operating office code")
    coinsurer_name = SelectField("Name of coinsurer", choices=coinsurer_list)
    coinsurer_office_code = StringField("Coinsurer office code")

    type_of_transaction = SelectField(
        "Select whether United India is leader or follower",
        choices=["Leader", "Follower"],
    )
    period_of_settlement = StringField("Period of settlement")
    name_of_insured = StringField("Name of insured")
    request_id = TextAreaField("Request ID")
    statement = FileField("Upload statement", validators=[Optional()])
    confirmation = FileField("Upload confirmation", validators=[Optional()])
    payable_amount = IntegerField("Payable amount", validators=[Optional()])
    receivable_amount = IntegerField("Receivable amount", validators=[Optional()])

    bool_reinsurance = BooleanField(
        "Whether Reinsurance is involved", validators=[Optional()]
    )
    int_ri_payable_amount = IntegerField(
        "Reinsurance payable amount", validators=[Optional()]
    )
    int_ri_receivable_amount = IntegerField(
        "Reinsurance receivable amount", validators=[Optional()]
    )
    ri_confirmation = FileField("Upload RI confirmation", validators=[Optional()])

    remarks = TextAreaField("Add remarks")
    current_status = SelectField(
        "Current status", choices=status_list, validators=[Optional()]
    )
    settlement = SelectField(
        "Update settlement details",
        choices=[],
        validators=[Optional()],
        validate_choice=False,
    )


class SettlementForm(FlaskForm):
    name_of_company = SelectField(
        "Enter coinsurer name", choices=coinsurer_list, validators=[DataRequired()]
    )
    date_of_settlement = DateField(validators=[DataRequired()])
    settled_amount = DecimalField(validators=[DataRequired()])
    utr_number = StringField("UTR number", validators=[DataRequired()])
    settlement_file = FileField("Upload summary statement")
    type_of_transaction = RadioField(
        "Paid or received", choices=["Paid", "Received"], validators=[DataRequired()]
    )
    notes = TextAreaField(validators=[Optional()])


class SettlementUTRForm(FlaskForm):
    utr_number = SelectField("UTR number", validators=[Optional()])
    update_settlement = SubmitField("Update settlement")


class CoinsuranceBalanceQueryForm(FlaskForm):
    period = SelectField("Select Period", validators=[DataRequired()])
    head_office_balance = BooleanField("Include Head Office balances")


class CoinsurerSelectForm(FlaskForm):
    coinsurer_name = SelectField("Select coinsurer")
    filter_coinsurer = SubmitField("Submit")


class CoinsuranceCashCallForm(FlaskForm):
    txt_hub = SelectField(
        "Coinsurance Hub",
        choices=["West Zone", "East Zone", "North Zone", "South Zone"],
        validators=[DataRequired()],
    )
    txt_ro_code = StringField("Regional Office Code", validators=[DataRequired()])
    txt_oo_code = StringField("Operating Office Code", validators=[DataRequired()])

    str_leader_follower = RadioField(
        "Whether United India is leader or follower",
        choices=["Leader", "Follower"],
        validators=[DataRequired()],
    )
    txt_insured_name = StringField("Name of insured", validators=[DataRequired()])
    date_policy_start_date = DateField("Policy start date", validators=[DataRequired()])
    date_policy_end_date = DateField("Policy end date", validators=[DataRequired()])

    amount_total_paid = DecimalField("100% claim amount", validators=[DataRequired()])
    date_claim_payment = DateField("Date of claim payment", validators=[Optional()])

    txt_coinsurer_name = SelectField(
        "Coinsurer name", choices=coinsurer_list, validators=[DataRequired()]
    )
    percent_share = DecimalField(
        "Percentage share to be settled", validators=[DataRequired()]
    )
    amount_of_share = DecimalField(
        "Amount of share to be settled", validators=[DataRequired()]
    )
    txt_request_id = StringField("Request ID", validators=[Optional()])

    date_of_cash_call_raised = DateField(
        "Date when cash call was raised", validators=[DataRequired()]
    )
    txt_current_status = SelectField(
        "Current status",
        validators=[DataRequired()],
        choices=["Pending", "Paid", "Received"],
    )
    txt_utr_number = StringField("If settled, UTR Number", validators=[Optional()])
    date_of_cash_call_settlement = DateField(
        "If settled, date of settlement", validators=[Optional()]
    )
    amount_settlement = DecimalField(
        "If settled, amount settled", validators=[Optional()]
    )
    txt_remarks = TextAreaField("Remarks", validators=[DataRequired()])

    def validate_date_policy_end_date(self, field):
        if field.data < self.date_policy_start_date.data:
            raise ValidationError("End date should not be earlier than start date.")


class UploadFileForm(FlaskForm):
    file_upload = FileField("Upload document", validators=[DataRequired()])
    upload_document = SubmitField("Upload")


class CoinsuranceBalanceForm(FlaskForm):

    period = StringField(
        description="Enter in mmm-yy format (example: 'Aug-24')",
        validators=[DataRequired()],
    )
    csv_files_upload = MultipleFileField(
        "Upload CSV files", validators=[FileRequired(), FileAllowed(["csv"])]
    )

    flag_sheet_file = FileField(
        "Upload Flag sheet", validators=[FileRequired(), FileAllowed(["xlsx"])]
    )
    upload_document = SubmitField("Upload")


class CoinsuranceBankMandateForm(FlaskForm):

    company_name = SelectField(choices=coinsurer_list, validators=[DataRequired()])
    office_code = StringField(validators=[DataRequired()])

    bank_name = StringField(validators=[DataRequired()])
    ifsc_code = StringField(
        "IFSC Code",
        validators=[
            DataRequired(),
            Regexp(
                "^[A-Z]{4}0[A-Z0-9a-z]{6}$",
                message="Please enter IFSC code in correct pattern.",
            ),
        ],
    )
    bank_account_number = StringField(validators=[DataRequired()])

    bank_mandate_file = FileField(validators=[FileAllowed(["pdf"])])
    remarks = TextAreaField()


class CoinsuranceReceiptEditForm(FlaskForm):

    status = RadioField(choices=["Pending", "Receipted"], validators=[DataRequired()])
    receipting_office = SelectField(
        choices=["", "South", "West", "East", "North", "Head Office"],
        validators=[Optional()],
    )
    date_of_receipt = DateField(validators=[Optional()])
    remarks = TextAreaField(validators=[Optional()])


class DeleteCoinsuranceBalanceEntries(FlaskForm):
    period = SelectField()


class CoinsuranceReceiptAddForm(FlaskForm):
    company_name = SelectField(choices=coinsurer_list, validators=[DataRequired()])
    credit = DecimalField(validators=[DataRequired()])
    value_date = DateField(validators=[DataRequired()])
    reference_no = StringField(validators=[DataRequired()])
    transaction_code = StringField(validators=[DataRequired()])
