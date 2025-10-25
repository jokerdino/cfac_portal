from sqlalchemy.orm import Mapped

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class EscalationMatrix(db.Model):
    id: Mapped[IntPK]

    service_type: Mapped[str]
    nature_of_entity: Mapped[str]
    name_of_entity: Mapped[str]
    level: Mapped[str]
    name: Mapped[str]
    roll: Mapped[str]
    email_address: Mapped[str]
    contact_number: Mapped[str]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]
