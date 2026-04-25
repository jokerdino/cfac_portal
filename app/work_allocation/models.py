from sqlalchemy.orm import Mapped

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class WorkAllocation(db.Model):
    id: Mapped[IntPK]

    bank_name: Mapped[str]
    mode: Mapped[str]
    officer_name: Mapped[str]

    created_on: Mapped[CreatedOn]
    created_by: Mapped[CreatedBy]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
