from datetime import date
from typing import Optional


from flask import abort
from sqlalchemy.orm import validates, mapped_column, Mapped
from sqlalchemy_continuum.plugins import FlaskPlugin
from sqlalchemy_continuum import make_versioned


from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn

from .lien_forms import ALLOWED_RO_CODES

make_versioned(plugins=[FlaskPlugin()])


class Lien(db.Model):
    __versioned__ = {}
    id: Mapped[IntPK]

    bank_name: Mapped[Optional[str]]
    account_number: Mapped[Optional[str]]

    ro_name: Mapped[Optional[str]]
    ro_code: Mapped[Optional[str]]
    lien_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    lien_date: Mapped[Optional[date]]
    court_order_lien: Mapped[Optional[str]]

    dd_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    dd_date: Mapped[Optional[date]]
    court_order_dd: Mapped[Optional[str]]
    bank_remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    action_taken_by_banker: Mapped[Optional[str]] = mapped_column(db.Text)

    department: Mapped[Optional[str]]
    court_name: Mapped[Optional[str]]
    case_number: Mapped[Optional[str]]
    case_title: Mapped[Optional[str]]
    mact_number: Mapped[Optional[str]]
    petitioner_name: Mapped[Optional[str]]

    date_of_lien_order: Mapped[Optional[date]]
    claim_already_paid_by_hub_office: Mapped[Optional[str]]
    claim_number: Mapped[Optional[str]]
    date_of_claim_registration: Mapped[Optional[date]]
    claim_disbursement_voucher: Mapped[Optional[str]]

    lien_dd_reversal_order: Mapped[Optional[str]]
    lien_status: Mapped[Optional[str]]
    appeal_given: Mapped[Optional[str]]
    appeal_copy: Mapped[Optional[str]]
    appeal_given_2: Mapped[Optional[str]]
    appeal_copy_2: Mapped[Optional[str]]
    stay_obtained: Mapped[Optional[str]]
    stay_order: Mapped[Optional[str]]
    claim_accounting_voucher_number: Mapped[Optional[str]]

    claim_accounting_voucher_date: Mapped[Optional[date]]

    ro_remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    ho_tp_remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    court_order_lien_reversal: Mapped[Optional[str]]
    court_order_dd_reversal: Mapped[Optional[str]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    is_duplicate: Mapped[bool] = mapped_column(default=False)

    @validates("ro_code")
    def validate_ro_code(self, key, value):
        if value not in ALLOWED_RO_CODES:
            raise ValueError(f"Invalid RO code: {value}. Allowed: {ALLOWED_RO_CODES}")
        return value

    def has_access(self, user) -> bool:
        role = user.user_type

        if role in ["admin", "ho_motor_tp"]:
            return True

        if role in ["ro_user", "ro_motor_tp"]:
            return user.ro_code == self.ro_code

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)


db.configure_mappers()
