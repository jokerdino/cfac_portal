# from dataclasses import dataclass
from datetime import date
from typing import Optional

# from flask_login import current_user
# from sqlalchemy import func
from sqlalchemy.orm import column_property, mapped_column, Mapped

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class CentralisedChequeSummary(db.Model):
    id: Mapped[IntPK]
    regional_office_code: Mapped[str]
    operating_office_code: Mapped[str]

    date_of_month: Mapped[date] = mapped_column(db.Date)

    centralised_cheque_bank: Mapped[str]
    centralised_cheque_brs_id: Mapped[Optional[int]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    details: Mapped["CentralisedChequeDetails"] = db.relationship(
        back_populates="summary"
    )

    month: Mapped[str] = column_property(db.func.to_char(date_of_month, "FMMonth-YYYY"))


class CentralisedChequeDetails(db.Model):
    id: Mapped[IntPK]
    summary_id: Mapped[int] = mapped_column(
        db.ForeignKey("centralised_cheque_summary.id")
    )
    opening_balance_unencashed: Mapped[float] = mapped_column(db.Numeric(15, 2))
    cheques_issued: Mapped[float] = mapped_column(db.Numeric(15, 2))
    cheques_reissued_unencashed: Mapped[float] = mapped_column(db.Numeric(15, 2))
    opening_balance_stale: Mapped[float] = mapped_column(db.Numeric(15, 2))
    cheques_reissued_stale: Mapped[float] = mapped_column(db.Numeric(15, 2))
    cheques_cleared: Mapped[float] = mapped_column(db.Numeric(15, 2))
    cheques_cancelled: Mapped[float] = mapped_column(db.Numeric(15, 2))
    closing_balance_unencashed: Mapped[float] = mapped_column(db.Numeric(15, 2))
    closing_balance_stale: Mapped[float] = mapped_column(db.Numeric(15, 2))

    remarks: Mapped[str] = mapped_column(db.Text)

    prepared_by_employee_name: Mapped[str]
    prepared_by_employee_number: Mapped[str]

    brs_status: Mapped[Optional[str]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
    summary: Mapped["CentralisedChequeSummary"] = db.relationship(
        back_populates="details"
    )

    unencashed_cheques: Mapped[list["CentralisedChequeInstrumentUnencashedDetails"]] = (
        db.relationship(
            back_populates="details",
            lazy="dynamic",
        )
    )

    stale_cheques: Mapped[list["CentralisedChequeInstrumentStaleDetails"]] = (
        db.relationship(
            back_populates="details",
            lazy="dynamic",
        )
    )


class CentralisedChequeInstrumentStaleDetails(db.Model):
    id: Mapped[IntPK]

    voucher_number: Mapped[str]
    voucher_date: Mapped[date]
    transaction_id: Mapped[str]
    instrument_number: Mapped[str]
    instrument_date: Mapped[date]
    instrument_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))
    payee_name: Mapped[str]

    remarks: Mapped[str] = mapped_column(db.Text)
    instrument_status: Mapped[Optional[str]]

    centralised_cheque_details_id: Mapped[int] = mapped_column(
        db.ForeignKey("centralised_cheque_details.id")
    )
    details: Mapped["CentralisedChequeDetails"] = db.relationship(
        back_populates="stale_cheques"
    )

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class CentralisedChequeInstrumentUnencashedDetails(db.Model):
    id: Mapped[IntPK]

    voucher_number: Mapped[str]
    voucher_date: Mapped[date]
    transaction_id: Mapped[str]
    instrument_number: Mapped[str]
    instrument_date: Mapped[date]
    instrument_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))
    payee_name: Mapped[str]

    remarks: Mapped[str] = mapped_column(db.Text)
    instrument_status: Mapped[Optional[str]]

    centralised_cheque_details_id: Mapped[int] = mapped_column(
        db.ForeignKey("centralised_cheque_details.id")
    )
    details: Mapped["CentralisedChequeDetails"] = db.relationship(
        back_populates="unencashed_cheques"
    )

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class CentralisedChequeEnableDelete(db.Model):
    id: Mapped[IntPK]
    date_of_month: Mapped[date]
    enable_delete: Mapped[bool] = mapped_column(default=True)

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
