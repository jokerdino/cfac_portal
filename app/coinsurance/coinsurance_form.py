from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    BooleanField,
    DateField,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import Optional

coinsurer_list = [
    "New India",
    "Oriental",
    "National",
    "Aditya Birla",
    "TATA AIG",
    "Bajaj Allianz",
    "SBI General",
    "Royal Sundaram",
]


class CoinsuranceForm(FlaskForm):
#    coinsurer_list = [
#        "New India",
#        "Oriental",
#        "National",
#        "Aditya Birla",
#        "TATA AIG",
#        "Bajaj Allianz",
#        "SBI General",
#        "Royal Sundaram",
#    ]
    status_list = [
        "To be reviewed by coinsurance hub",
        "Needs clarification from RO or OO",
        "To be approved in GC Core",
        "To be considered for settlement",
        "Settled",
        "No longer valid",
    ]

    regional_office_code = StringField("Enter Regional Office Code:")
    oo_code = StringField("Enter operating office code:")
    coinsurer_name = SelectField("Enter coinsurer name:", choices=coinsurer_list)
    coinsurer_office_code = StringField("Enter Coinsurer office code:")

    type_of_transaction = SelectField(
        "Select whether leader or follower:", choices=["Leader", "Follower"]
    )
    name_of_insured = StringField("Enter name of insured")
    request_id = StringField("Enter Request ID")
    statement = FileField("Upload statement")
    confirmation = FileField("Upload confirmation")
    payable_amount = IntegerField("Enter payable amount:", validators=[Optional()])
    receivable_amount = IntegerField(
        "Enter receivable amount:", validators=[Optional()]
    )

    bool_reinsurance = BooleanField("Whether Reinsurance is involved: ", validators=[Optional()])
    int_ri_payable_amount = IntegerField(
        "Enter Reinsurance payable amount", validators=[Optional()]
    )
    int_ri_receivable_amount = IntegerField(
        "Enter Reinsurance receivable amount", validators=[Optional()]
    )
    ri_confirmation = FileField("Upload RI confirmation", validators=[Optional()])

    remarks = TextAreaField("Enter remarks")
    current_status = SelectField(
        "Current status:", choices=status_list, validators=[Optional()]
    )
    settlement = SelectField(
        "Update settlement details:", choices=[], validators=[Optional()], validate_choice=False
    )


class SettlementForm(FlaskForm):
    coinsurer_name = SelectField("Enter coinsurer name:", choices=coinsurer_list)
    date_of_settlement = DateField("Date of settlement:")
    amount_settled = IntegerField("Amount settled")
    utr_number = StringField("UTR number:")
    settlement_file = FileField("Upload summary statement:")
    type_of_settlement = SelectField(
        "Paid or received: ", choices=["Paid","Received"], validators=[Optional()]
    )
