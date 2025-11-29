from flask import abort
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class Tickets(db.Model):
    id: Mapped[IntPK]
    regional_office_code: Mapped[str]
    office_code: Mapped[str]
    ticket_number: Mapped[str]
    contact_person: Mapped[str]
    contact_mobile_number: Mapped[str]
    contact_email_address: Mapped[str]

    status: Mapped[str]
    department: Mapped[str]

    date_of_creation: Mapped[CreatedOn]
    created_by: Mapped[CreatedBy]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    # ✅ ORM relationship to remarks
    remarks: Mapped[list["TicketRemarks"]] = db.relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketRemarks.time_of_remark.asc()",
        # lazy="selectin",
    )

    def has_access(self, user) -> bool:
        role = user.user_type

        if role == "admin":
            return True

        if role == "ro_user":
            return user.ro_code == self.regional_office_code

        if role == "oo_user":
            return user.oo_code == self.office_code

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)


class TicketRemarks(db.Model):
    id: Mapped[IntPK]
    ticket_id: Mapped[int] = mapped_column(db.ForeignKey("tickets.id"))
    remarks: Mapped[str] = mapped_column(db.Text)

    user: Mapped[CreatedBy]
    time_of_remark: Mapped[CreatedOn]

    # ✅ Back-reference
    ticket: Mapped["Tickets"] = db.relationship(back_populates="remarks")
