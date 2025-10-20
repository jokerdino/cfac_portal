from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column
from flask_login import current_user

from extensions import db


class EscalationMatrix(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)

    service_type: Mapped[str]
    nature_of_entity: Mapped[str]
    name_of_entity: Mapped[str]
    level: Mapped[str]
    name: Mapped[str]
    roll: Mapped[str]
    email_address: Mapped[str]
    contact_number: Mapped[str]

    created_by: Mapped[str] = mapped_column(default=lambda: current_user.username)
    created_on: Mapped[datetime] = mapped_column(default=datetime.now)

    updated_by: Mapped[Optional[str]] = mapped_column(
        onupdate=lambda: current_user.username
    )
    updated_on: Mapped[Optional[datetime]] = mapped_column(onupdate=datetime.now)
