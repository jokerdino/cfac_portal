from extensions import db

class BRS(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    uiic_regional_code = db.Column(db.String)
    uiic_office_code = db.Column(db.String)

    financial_year = db.Column(db.String)
    month = db.Column(db.String)

    cash_bank = db.Column(db.String)
    cash_brs_file = db.Column(db.String)

    cheque_bank = db.Column(db.String)
    cheque_brs_file = db.Column(db.String)

    pos_bank = db.Column(db.String)
    pos_brs_file = db.Column(db.String)

    pg_bank = db.Column(db.String)
    pg_brs_file = db.Column(db.String)
