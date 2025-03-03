from datetime import datetime
from dataclasses import dataclass, field
from extensions import db

from flask_login import current_user

from sqlalchemy import func
from sqlalchemy.orm import column_property


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

    month = column_property(func.to_char(value_date, "YYYY-MM"))
    month_string = column_property(func.to_char(value_date, "Mon-YY"))


@dataclass
class PoolCreditsPortal(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)

    txt_reference_number = db.Column(db.String)
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
    reference_number: str = field(init=False)

    @property
    def office_code(self):
        return "000100"

    @property
    def reference_number(self):
        return self.txt_reference_number.replace(" 00:00:00", "")


class PoolCreditsJournalVoucher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    str_regional_office_code = db.Column(db.String, unique=True)
    gl_code = db.Column(db.String)
    sl_code = db.Column(db.String)

    created_on = db.Column(db.DateTime, default=datetime.now)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
