from typing import Optional
from datetime import date

from sqlalchemy import Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from extensions import db, IntPK


class BankGuarantee(db.Model):
    id: Mapped[IntPK]

    ro_code: Mapped[str]
    oo_code: Mapped[str]

    customer_name: Mapped[str]
    customer_id: Mapped[str]
    debit_amount: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    credit_amount: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    payment_id: Mapped[str]

    date_of_payment: Mapped[date]
    reason: Mapped[str] = mapped_column(Text)
    course_of_action: Mapped[Optional[str]] = mapped_column(Text)
