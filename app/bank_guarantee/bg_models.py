from typing import Optional
from datetime import date

from flask import abort
from sqlalchemy.orm import Mapped, mapped_column
from extensions import db, IntPK


class BankGuarantee(db.Model):
    id: Mapped[IntPK]

    ro_code: Mapped[str]
    oo_code: Mapped[str]

    customer_name: Mapped[str]
    customer_id: Mapped[str]
    debit_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    credit_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    payment_id: Mapped[str]

    date_of_payment: Mapped[date]
    reason: Mapped[str] = mapped_column(db.Text)
    course_of_action: Mapped[Optional[str]] = mapped_column(db.Text)

    def has_access(self, user) -> bool:
        role = user.user_type

        if role in ["admin"]:
            return True

        if role in ["ro_user"]:
            return user.ro_code == self.ro_code
        if role in ["oo_user"]:
            return user.oo_code == self.oo_code

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)
