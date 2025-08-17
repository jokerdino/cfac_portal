from datetime import datetime

from sqlalchemy.orm import validates
from sqlalchemy_continuum.plugins import FlaskPlugin
from sqlalchemy_continuum import make_versioned
from flask_login import current_user


from extensions import db

from .lien_forms import ALLOWED_RO_CODES

make_versioned(plugins=[FlaskPlugin()])


class Lien(db.Model):
    __versioned__ = {}
    id = db.Column(db.Integer, primary_key=True)

    bank_name = db.Column(db.String)
    account_number = db.Column(db.String)

    ro_name = db.Column(db.String)
    ro_code = db.Column(db.String)
    lien_amount = db.Column(db.Numeric(15, 2))
    lien_date = db.Column(db.Date)
    court_order_lien = db.Column(db.String)

    dd_amount = db.Column(db.Numeric(15, 2))
    dd_date = db.Column(db.Date)
    court_order_dd = db.Column(db.String)
    bank_remarks = db.Column(db.Text)
    action_taken_by_banker = db.Column(db.Text)

    department = db.Column(db.String)
    court_name = db.Column(db.String)
    case_number = db.Column(db.String)
    case_title = db.Column(db.String)
    petitioner_name = db.Column(db.String)

    date_of_lien_order = db.Column(db.Date)
    claim_already_paid_by_hub_office = db.Column(db.String)
    claim_number = db.Column(db.String)
    date_of_claim_registration = db.Column(db.Date)
    claim_disbursement_voucher = db.Column(db.String)

    lien_dd_reversal_order = db.Column(db.String)
    lien_status = db.Column(db.String)
    appeal_given = db.Column(db.String)
    appeal_copy = db.Column(db.String)
    stay_obtained = db.Column(db.String)
    stay_order = db.Column(db.String)
    claim_accounting_voucher_number = db.Column(db.String)

    claim_accounting_voucher_date = db.Column(db.Date)

    ro_remarks = db.Column(db.Text)
    ho_tp_remarks = db.Column(db.Text)

    court_order_lien_reversal = db.Column(db.String)
    court_order_dd_reversal = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)

    @validates("ro_code")
    def validate_ro_code(self, key, value):
        if value not in ALLOWED_RO_CODES:
            raise ValueError(f"Invalid RO code: {value}. Allowed: {ALLOWED_RO_CODES}")
        return value


db.configure_mappers()
