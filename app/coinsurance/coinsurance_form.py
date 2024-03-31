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
    "Kotak Mahindra",
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

    regional_office_code = StringField("Enter Regional Office Code")
    oo_code = StringField("Enter Operating Office Code")
    coinsurer_name = SelectField("Enter Coinsurer name", choices=coinsurer_list)
    coinsurer_office_code = StringField("Enter Coinsurer Office Code")

    type_of_transaction = SelectField(
        "Select whether United India is leader or follower",
        choices=["Leader", "Follower"],
    )
    name_of_insured = StringField("Enter name of insured")
    request_id = StringField("Enter Request ID")
    statement = FileField("Upload statement", validators=[Optional()])
    confirmation = FileField("Upload confirmation", validators=[Optional()])
    payable_amount = IntegerField("Enter payable amount", validators=[Optional()])
    receivable_amount = IntegerField("Enter receivable amount", validators=[Optional()])

    bool_reinsurance = BooleanField(
        "Whether Reinsurance is involved", validators=[Optional()]
    )
    int_ri_payable_amount = IntegerField(
        "Enter Reinsurance payable amount", validators=[Optional()]
    )
    int_ri_receivable_amount = IntegerField(
        "Enter Reinsurance receivable amount", validators=[Optional()]
    )
    ri_confirmation = FileField("Upload RI confirmation", validators=[Optional()])

    remarks = TextAreaField("Enter remarks")
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
        "Enter coinsurer name:", choices=coinsurer_list, validators=[DataRequired()]
    )
    date_of_settlement = DateField("Date of settlement:", validators=[DataRequired()])
    amount_settled = DecimalField("Amount settled", validators=[DataRequired()])
    utr_number = StringField("UTR number:", validators=[DataRequired()])
    settlement_file = FileField("Upload summary statement:")
    type_of_settlement = RadioField(
        "Paid or received: ", choices=["Paid", "Received"], validators=[DataRequired()]
    )
    notes = TextAreaField("Notes", validators=[Optional()])


class SettlementUTRForm(FlaskForm):
    utr_number = SelectField("UTR number: ", validators=[Optional()])
    update_settlement = SubmitField("Update settlement")


class CoinsuranceBalanceQueryForm(FlaskForm):
    period = SelectField("Select Period", validators=[DataRequired()])


class CoinsurerSelectForm(FlaskForm):
    coinsurer_name = SelectField("Select coinsurer")
    filter_coinsurer = SubmitField("Refresh")
