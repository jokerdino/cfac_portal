from datetime import datetime
from typing import Optional

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column


from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class HeadOfficeAccountsTracker(db.Model):
    id: Mapped[IntPK]
    str_work: Mapped[str]
    str_period: Mapped[str]
    str_person: Mapped[Optional[str]]

    # user inputs
    bool_current_status: Mapped[Optional[bool]]
    text_remarks: Mapped[Optional[str]] = mapped_column(Text)

    # meta data
    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]


class HeadOfficeBankReconTracker(db.Model):
    id: Mapped[IntPK]

    str_period: Mapped[str]

    str_name_of_bank: Mapped[Optional[str]]
    str_bank_address: Mapped[Optional[str]]

    str_purpose: Mapped[Optional[str]]
    str_person: Mapped[Optional[str]]

    str_gl_code: Mapped[Optional[str]]
    str_sl_code: Mapped[Optional[str]]

    str_bank_account_number: Mapped[Optional[str]]
    str_customer_id: Mapped[Optional[str]]

    # user inputs
    boolean_mis_shared: Mapped[Optional[bool]]
    str_brs_file_upload: Mapped[Optional[str]]
    boolean_jv_passed: Mapped[Optional[bool]]
    str_bank_confirmation_file_upload: Mapped[Optional[str]]
    text_remarks: Mapped[Optional[str]] = mapped_column(Text)

    # meta data
    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]
