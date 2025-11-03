from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped
from extensions import db, IntPK, CreatedBy, CreatedOn


class MisTracker(db.Model):
    id: Mapped[IntPK]
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    txt_period: Mapped[str]
    txt_mis_type: Mapped[str]

    bool_mis_shared: Mapped[Optional[bool]]
    date_mis_shared: Mapped[Optional[datetime]]
    mis_shared_by: Mapped[Optional[str]]

    bool_brs_completed: Mapped[Optional[bool]]
    date_brs_completed: Mapped[Optional[datetime]]
    brs_completed_by: Mapped[Optional[str]]

    bool_jv_passed: Mapped[Optional[bool]]
    date_jv_passed: Mapped[Optional[datetime]]
    jv_passed_by: Mapped[Optional[str]]
