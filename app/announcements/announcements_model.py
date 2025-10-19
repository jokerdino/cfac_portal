from datetime import datetime

from flask_login import current_user
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


class Announcements(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)

    created_by: Mapped[str] = mapped_column(default=lambda: current_user.username)
    created_on: Mapped[datetime] = mapped_column(default=datetime.now)

    txt_title: Mapped[str] = mapped_column(db.Text)
    txt_message: Mapped[str] = mapped_column(db.Text)
