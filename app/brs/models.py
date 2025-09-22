from dataclasses import dataclass
from datetime import datetime

from flask_login import current_user

from extensions import db


@dataclass
class BRS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uiic_regional_code: str = db.Column(db.String)
    uiic_office_code: str = db.Column(db.String)

    financial_year = db.Column(db.String)
    month = db.Column(db.String)

    cash_bank: str = db.Column(db.String)
    cheque_bank: str = db.Column(db.String)
    pos_bank: str = db.Column(db.String)
    pg_bank: str = db.Column(db.String)
    bbps_bank: str = db.Column(db.String)
    dqr_bank: str = db.Column(db.String)
    local_collection_bank: str = db.Column(db.String)

    cash_brs_id = db.Column(db.Integer)
    cheque_brs_id = db.Column(db.Integer)
    pos_brs_id = db.Column(db.Integer)
    pg_brs_id = db.Column(db.Integer)
    bbps_brs_id = db.Column(db.Integer)
    dqr_brs_id = db.Column(db.Integer)
    local_collection_brs_id = db.Column(db.Integer)

    brs_month = db.relationship("BRSMonth", backref="brs", lazy="dynamic")
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def get_bank_for_type(self, brs_type: str) -> str:
        mapping = {
            "cash": self.cash_bank,
            "cheque": self.cheque_bank,
            "pos": self.pos_bank,
            "pg": self.pg_bank,
            "bbps": self.bbps_bank,
            "dqr": self.dqr_bank,
            "local_collection": self.local_collection_bank,
        }
        return mapping.get(brs_type, "")


class DeleteEntries(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    txt_month = db.Column(db.String)
    bool_enable_delete = db.Column(db.Boolean, default=True)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


class BRSMonth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brs_id = db.Column(db.Integer, db.ForeignKey("brs.id"))
    brs_type = db.Column(db.String)

    int_opening_balance = db.Column(db.Numeric(15, 2), default=0)
    int_opening_on_hand = db.Column(db.Numeric(15, 2), default=0)
    int_transactions = db.Column(db.Numeric(15, 2), default=0)
    int_cancellations = db.Column(db.Numeric(15, 2), default=0)
    int_fund_transfer = db.Column(db.Numeric(15, 2), default=0)
    int_bank_charges = db.Column(db.Numeric(15, 2), default=0)
    int_closing_on_hand = db.Column(db.Numeric(15, 2), default=0)
    int_closing_balance = db.Column(db.Numeric(15, 2), default=0)

    int_deposited_not_credited = db.Column(db.Numeric(15, 2), default=0)
    int_short_credited = db.Column(db.Numeric(15, 2), default=0)
    int_excess_credited = db.Column(db.Numeric(15, 2), default=0)

    int_balance_as_per_bank = db.Column(db.Numeric(15, 2), default=0)

    # file_outstanding_entries = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String)
    brs_outstanding = db.relationship(
        "Outstanding", backref="brs_month", lazy="dynamic"
    )
    brs_short_credit = db.relationship(
        "BankReconShortCredit", backref="brs_month", lazy="dynamic"
    )
    brs_excess_credit = db.relationship(
        "BankReconExcessCredit", backref="brs_month", lazy="dynamic"
    )
    remarks = db.Column(db.Text)
    prepared_by = db.Column(db.String)
    prepared_by_employee_number = db.Column(db.String)


class Outstanding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brs_month_id = db.Column(db.Integer, db.ForeignKey("brs_month.id"))

    # instrument number and date of instrument is optional for cash alone.
    # other modes of collection must provide all the columns
    instrument_number = db.Column(db.String)
    instrument_amount = db.Column(db.Numeric(15, 2))
    date_of_instrument = db.Column(db.Date)
    date_of_collection = db.Column(db.Date)
    remarks = db.Column(db.Text)


class BankReconShortCredit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brs_month_id = db.Column(db.Integer, db.ForeignKey("brs_month.id"))

    # instrument number and date of instrument is optional for cash alone.
    # other modes of collection must provide all the columns
    instrument_number = db.Column(db.String)
    instrument_amount = db.Column(db.Numeric(15, 2))
    date_of_instrument = db.Column(db.Date)
    date_of_collection = db.Column(db.Date)
    remarks = db.Column(db.Text)


class BankReconExcessCredit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brs_month_id = db.Column(db.Integer, db.ForeignKey("brs_month.id"))

    # instrument number and date of instrument is optional for cash alone.
    # other modes of collection must provide all the columns
    instrument_number = db.Column(db.String)
    instrument_amount = db.Column(db.Numeric(15, 2))
    date_of_instrument = db.Column(db.Date)
    date_of_collection = db.Column(db.Date)
    remarks = db.Column(db.Text)


class BankReconAccountDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    str_name_of_bank = db.Column(db.String)
    str_brs_type = db.Column(db.String)

    str_bank_account_number = db.Column(db.String)
    str_ifsc_code = db.Column(db.String)
