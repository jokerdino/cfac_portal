from datetime import date
from typing import Optional

from flask import abort
from sqlalchemy.orm import mapped_column, Mapped

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class BankReconImprestSummary(db.Model):
    id: Mapped[IntPK]
    regional_office: Mapped[str]
    operating_office: Mapped[str]
    month: Mapped[str]

    purpose_of_bank_account: Mapped[str]

    imprest_bank_name: Mapped[str]
    imprest_bank_branch_name: Mapped[Optional[str]]
    imprest_bank_branch_location: Mapped[Optional[str]]
    imprest_bank_account_type: Mapped[Optional[str]]
    imprest_bank_account_number: Mapped[str]
    imprest_bank_ifsc_code: Mapped[Optional[str]]

    imprest_brs_month_id: Mapped[Optional[int]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    details: Mapped[list["BankReconImprestDetails"]] = db.relationship(
        back_populates="summary"
    )

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
        self.imprest_brs_month_id = None
        for detail in self.details:
            detail.status = "Deleted"


class BankReconImprestDetails(db.Model):
    id: Mapped[IntPK]
    summary_id: Mapped[int] = mapped_column(
        db.ForeignKey("bank_recon_imprest_summary.id")
    )
    opening_balance: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    fund_transfer: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)

    cheques_issued: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    cheques_cancelled: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    bank_charges: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)

    closing_balance_gl: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    cheques_unencashed: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)
    closing_balance_bank: Mapped[float] = mapped_column(db.Numeric(15, 2), default=0)

    remarks: Mapped[str] = mapped_column(db.Text)

    prepared_by_employee_name: Mapped[str]
    prepared_by_employee_number: Mapped[str]

    bank_statement: Mapped[Optional[str]]
    status: Mapped[Optional[str]] = mapped_column(default="Active")

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
    summary: Mapped["BankReconImprestSummary"] = db.relationship(
        back_populates="details"
    )

    unencashed_cheques: Mapped[list["BankReconImprestUnencashedDetails"]] = (
        db.relationship(
            back_populates="details",
            lazy="dynamic",
        )
    )


class BankReconImprestUnencashedDetails(db.Model):
    id: Mapped[IntPK]

    voucher_number: Mapped[str]
    voucher_date: Mapped[date]

    instrument_number: Mapped[str]
    instrument_date: Mapped[date]
    instrument_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))
    payee_name: Mapped[str]

    remarks: Mapped[str] = mapped_column(db.Text)
    instrument_status: Mapped[Optional[str]]

    brs_details_id: Mapped[int] = mapped_column(
        db.ForeignKey("bank_recon_imprest_details.id")
    )
    details: Mapped["BankReconImprestDetails"] = db.relationship(
        back_populates="unencashed_cheques"
    )

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
