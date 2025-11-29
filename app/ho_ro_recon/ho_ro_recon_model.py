from datetime import datetime, date
from typing import Optional

from flask import abort

from sqlalchemy.orm import Mapped, mapped_column
from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class ReconEntries(db.Model):
    id: Mapped[IntPK]
    str_period: Mapped[str]

    str_regional_office_code: Mapped[str]
    str_department: Mapped[Optional[str]]
    str_target_ro_code: Mapped[Optional[str]]
    txt_remarks: Mapped[str] = mapped_column(db.Text)
    str_debit_credit: Mapped[str]
    amount_recon: Mapped[float] = mapped_column(db.Numeric(20, 2))

    str_assigned_to: Mapped[Optional[str]]
    str_head_office_status: Mapped[str] = mapped_column(default="Pending")

    txt_head_office_remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    str_head_office_voucher: Mapped[Optional[str]]
    date_head_office_voucher: Mapped[Optional[date]] = mapped_column(db.Date)

    created_by: Mapped[CreatedBy]
    date_created_date: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    date_updated_date: Mapped[UpdatedOn]

    deleted_by: Mapped[Optional[str]]
    date_deleted_date: Mapped[Optional[datetime]]

    def has_access(self, user):
        if user.user_type == "admin":
            return True
        if user.user_type == "ro_user":
            if user.ro_code in [
                self.str_regional_office_code,
                self.str_target_ro_code,
            ]:
                return True
        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)


class ReconSummary(db.Model):
    id: Mapped[IntPK]
    str_period: Mapped[str]
    str_regional_office_code: Mapped[str]

    input_ro_balance_dr_cr: Mapped[str]
    input_float_ro_balance: Mapped[float] = mapped_column(db.Numeric(20, 2))
    input_ho_balance_dr_cr: Mapped[str]
    input_float_ho_balance: Mapped[float] = mapped_column(db.Numeric(20, 2))

    # meta data
    created_by: Mapped[CreatedBy]
    date_created_date: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    date_updated_date: Mapped[UpdatedOn]

    deleted_by: Mapped[Optional[str]]
    date_deleted_date: Mapped[Optional[datetime]]

    def has_access(self, user):
        if user.user_type == "admin":
            return True
        if user.user_type == "ro_user":
            return user.ro_code == self.str_regional_office_code

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)


class ReconUpdateBalance(db.Model):
    id: Mapped[IntPK]
    str_period: Mapped[str]
    str_regional_office_code: Mapped[str]

    ro_balance: Mapped[float] = mapped_column(db.Numeric(20, 2))
    ro_dr_cr: Mapped[str]
    ho_balance: Mapped[float] = mapped_column(db.Numeric(20, 2))
    ho_dr_cr: Mapped[str]
