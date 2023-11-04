from flask_wtf import FlaskForm
from wtforms import BooleanField, FileField, DecimalField, IntegerField, SelectField
from wtforms.validators import Optional

class BRSForm(FlaskForm):


    delete_cash_brs = BooleanField("Delete cash BRS")
    delete_cheque_brs = BooleanField("Delete cheque BRS")
    delete_pos_brs = BooleanField("Delete POS BRS")
    delete_pg_brs = BooleanField("Delete PG BRS")
    delete_bbps_brs = BooleanField("Delete BBPS BRS")

class BRS_entry(FlaskForm):
    opening_balance = DecimalField("Enter opening balance", validators=[Optional()])
    opening_on_hand = DecimalField("Add: Enter cash/cheques on hand", validators=[Optional()])
    transactions = DecimalField("Add: Enter collections during the month", validators=[Optional()])
    cancellations = DecimalField("Less: Cancellations / dishonours during the month", validators=[Optional()])
    fund_transfer = DecimalField("Less: Fund transfer", validators=[Optional()])
    bank_charges = DecimalField("Less: Bank charges", validators=[Optional()])
    closing_on_hand = DecimalField("Less: Enter cash/cheques on hand", validators=[Optional()])
    outstanding_entries = FileField("Upload outstanding cheque entries:", validators=[Optional()])

class DashboardForm(FlaskForm):
    month = SelectField("Select month")#, choices=["All"])
