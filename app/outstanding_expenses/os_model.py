from datetime import date
from typing import Optional

from flask import abort
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db, IntPK, CreatedOn


class OutstandingExpenses(db.Model):
    id: Mapped[IntPK]

    str_regional_office_code: Mapped[str]
    str_operating_office_code: Mapped[str]

    str_party_type: Mapped[str]
    str_party_id: Mapped[str]
    str_party_name: Mapped[str]
    float_gross_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))

    bool_tds_involved: Mapped[Optional[bool]]
    float_tds_amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    float_net_amount: Mapped[float] = mapped_column(db.Numeric(15, 2))

    str_section: Mapped[Optional[str]]
    str_pan_number: Mapped[Optional[str]]

    str_nature_of_payment: Mapped[str]
    str_narration: Mapped[str] = mapped_column(db.Text)

    date_payment_date: Mapped[Optional[date]]
    current_status: Mapped[Optional[str]]

    date_date_of_creation: Mapped[CreatedOn]

    def has_access(self, user) -> bool:
        # Disallow deleted items
        if self.current_status == "Deleted":
            return False

        role = user.user_type

        if role == "admin":
            return True

        if role == "ro_user":
            return user.ro_code == self.str_regional_office_code

        if role == "oo_user":
            return user.oo_code == self.str_operating_office_code

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)
