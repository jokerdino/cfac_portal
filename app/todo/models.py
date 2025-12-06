from typing import Optional
from datetime import date
from sqlalchemy.orm import Mapped, mapped_column

from extensions import (
    db,
    IntPK,
    CreatedBy,
    CreatedOn,
    UpdatedBy,
    UpdatedOn,
    CreatedById,
    UpdatedById,
)


class Task(db.Model):
    id: Mapped[IntPK]
    title: Mapped[str]
    description: Mapped[str] = mapped_column(db.Text, default="")
    status: Mapped[str] = mapped_column(default="pending")
    priority: Mapped[int] = mapped_column(default=0)
    due_date: Mapped[date | None]
    assigned_to_id: Mapped[int | None]

    subscribers: Mapped[Optional[list[int]]] = mapped_column(db.ARRAY(db.Integer))

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    created_by_id: Mapped[CreatedById]
    updated_by_id: Mapped[UpdatedById]

    @property
    def get_status_display(self):
        return {
            "pending": "Pending",
            "in-progress": "In Progress",
            "done": "Completed",
        }[self.status]

    @property
    def get_priority_display(self):
        return {
            1: "Low",
            2: "Medium",
            3: "High",
        }[self.priority]

    @property
    def priority_badge_class(self):
        return {
            3: "text-bg-warning",  # High
            2: "text-bg-info",  # Medium
            1: "",  # Low
        }.get(self.priority, "")


class Notification(db.Model):
    id: Mapped[IntPK]
    user_id: Mapped[int] = mapped_column(nullable=False)  # assigned_to_id
    message: Mapped[str] = mapped_column(db.String(255), nullable=False)
    created_on: Mapped[CreatedOn]
    is_read: Mapped[bool] = mapped_column(default=False)
