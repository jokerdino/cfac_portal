from dataclasses import dataclass
from datetime import datetime
from extensions import db

from flask_login import current_user


@dataclass
class HeadOfficeAccountsTracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    str_work: str = db.Column(db.String)
    str_period = db.Column(db.String)
    str_person: str = db.Column(db.String)

    # user inputs
    bool_current_status = db.Column(db.Boolean)
    text_remarks = db.Column(db.Text)

    # meta data
    date_created_date = db.Column(db.DateTime, default=datetime.now)
    date_updated_date = db.Column(db.DateTime, onupdate=datetime.now)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    deleted_by = db.Column(db.String)


@dataclass
class HeadOfficeBankReconTracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    str_period = db.Column(db.String)

    str_name_of_bank: str = db.Column(db.String)
    str_bank_address: str = db.Column(db.String)

    str_purpose: str = db.Column(db.String)
    str_person: str = db.Column(db.String)

    str_gl_code: str = db.Column(db.String)
    str_sl_code: str = db.Column(db.String)

    str_bank_account_number: str = db.Column(db.String)
    str_customer_id: str = db.Column(db.String)

    # user inputs
    boolean_mis_shared = db.Column(db.Boolean)
    str_brs_file_upload = db.Column(db.String)
    boolean_jv_passed = db.Column(db.Boolean)
    str_bank_confirmation_file_upload = db.Column(db.String)
    text_remarks = db.Column(db.Text)

    # meta data
    date_created_date = db.Column(db.DateTime, default=datetime.now)
    date_updated_date = db.Column(db.DateTime, onupdate=datetime.now)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    deleted_by = db.Column(db.String)
