from flask_wtf import FlaskForm
from wtforms import FileField

class BRSForm(FlaskForm):
    cash_brs_file = FileField("Upload cash BRS")
    cheque_brs_file = FileField("Upload Cheque BRS")
    pos_brs_file = FileField("Upload POS BRS")
    pg_brs_file = FileField("Upload PG BRS")
