from extensions import db

class BRS(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    uiic_regional_code = db.Column(db.String)
    uiic_office_code = db.Column(db.String)

    financial_year = db.Column(db.String)
    month = db.Column(db.String)

    cash_bank = db.Column(db.String)
    cheque_bank = db.Column(db.String)
    pos_bank = db.Column(db.String)
    pg_bank = db.Column(db.String)

    cash_brs_id = db.Column(db.Integer)
    cheque_brs_id = db.Column(db.Integer)
    pos_brs_id = db.Column(db.Integer)
    pg_brs_id = db.Column(db.Integer)
    brs_month = db.relationship('BRS_month', backref='brs', lazy='dynamic')
    timestamp = db.Column(db.DateTime)

class BRS_month(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    brs_id = db.Column(db.Integer, db.ForeignKey('brs.id'))
    brs_type = db.Column(db.String)

    int_opening_balance = db.Column(db.Numeric(10,2))
    int_opening_on_hand = db.Column(db.Numeric(10,2))
    int_transactions = db.Column(db.Numeric(10,2))
    int_cancellations = db.Column(db.Numeric(10,2))
    int_fund_transfer = db.Column(db.Numeric(10,2))
    int_bank_charges = db.Column(db.Numeric(10,2))
    int_closing_on_hand = db.Column(db.Numeric(10,2))
    int_closing_balance = db.Column(db.Numeric(10,2))
    file_outstanding_entries = db.Column(db.String)
    timestamp = db.Column(db.DateTime)
    status = db.Column(db.String)
    brs_outstanding = db.relationship('Outstanding', backref='brs_month', lazy='dynamic')

class Outstanding(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    brs_month_id = db.Column(db.Integer, db.ForeignKey('brs_month.id'))

    cheque_number = db.Column(db.String)
    cheque_amount = db.Column(db.Numeric(10,2))
    cheque_date = db.Column(db.Date)