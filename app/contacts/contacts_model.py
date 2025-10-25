from typing import Optional
from sqlalchemy.orm import Mapped
from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class Contacts(db.Model):
    id: Mapped[IntPK]
    office_code: Mapped[str]
    office_name: Mapped[str]
    name: Mapped[str]
    employee_number: Mapped[int]
    email_address: Mapped[Optional[str]]
    mobile_number: Mapped[Optional[str]]
    zone: Mapped[str]
    designation: Mapped[Optional[str]]
    role: Mapped[str]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
