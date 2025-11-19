from datetime import date
from typing import Optional, Literal

from flask import abort
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class DqrRefund(db.Model):
    id: Mapped[IntPK]

    organisation: Mapped[str] = mapped_column(default="United India Insurance Co.")
    ro_code: Mapped[str]
    office_code: Mapped[str]
    device_serial_number: Mapped[str]
    refund_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))
    txn_date: Mapped[date]
    txn_currency: Mapped[str]
    refund_currency: Mapped[str]
    auth_code: Mapped[Optional[str]]
    mid: Mapped[str]
    tid: Mapped[str]
    txn_amt: Mapped[float] = mapped_column(db.Numeric(15, 2))
    rrn: Mapped[str]
    account_number: Mapped[str] = mapped_column(default="719011004568")
    reason_for_refund: Mapped[str] = mapped_column(db.Text)
    refund_ref_no: Mapped[Optional[str]]
    refund_date: Mapped[Optional[date]]
    ro_remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    refund_status: Mapped[str] = mapped_column(default="Refund pending")

    # metadata
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    def has_access(self, user) -> bool:
        role = user.user_type

        if role in ["admin"]:
            return True

        elif role in ["ro_user"]:
            return user.ro_code == self.ro_code
        elif role in ["oo_user"]:
            return user.oo_code == self.office_code
        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)


class DqrMachines(db.Model):
    id: Mapped[IntPK]
    ro_code: Mapped[str]
    merchant_name: Mapped[str]
    merchant_dba_name: Mapped[str]
    mid: Mapped[str]
    tid: Mapped[str]
    mcc_code: Mapped[str]
    office_code: Mapped[str]
    address: Mapped[str] = mapped_column(db.Text)
    city: Mapped[str]
    pincode: Mapped[int]
    state: Mapped[str]
    name: Mapped[str]
    login: Mapped[str]
    user_id: Mapped[str]
    password: Mapped[str]
    device_name: Mapped[str]
    status: Mapped[Optional[Literal["Installed", "Pending"]]]
    device_serial_number: Mapped[str]
    installation_date: Mapped[Optional[date]]

    # metadata
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
