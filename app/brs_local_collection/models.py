from datetime import date
from typing import Optional

from flask import abort
from sqlalchemy.orm import Mapped, mapped_column
from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class BankReconLocalCollectionSummary(db.Model):
    id: Mapped[IntPK]

    regional_office: Mapped[str]
    operating_office: Mapped[str]

    month: Mapped[str]

    purpose_of_bank_account: Mapped[str]  # Local collection or PMSBY

    local_collection_bank_name: Mapped[str]
    local_collection_bank_branch_name: Mapped[Optional[str]]
    local_collection_bank_branch_location: Mapped[Optional[str]]
    local_collection_bank_account_type: Mapped[Optional[str]]
    local_collection_bank_account_number: Mapped[str]
    local_collection_bank_ifsc_code: Mapped[Optional[str]]

    local_collection_brs_month_id: Mapped[Optional[int]]

    details: Mapped[list["BankReconLocalCollectionDetails"]] = db.relationship(
        back_populates="summary"
    )

    # meta
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    def has_access(self, user) -> bool:
        role = user.user_type

        if role in ["admin"]:
            return True

        if role in ["ro_user"]:
            return user.ro_code == self.regional_office
        if role in ["oo_user"]:
            return user.oo_code == self.operating_office

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)

    def mark_deleted(self):
        self.local_collection_brs_month_id = None
        for detail in self.details:
            detail.status = "Deleted"


class BankReconLocalCollectionDetails(db.Model):
    id: Mapped[IntPK]
    brs_id: Mapped[int] = mapped_column(
        db.ForeignKey("bank_recon_local_collection_summary.id")
    )

    summary: Mapped["BankReconLocalCollectionSummary"] = db.relationship(
        back_populates="details"
    )

    opening_balance: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    opening_on_hand: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    transactions: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    cancellations: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    fund_transfer: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    bank_charges: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    closing_on_hand: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    closing_balance: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)

    deposited_not_credited: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    short_credited: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    excess_credited: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    balance_as_per_bank: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)

    bank_statement: Mapped[Optional[str]]
    remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    prepared_by_employee_name: Mapped[str]
    prepared_by_employee_number: Mapped[str]
    brs_outstanding: Mapped[list["BankReconLocalCollectionOutstanding"]] = (
        db.relationship(back_populates="details", cascade="all, delete-orphan")
    )
    brs_short_credit: Mapped[list["BankReconLocalCollectionShortCredit"]] = (
        db.relationship(back_populates="details", cascade="all, delete-orphan")
    )
    brs_excess_credit: Mapped[list["BankReconLocalCollectionExcessCredit"]] = (
        db.relationship(back_populates="details", cascade="all, delete-orphan")
    )
    # meta
    status: Mapped[str] = mapped_column(default="Active")
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    @property
    def balance_before_fund_transfer(self):
        amount = (
            self.opening_balance
            + self.opening_on_hand
            + self.transactions
            - self.cancellations
        )
        return amount


class BankReconLocalCollectionOutstanding(db.Model):
    id: Mapped[IntPK]
    brs_details_id: Mapped[int] = mapped_column(
        db.ForeignKey("bank_recon_local_collection_details.id")
    )

    mode_of_collection: Mapped[str]  # cash, cheque, NEFT, etc
    instrument_number: Mapped[Optional[str]]
    instrument_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))
    date_of_instrument: Mapped[Optional[date]]
    date_of_collection: Mapped[date]
    remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    details: Mapped["BankReconLocalCollectionDetails"] = db.relationship(
        back_populates="brs_outstanding"
    )
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class BankReconLocalCollectionShortCredit(db.Model):
    id: Mapped[IntPK]
    brs_details_id: Mapped[int] = mapped_column(
        db.ForeignKey("bank_recon_local_collection_details.id")
    )

    mode_of_collection: Mapped[str]  # cash, cheque, NEFT, etc
    instrument_number: Mapped[Optional[str]]
    instrument_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))
    date_of_instrument: Mapped[Optional[date]]
    date_of_collection: Mapped[date]
    remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    details: Mapped["BankReconLocalCollectionDetails"] = db.relationship(
        back_populates="brs_short_credit"
    )
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class BankReconLocalCollectionExcessCredit(db.Model):
    id: Mapped[IntPK]
    brs_details_id: Mapped[int] = mapped_column(
        db.ForeignKey("bank_recon_local_collection_details.id")
    )

    mode_of_collection: Mapped[str]  # cash, cheque, NEFT, etc
    instrument_number: Mapped[Optional[str]]
    instrument_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))
    date_of_instrument: Mapped[Optional[date]]
    date_of_collection: Mapped[date]
    remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    details: Mapped["BankReconLocalCollectionDetails"] = db.relationship(
        back_populates="brs_excess_credit"
    )
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
