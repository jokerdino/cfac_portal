from datetime import date
from typing import Optional

from flask import abort
from sqlalchemy.orm import mapped_column, Mapped


from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class RegionalOfficeAuditReport(db.Model):
    id: Mapped[IntPK]

    regional_office_code: Mapped[str]
    regional_office_name: Mapped[str]
    period: Mapped[str]

    audit_report: Mapped[Optional[str]]
    annexures: Mapped[Optional[str]]
    notes_forming_part_of_accounts: Mapped[Optional[str]]

    mode_of_dispatch: Mapped[Optional[str]]
    date_of_dispatch: Mapped[Optional[date]]
    tracking_number: Mapped[Optional[str]]

    remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    # meta
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    def has_access(self, user) -> bool:
        user_type = user.user_type

        if user_type == "admin":
            return True
        if user_type == "ro_user":
            if self.regional_office_code == user.ro_code:
                return True

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)


class RegionalOfficeAuditObservation(db.Model):
    id: Mapped[IntPK]

    regional_office_code: Mapped[str]
    period: Mapped[str]

    department: Mapped[str]
    audit_observation: Mapped[str] = mapped_column(db.Text)
    regional_office_remarks: Mapped[str] = mapped_column(db.Text)
    head_office_remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    # meta
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    def has_access(self, user) -> bool:
        user_type = user.user_type

        if user_type == "admin":
            return True
        if user_type == "ro_user":
            if self.regional_office_code == user.ro_code:
                return True

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)


class AuditorRegionalOfficeMapping(db.Model):
    id: Mapped[IntPK]

    regional_office_code: Mapped[str]
    regional_office_name: Mapped[str]

    period: Mapped[str]
    user_id: Mapped[Optional[int]]

    # meta
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
