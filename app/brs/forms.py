from flask_wtf import FlaskForm
from wtforms import BooleanField, FileField

class BRSForm(FlaskForm):
    cash_brs_file = FileField("Upload cash BRS")
    cheque_brs_file = FileField("Upload Cheque BRS")
    pos_brs_file = FileField("Upload POS BRS")
    pg_brs_file = FileField("Upload PG BRS")
    delete_cash_brs = BooleanField("Delete cash BRS")
    delete_cheque_brs = BooleanField("Delete cheque BRS")
    delete_pos_brs = BooleanField("Delete POS BRS")
    delete_pg_brs = BooleanField("Delete PG BRS")
