from datetime import date
from typing import Optional


from sqlalchemy.orm import Mapped, mapped_column
from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class ChangeInstruction(db.Model):
    id: Mapped[IntPK]

    title: Mapped[str]
    description: Mapped[Optional[str]] = mapped_column(db.Text)
    ticket_date: Mapped[date]
    ticket_number: Mapped[str]

    ci_document: Mapped[Optional[str]]
    ci_number: Mapped[Optional[str]]

    current_status: Mapped[str] = mapped_column(default="CI raised")
    approach_note_date: Mapped[Optional[date]]
    approach_note_document: Mapped[Optional[str]]

    approach_note_approval_date: Mapped[Optional[date]]

    uat_testing_date: Mapped[Optional[date]]
    uat_remarks: Mapped[Optional[str]] = mapped_column(db.Text)

    pilot_deployment_date: Mapped[Optional[date]]
    production_deployment_date: Mapped[Optional[date]]

    # metadata
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
