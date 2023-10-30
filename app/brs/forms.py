from flask_wtf import FlaskForm
from wtforms import BooleanField, FileField, DecimalField, IntegerField
from wtforms.validators import Optional

class BRSForm(FlaskForm):
    cash_brs_file = FileField("Upload cash BRS")
    cheque_brs_file = FileField("Upload Cheque BRS")
    pos_brs_file = FileField("Upload POS BRS")
    pg_brs_file = FileField("Upload PG BRS")
    delete_cash_brs = BooleanField("Delete cash BRS")
    delete_cheque_brs = BooleanField("Delete cheque BRS")
    delete_pos_brs = BooleanField("Delete POS BRS")
    delete_pg_brs = BooleanField("Delete PG BRS")

class BRS_entry(FlaskForm):
    opening_balance = DecimalField("Enter opening balance", validators=[Optional()])
    opening_on_hand = DecimalField("Add: Enter cash/cheques on hand", validators=[Optional()])
    transactions = DecimalField("Add: Enter collections during the month", validators=[Optional()])
    cancellations = DecimalField("Less: Cancellations / dishonours during the month", validators=[Optional()])
    fund_transfer = DecimalField("Less: Fund transfer", validators=[Optional()])
    bank_charges = DecimalField("Less: Bank charges", validators=[Optional()])
    closing_on_hand = DecimalField("Less: Enter cash/cheques on hand", validators=[Optional()])
    outstanding_entries = FileField("Upload outstanding cheque entries:", validators=[Optional()])
