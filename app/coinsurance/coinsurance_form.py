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
    status_list = [
        "To be reviewed by coinsurance hub",
        "Needs clarification from RO/OO",
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
    request_id = StringField("Enter Request ID")
    statement = FileField("Upload statement")
    confirmation = FileField("Upload confirmation")
    payable_amount = IntegerField("Enter payable amount:", validators=[Optional()])
    receivable_amount = IntegerField(
        "Enter receivable amount:", validators=[Optional()]
    )

    bool_reinsurance = BooleanField("Whether RI is involved: ", validators=[Optional()])
    int_ri_payable_amount = IntegerField(
        "Enter RI payable amount", validators=[Optional()]
    )
    int_ri_receivable_amount = IntegerField(
        "Enter RI receivable amount", validators=[Optional()]
    )
    ri_confirmation = FileField("Upload RI confirmation", validators=[Optional()])

    remarks = TextAreaField("Enter remarks")
    current_status = SelectField(
        "Current status:", choices=status_list, validators=[Optional()]
    )
    settlement = SelectField(
        "Update settlement details:", choices=status_list, validators=[Optional()]
    )


class SettlementForm(FlaskForm):
    coinsurer_name = SelectField("Enter coinsurer name:", choices=coinsurer_list)
    # coinsurance_keys = StringField()
    date_of_settlement = DateField("Date of settlement:")
    amount_settled = IntegerField("Amount settled")
    utr_number = StringField("UTR number:")
    settlement_file = FileField("Upload summary statement:")
    settlement_list = ["Paid", "Received"]
    type_of_settlement = SelectField(
        "Paid or received: ", choices=settlement_list, validators=[Optional()]
    )


# class SignupForm(FlaskForm):
#    username = StringField("Username", validators=[DataRequired()])
#    password = PasswordField("Password", validators=[DataRequired()])
#    emp_number = IntegerField(
#        "Employee number",
#        validators=[NumberRange(min=10000, max=99999), DataRequired()],
#    )
#
#
# class LoginForm(FlaskForm):
#    username = StringField("Username", validators=[DataRequired()])
#    password = PasswordField("Password", validators=[DataRequired()])
#
#
# class UpdateUserForm(FlaskForm):
#    is_admin = BooleanField("Make the user admin: ")
#    reset_password_page = BooleanField("Enable password reset page: ")
#
#
# class ResetPasswordForm(FlaskForm):
#    username = StringField("Enter username:", validators=[DataRequired()])
#    emp_number = IntegerField("Enter employee number: ", validators=[DataRequired()])
#    #  reset_code = IntegerField("Enter reset code received from admin: ", validators=[DataRequired()])
#    password = PasswordField("Enter new password: ", validators=[DataRequired()])
