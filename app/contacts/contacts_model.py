from typing import Optional

from flask import abort
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

    def has_access(self, user) -> bool:
        role = user.user_type

        if role in ["admin"]:
            return True

        if role in ["ro_user"]:
            return user.ro_code == self.office_code

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)
