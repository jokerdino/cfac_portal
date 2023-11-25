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


class BRSForm(FlaskForm):
    delete_cash_brs = BooleanField("Delete cash BRS")
    delete_cheque_brs = BooleanField("Delete cheque BRS")
    delete_pos_brs = BooleanField("Delete POS BRS")
    delete_pg_brs = BooleanField("Delete PG BRS")
    delete_bbps_brs = BooleanField("Delete BBPS BRS")
    delete_local_collection_brs = BooleanField("Delete local collection BRS")


class BRS_entry(FlaskForm):
    opening_balance = DecimalField("Enter opening balance", validators=[Optional()])
    opening_on_hand = DecimalField(
        "Add: Enter cash/cheques on hand", validators=[Optional()]
    )
    transactions = DecimalField(
        "Add: Enter collections during the month", validators=[Optional()]
    )
    cancellations = DecimalField(
        "Less: Cancellations / dishonours during the month", validators=[Optional()]
    )
    fund_transfer = DecimalField("Less: Fund transfer", validators=[Optional()])
    bank_charges = DecimalField("Less: Bank charges", validators=[Optional()])
    closing_on_hand = DecimalField(
        "Less: Enter cash/cheques on hand", validators=[Optional()]
    )
    outstanding_entries = FileField(
        "Upload details of closing balance in prescribed format:",
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
