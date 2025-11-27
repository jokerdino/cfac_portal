from datetime import date
from typing import Optional

from flask import abort
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class BRS(db.Model):
    # TODO: Enable row level security
    id: Mapped[IntPK]
    uiic_regional_code: Mapped[str]
    uiic_office_code: Mapped[str]

    financial_year: Mapped[str]
    month: Mapped[str]

    cash_bank: Mapped[Optional[str]]
    cheque_bank: Mapped[Optional[str]]
    pos_bank: Mapped[Optional[str]]
    pg_bank: Mapped[Optional[str]]
    bbps_bank: Mapped[Optional[str]]
    dqr_bank: Mapped[Optional[str]]
    local_collection_bank: Mapped[Optional[str]]

    cash_brs_id: Mapped[Optional[int]]
    cheque_brs_id: Mapped[Optional[int]]
    pos_brs_id: Mapped[Optional[int]]
    pg_brs_id: Mapped[Optional[int]]
    bbps_brs_id: Mapped[Optional[int]]
    dqr_brs_id: Mapped[Optional[int]]
    local_collection_brs_id: Mapped[Optional[int]]

    brs_month: Mapped["BRSMonth"] = db.relationship(
        back_populates="brs", cascade="all, delete-orphan"
    )
    timestamp: Mapped[CreatedOn]

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
    id: Mapped[IntPK]
    txt_month: Mapped[str]
    bool_enable_delete: Mapped[bool] = mapped_column(default=True)

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class BRSMonth(db.Model):
    id: Mapped[IntPK]
    brs_id: Mapped[int] = mapped_column(db.ForeignKey("brs.id"))
    brs_type: Mapped[str]

    int_opening_balance: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    int_opening_on_hand: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    int_transactions: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    int_cancellations: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    int_fund_transfer: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    int_bank_charges: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    int_closing_on_hand: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    int_closing_balance: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)

    int_deposited_not_credited: Mapped[float] = mapped_column(
        db.Numeric(15, 2), default=0
    )
    int_short_credited: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    int_excess_credited: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)

    int_balance_as_per_bank: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)

    timestamp: Mapped[CreatedOn]
    status: Mapped[Optional[str]]
    brs_outstanding: Mapped[list["Outstanding"]] = db.relationship(
        back_populates="brs_month", cascade="all, delete-orphan"
    )
    brs_short_credit: Mapped[list["BankReconShortCredit"]] = db.relationship(
        back_populates="brs_month", cascade="all, delete-orphan"
    )
    brs_excess_credit: Mapped[list["BankReconExcessCredit"]] = db.relationship(
        back_populates="brs_month", cascade="all, delete-orphan"
    )
    remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    prepared_by: Mapped[str]
    prepared_by_employee_number: Mapped[str]

    brs: Mapped["BRS"] = db.relationship(back_populates="brs_month")



class Outstanding(db.Model):
    id: Mapped[IntPK]
    brs_month_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("brs_month.id"))

    # instrument number and date of instrument is optional for cash alone.
    # other modes of collection must provide all the columns
    instrument_number: Mapped[Optional[str]]
    instrument_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))
    date_of_instrument: Mapped[Optional[date]]
    date_of_collection: Mapped[Optional[date]]
    remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    brs_month: Mapped["BRSMonth"] = db.relationship(back_populates="brs_outstanding")

class BankReconShortCredit(db.Model):
    id: Mapped[IntPK]
    brs_month_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("brs_month.id"))

    # instrument number and date of instrument is optional for cash alone.
    # other modes of collection must provide all the columns
    instrument_number: Mapped[Optional[str]]
    instrument_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))
    date_of_instrument: Mapped[Optional[date]]
    date_of_collection: Mapped[date]
    remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    brs_month: Mapped["BRSMonth"] = db.relationship(back_populates="brs_short_credit")

class BankReconExcessCredit(db.Model):
    id: Mapped[IntPK]
    brs_month_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("brs_month.id"))

    # instrument number and date of instrument is optional for cash alone.
    # other modes of collection must provide all the columns
    instrument_number: Mapped[Optional[str]]
    instrument_amount: Mapped[float] = db.Column(db.Numeric(15, 2))
    date_of_instrument: Mapped[Optional[date]]
    date_of_collection: Mapped[date]
    remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    brs_month: Mapped["BRSMonth"] = db.relationship(back_populates="brs_excess_credit")

class BankReconAccountDetails(db.Model):
    id: Mapped[IntPK]
    str_name_of_bank: Mapped[str]
    str_brs_type: Mapped[str]

    str_bank_account_number: Mapped[str]
    str_ifsc_code: Mapped[str]
