from extensions import db


class Contracts(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    vendor = db.Column(db.String)
    purpose = db.Column(db.String)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String)
    emd = db.Column(db.Integer)
    renewal = db.Column(db.String)
    notice_period = db.Column(db.String)

    remarks = db.Column(db.String)
    contract_file = db.Column(db.String)
