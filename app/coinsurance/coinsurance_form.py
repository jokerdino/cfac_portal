from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    IntegerField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Optional

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


class CoinsuranceForm(FlaskForm):
    status_list = [
        "To be reviewed by coinsurance hub",
        "Needs clarification from RO or OO",
        "To be approved in GC Core",
        "To be settled",
        "Settled",
        "No longer valid",
    ]

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
    coinsurer_name = SelectField(
        "Enter coinsurer name", choices=coinsurer_list, validators=[DataRequired()]
    )
    date_of_settlement = DateField("Date of settlement", validators=[DataRequired()])
    amount_settled = DecimalField("Amount settled", validators=[DataRequired()])
    utr_number = StringField("UTR number", validators=[DataRequired()])
    settlement_file = FileField("Upload summary statement")
    type_of_settlement = RadioField(
        "Paid or received", choices=["Paid", "Received"], validators=[DataRequired()]
    )
    notes = TextAreaField("Notes", validators=[Optional()])


class SettlementUTRForm(FlaskForm):
    utr_number = SelectField("UTR number", validators=[Optional()])
    update_settlement = SubmitField("Update settlement")


class CoinsuranceBalanceQueryForm(FlaskForm):
    period = SelectField("Select Period", validators=[DataRequired()])


class CoinsurerSelectForm(FlaskForm):
    coinsurer_name = SelectField("Select coinsurer")
    filter_coinsurer = SubmitField("Submit")


class CoinsuranceCashCallForm(FlaskForm):
    hub = SelectField(
        "Coinsurance Hub",
        choices=["West Zone", "East Zone", "North Zone", "South Zone"],
        validators=[DataRequired()],
    )
    ro_code = StringField("Regional Office Code", validators=[DataRequired()])
    oo_code = StringField("Operating Office Code", validators=[DataRequired()])

    str_leader_follower = SelectField(
        "Whether United India is leader or follower",
        choices=["Leader", "Follower"],
        validators=[DataRequired()],
    )
    insured_name = StringField("Name of insured", validators=[DataRequired()])
    policy_start_date = DateField("Policy start date", validators=[DataRequired()])
    policy_end_date = DateField("Policy end date", validators=[DataRequired()])

    amount_total_paid = DecimalField("100% claim amount", validators=[DataRequired()])
    remarks = TextAreaField("Remarks", validators=[DataRequired()])
    date_claim_payment = DateField("Date of claim payment", validators=[Optional()])

    coinsurer_name = SelectField(
        "Coinsurer name", choices=coinsurer_list, validators=[DataRequired()]
    )
    percent_share = DecimalField(
        "Percentage share to be settled", validators=[DataRequired()]
    )
    amount_of_share = DecimalField(
        "Amount of share to be settled", validators=[DataRequired()]
    )
    request_id = StringField("Request ID", validators=[Optional()])

    date_of_cash_call_raised = DateField(
        "Date when cash call was raised", validators=[DataRequired()]
    )
    current_status = SelectField(
        "Current status",
        validators=[DataRequired()],
        choices=["Pending", "Paid", "Received"],
    )
    utr_number = StringField("If settled, UTR Number", validators=[Optional()])
    date_of_settlement = DateField(
        "If settled, date of settlement", validators=[Optional()]
    )
    amount_settled = DecimalField("If settled, amount settled", validators=[Optional()])


class UploadFileForm(FlaskForm):
    file_upload = FileField("Upload document", validators=[DataRequired()])
    upload_document = SubmitField("Upload")
