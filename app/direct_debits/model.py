from datetime import date
from typing import Optional

from flask import abort
from sqlalchemy.orm import mapped_column, Mapped

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class DirectDebit(db.Model):
    id: Mapped[IntPK]

    # Will be uploaded by HO in bulk
    ro_name: Mapped[str]
    ro_code: Mapped[str]
    transaction_date: Mapped[date]
    particulars: Mapped[str]
    debit: Mapped[float] = mapped_column(db.Numeric(15, 2))

    # HO IOT JV

    ho_iot_jv_number: Mapped[Optional[str]]
    ho_iot_jv_date: Mapped[Optional[date]]
    bool_jv_passed: Mapped[bool] = mapped_column(default=False)
    jv_passed_as_on: Mapped[Optional[date]]

    # to be entered by RO accounts or RO TP department
    ro_jv_number: Mapped[Optional[str]]
    ro_jv_date: Mapped[Optional[str]]

    remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    def has_access(self, user) -> bool:
        role = user.user_type

        if role in ["admin"]:
            return True

        if role in ["ro_user", "ro_motor_tp"]:
            return user.ro_code == self.ro_code

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)
