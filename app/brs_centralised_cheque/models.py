from dataclasses import dataclass
from datetime import datetime

from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.orm import column_property

from extensions import db


@dataclass
class CentralisedChequeSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    regional_office_code: str = db.Column(db.String)
    operating_office_code: str = db.Column(db.String)

    date_of_month = db.Column(db.Date)

    centralised_cheque_bank: str = db.Column(db.String)
    centralised_cheque_brs_id = db.Column(db.Integer)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)

    details = db.relationship(
        "CentralisedChequeDetails", backref="summary", lazy="select"
    )

    month = column_property(func.to_char(date_of_month, "FMMonth-YYYY"))


class CentralisedChequeDetails(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    summary_id = db.Column(db.Integer, db.ForeignKey("centralised_cheque_summary.id"))
    opening_balance_unencashed = db.Column(db.Numeric(15, 2))
    opening_balance_stale = db.Column(db.Numeric(15, 2))
    cheques_issued = db.Column(db.Numeric(15, 2))
    cheques_reissued = db.Column(db.Numeric(15, 2))
    cheques_cleared = db.Column(db.Numeric(15, 2))
    cheques_cancelled = db.Column(db.Numeric(15, 2))
    closing_balance_unencashed = db.Column(db.Numeric(15, 2))
    closing_balance_stale = db.Column(db.Numeric(15, 2))

    remarks = db.Column(db.Text)

    prepared_by_employee_name = db.Column(db.String)
    prepared_by_employee_number = db.Column(db.String)

    brs_status = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)

    unencashed_cheques = db.relationship(
        "CentralisedChequeInstrumentUnencashedDetails",
        backref="instrument_unencashed_details",
        lazy="dynamic",
    )

    stale_cheques = db.relationship(
        "CentralisedChequeInstrumentStaleDetails",
        backref="instrument_stale_details",
        lazy="dynamic",
    )


class CentralisedChequeInstrumentStaleDetails(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)

    voucher_number = db.Column(db.String)
    voucher_date = db.Column(db.Date)
    transaction_id = db.Column(db.String)
    instrument_number = db.Column(db.String)
    instrument_date = db.Column(db.Date)
    instrument_amount = db.Column(db.Numeric(15, 2))
    payee_name = db.Column(db.String)

    remarks = db.Column(db.Text)
    instrument_status = db.Column(db.String)

    centralised_cheque_details_id = db.Column(
        db.Integer, db.ForeignKey("centralised_cheque_details.id")
    )

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


class CentralisedChequeInstrumentUnencashedDetails(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)

    voucher_number = db.Column(db.String)
    voucher_date = db.Column(db.Date)
    transaction_id = db.Column(db.String)
    instrument_number = db.Column(db.String)
    instrument_date = db.Column(db.Date)
    instrument_amount = db.Column(db.Numeric(15, 2))
    payee_name = db.Column(db.String)

    remarks = db.Column(db.Text)
    instrument_status = db.Column(db.String)

    centralised_cheque_details_id = db.Column(
        db.Integer, db.ForeignKey("centralised_cheque_details.id")
    )

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


class CentralisedChequeEnableDelete(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_of_month = db.Column(db.Date)
    enable_delete = db.Column(db.Boolean, default=True)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)
