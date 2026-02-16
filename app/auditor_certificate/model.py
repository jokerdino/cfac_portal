from datetime import date
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class AuditorCertificate(db.Model):
    id: Mapped[IntPK]

    ro_code: Mapped[str]
    ro_name: Mapped[str]

    purpose: Mapped[str] = mapped_column(db.Text)
    date_of_request: Mapped[date]
    bid_closing_date: Mapped[Optional[date]]
    certificate_issued_date: Mapped[Optional[date]]
    invoice_received_date: Mapped[Optional[date]]
    invoice_date: Mapped[Optional[date]]

    remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    disbursement_date: Mapped[Optional[date]]

    request_id: Mapped[Optional[str]]
    date_of_payment: Mapped[Optional[date]]
    utr_number: Mapped[Optional[str]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
