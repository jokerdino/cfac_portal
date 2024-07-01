from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FileField,
    DecimalField,
    IntegerField,
    TextAreaField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, NumberRange


class BRSForm(FlaskForm):
    delete_cash_brs = BooleanField("Delete cash BRS")
    delete_cheque_brs = BooleanField("Delete cheque BRS")
    delete_pos_brs = BooleanField("Delete POS BRS")
    delete_pg_brs = BooleanField("Delete PG BRS")
    delete_bbps_brs = BooleanField("Delete BBPS BRS")
    delete_local_collection_brs = BooleanField("Delete local collection BRS")


class BRS_entry(FlaskForm):
    opening_balance = DecimalField("Opening balance as per GL", validators=[Optional()])
    opening_on_hand = DecimalField(
        "Add: Opening cash/cheques on hand", validators=[Optional()]
    )
    transactions = DecimalField(
        "Add: Collections during the month", validators=[Optional()]
    )
    cancellations = DecimalField(
        "Less: Cancellations / dishonours during the month", validators=[Optional()]
    )
    fund_transfer = DecimalField("Less: Fund transfer", validators=[Optional()])
    bank_charges = DecimalField("Less: Bank charges", validators=[Optional()])
    closing_on_hand = DecimalField(
        "Less: Closing cash/cheques on hand", validators=[Optional()]
    )
    int_deposited_not_credited = DecimalField(
        "Less: Deposited but not credited", validators=[Optional()]
    )
    int_short_credited = DecimalField("Less: Short credit", validators=[Optional()])
    int_excess_credited = DecimalField("Add: Excess credit", validators=[Optional()])

    file_outstanding_entries = FileField(
        "Upload details of entries which are deposited but not credited in prescribed format:",
        validators=[Optional()],
    )
    file_short_credit_entries = FileField(
        "Upload details of short credit entries in prescribed format:",
        validators=[Optional()],
    )
    file_excess_credit_entries = FileField(
        "Upload details of Excess credit in prescribed format:",
        validators=[Optional()],
    )
    remarks = TextAreaField("Enter remarks:", validators=[Optional()])
    prepared_by = StringField("Prepared by:", validators=[DataRequired()])
    prepared_by_employee_number = IntegerField(
        "Employee number",
        validators=[NumberRange(min=10000, max=99999), DataRequired()],
    )


class DashboardForm(FlaskForm):
    month = SelectField("Select month")


class RawDataForm(FlaskForm):
    month = SelectField("Select month")
    brs_type = SelectField(
        "Select BRS type",
        choices=[
            ("cash", "Cash"),
            ("cheque", "Cheque"),
            ("pg", "PG"),
            ("pos", "POS"),
            ("bbps", "BBPS"),
            ("local_collection", "Local collection"),
        ],
    )


class EnableDeleteMonthForm(FlaskForm):
    txt_month = StringField("Month", validators=[DataRequired()])
    bool_enable_delete = BooleanField(
        "Enable month for deletion", validators=[Optional()]
    )
    submit = SubmitField("Submit")
