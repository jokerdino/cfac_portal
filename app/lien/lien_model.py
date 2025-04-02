from datetime import datetime

from flask_login import current_user
from extensions import db


class Lien(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ro_code = db.Column(db.String)
    ro_name = db.Column(db.String)

    court_name = db.Column(db.String)
    case_number = db.Column(db.String)
    petitioner_name = db.Column(db.String)
    date_of_order = db.Column(db.Date)

    lien_amount = db.Column(db.Numeric(15, 2))
    dd_amount = db.Column(db.Numeric(15, 2))

    action_taken_by_banker = db.Column(db.Text)

    bank_name = db.Column(db.String)
    account_number = db.Column(db.String)

    bank_remarks = db.Column(db.Text)
    ro_remarks = db.Column(db.Text)

    lien_status = db.Column(db.String)

    court_order_lien = db.Column(db.String)
    court_order_dd = db.Column(db.String)
    court_order_lien_reversal = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)
