from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text

from extensions import db, IntPK, CreatedBy, CreatedOn


class Announcements(db.Model):
    id: Mapped[IntPK]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    txt_title: Mapped[str] = mapped_column(Text)
    txt_message: Mapped[str] = mapped_column(Text)
