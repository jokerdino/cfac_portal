from datetime import date, time


from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class Circular(db.Model):
    id: Mapped[IntPK]

    year: Mapped[Optional[int]]
    month: Mapped[Optional[int]]
    number: Mapped[Optional[int]]
    reference_number: Mapped[Optional[str]]

    date_of_issue: Mapped[Optional[date]]
    circular_title: Mapped[Optional[str]]
    issued_by_name: Mapped[Optional[str]]
    issued_by_designation: Mapped[Optional[str]]
    mode_of_dispatch: Mapped[Optional[str]]
    recipients: Mapped[Optional[str]]
    number_of_copies: Mapped[Optional[int]]
    date_of_acknowledgement: Mapped[Optional[date]]
    remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    upload_document: Mapped[Optional[str]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class OutwardDocument(db.Model):
    id: Mapped[IntPK]

    year: Mapped[Optional[int]]
    month: Mapped[Optional[int]]
    number: Mapped[Optional[int]]
    reference_number: Mapped[Optional[str]]

    date_of_dispatch: Mapped[Optional[date]]
    time_of_dispatch: Mapped[Optional[time]]
    recipient_name: Mapped[Optional[str]]
    recipient_address: Mapped[Optional[str]] = mapped_column(db.Text)
    mode_of_dispatch: Mapped[Optional[str]]

    description_of_item: Mapped[Optional[str]] = mapped_column(db.Text)
    sender_name: Mapped[Optional[str]]
    dispatched_by: Mapped[Optional[str]]
    remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    upload_document: Mapped[Optional[str]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class InwardDocument(db.Model):
    id: Mapped[IntPK]

    year: Mapped[Optional[int]]
    month: Mapped[Optional[int]]
    number: Mapped[Optional[int]]
    reference_number: Mapped[Optional[str]]

    date_of_receipt: Mapped[Optional[date]]
    time_of_receipt: Mapped[Optional[time]]
    sender_name: Mapped[Optional[str]]
    sender_address: Mapped[Optional[str]] = mapped_column(db.Text)
    mode_of_receipt: Mapped[Optional[str]]
    letter_reference_number: Mapped[Optional[str]]

    description_of_item: Mapped[Optional[str]] = mapped_column(db.Text)

    recipient_name: Mapped[Optional[str]]
    received_by: Mapped[Optional[str]]

    remarks: Mapped[Optional[str]] = mapped_column(db.Text)
    upload_document: Mapped[Optional[str]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
