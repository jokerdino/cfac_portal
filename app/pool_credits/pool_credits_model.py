from datetime import datetime
from dataclasses import dataclass, field
from extensions import db

from flask_login import current_user


@dataclass
class PoolCredits(db.Model):

    id: int = db.Column(db.Integer, primary_key=True)
    date_uploaded_date = db.Column(db.Date)

    # below columns are uploaded from bank statement excel
    book_date: datetime.date = db.Column(db.Date)
    description: str = db.Column(db.Text)
    ledger_balance = db.Column(db.Numeric(20, 2))
    credit: float = db.Column(db.Numeric(20, 2))
    debit: float = db.Column(db.Numeric(20, 2))
    value_date: datetime.date = db.Column(db.Date)
    reference_no: str = db.Column(db.String)
    transaction_branch: str = db.Column(db.Text)

    # flag description is assigned from our table
    flag_description = db.Column(db.Text)

    # user inputs

    # regional office users will self assign the credits to their RO
    str_regional_office_code: str = db.Column(db.String)
    text_remarks: str = db.Column(db.Text)

    bool_jv_passed: bool = db.Column(db.Boolean, default=False)

    # meta data
    date_created_date = db.Column(db.DateTime, default=datetime.now)
    date_updated_date = db.Column(db.DateTime, onupdate=datetime.now)
    date_deleted_date = db.Column(db.DateTime)
    date_jv_passed_date = db.Column(db.DateTime)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    deleted_by = db.Column(db.String)
    jv_passed_by = db.Column(db.String)


@dataclass
class PoolCreditsPortal(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)

    txt_reference_number: str = db.Column(db.String)
    date_value_date: datetime.date = db.Column(db.Date)
    amount_credit: float = db.Column(db.Numeric(20, 2))
    txt_name_of_remitter: str = db.Column(db.String)

    date_created_date: datetime.time = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)

    office_code: str = field(init=False)

    @property
    def office_code(self):
        return "000100"
