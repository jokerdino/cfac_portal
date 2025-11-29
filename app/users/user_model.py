from datetime import datetime
from typing import Optional, Literal

from flask import abort
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


UserTypes = Literal[
    "admin",
    "oo_user",
    "ro_user",
    "coinsurance_hub_user",
    "ho_motor_tp",
    "ro_motor_tp",
    "ri_tech",
    "ri_accounts",
    "ho_technical",
]


class User(UserMixin, db.Model):
    id: Mapped[IntPK]
    ro_code: Mapped[str]
    oo_code: Mapped[str]
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    user_type: Mapped[UserTypes]
    reset_password: Mapped[bool]
    time_last_login: Mapped[Optional[datetime]]

    role: Mapped[Optional[list[str]]] = mapped_column(db.ARRAY(db.String))

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    @property
    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def has_access(self, user) -> bool:
        role = user.user_type

        if role in ["admin"]:
            return True

        if role in ["ro_user"]:
            if self.user_type in ["oo_user"]:
                return user.ro_code == self.ro_code

        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)


class LogUser(db.Model):
    id: Mapped[IntPK]
    user_id: Mapped[str]

    type_of_action: Mapped[str]
    time_of_action: Mapped[datetime]
