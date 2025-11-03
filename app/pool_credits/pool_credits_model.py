from datetime import datetime, date

from typing import Optional
import uuid


from sqlalchemy import Uuid
from sqlalchemy.orm import column_property, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class PoolCredits(db.Model):
    id: Mapped[IntPK]
    date_uploaded_date: Mapped[date]

    # below columns are uploaded from bank statement excel
    book_date: Mapped[date]
    description: Mapped[str] = mapped_column(db.Text)
    ledger_balance: Mapped[Optional[float]] = mapped_column(db.Numeric(20, 2))
    credit: Mapped[Optional[float]] = mapped_column(db.Numeric(20, 2))
    debit: Mapped[Optional[float]] = mapped_column(db.Numeric(20, 2))
    value_date: Mapped[date] = mapped_column(db.Date)
    reference_no: Mapped[Optional[str]]
    transaction_branch: Mapped[str] = mapped_column(db.Text)

    # flag description is assigned from our table
    flag_description: Mapped[str] = mapped_column(db.Text)

    # user inputs

    # regional office users will self assign the credits to their RO
    str_regional_office_code: Mapped[Optional[str]]
    text_remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    bool_jv_passed: Mapped[Optional[bool]] = mapped_column(default=False)

    # meta data
    batch_id: Mapped[Optional[Uuid]] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, index=True
    )
    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]
    date_jv_passed_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]
    jv_passed_by: Mapped[Optional[str]]

    month: Mapped[str] = column_property(db.func.to_char(value_date, "YYYY-MM"))
    month_string: Mapped[str] = column_property(db.func.to_char(value_date, "Mon-YY"))


class PoolCreditsPortal(db.Model):
    id: Mapped[IntPK]

    txt_reference_number: Mapped[str]
    date_value_date: Mapped[date] = mapped_column(db.Date)
    amount_credit: Mapped[float] = mapped_column(db.Numeric(20, 2))
    txt_name_of_remitter: Mapped[str] = mapped_column(db.String)

    batch_id: Mapped[Optional[Uuid]] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, index=True
    )
    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]


class PoolCreditsJournalVoucher(db.Model):
    id: Mapped[IntPK]
    str_regional_office_code: Mapped[str] = mapped_column(unique=True)
    gl_code: Mapped[str]
    sl_code: Mapped[str]

    created_on: Mapped[CreatedOn]
    updated_on: Mapped[UpdatedOn]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
