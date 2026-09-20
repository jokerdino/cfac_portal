from datetime import date

from flask import abort
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from extensions import CreatedBy, CreatedOn, IntPK, UpdatedBy, UpdatedOn, db

HEAD_OFFICE_CODE = "000100"
HO_REPLACEMENT = "9"
DEFAULT_REPLACEMENT = "3"


def display_transaction_id(
    transaction_id: str | None, office_code: str | None
) -> str | None:
    if not transaction_id or not transaction_id.startswith("0"):
        return transaction_id
    replacement = (
        HO_REPLACEMENT if office_code == HEAD_OFFICE_CODE else DEFAULT_REPLACEMENT
    )
    return replacement + transaction_id[1:]


class FundIntimation(db.Model):
    id: Mapped[IntPK]

    regional_office_code: Mapped[str]
    operating_office_code: Mapped[str]

    type_of_disbursement: Mapped[str]
    nature_of_recipient: Mapped[str]
    name_of_recipient: Mapped[str]

    purpose_of_disbursement: Mapped[str]
    claim_number: Mapped[str | None]
    coinsurance_involved: Mapped[bool | None]
    coinsurance_details: Mapped[str | None] = mapped_column(db.Text)

    date_of_intimation: Mapped[date] = mapped_column(default=date.today)

    transaction_id: Mapped[str | None]
    transaction_date: Mapped[date | None]
    transaction_amount: Mapped[float | None] = mapped_column(db.Numeric(15, 2))

    expected_date_of_disbursement: Mapped[date | None]

    regional_office_remarks: Mapped[str | None] = mapped_column(db.Text)
    head_office_remarks: Mapped[str | None] = mapped_column(db.Text)

    utr_number: Mapped[str | None]
    utr_date: Mapped[date | None]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    @hybrid_property
    def display_transaction_id(self) -> str | None:
        return display_transaction_id(self.transaction_id, self.operating_office_code)

    @display_transaction_id.inplace.expression
    @classmethod
    def _display_transaction_id_expr(cls):
        replacement = db.case(
            (cls.operating_office_code == HEAD_OFFICE_CODE, HO_REPLACEMENT),
            else_=DEFAULT_REPLACEMENT,
        )
        return db.case(
            (
                cls.transaction_id.like("0%"),
                replacement.concat(db.func.substr(cls.transaction_id, 2)),
            ),
            else_=cls.transaction_id,
        )

    def has_access(self, user):
        if user.user_type == "admin":
            return True
        if user.user_type == "ro_user":
            return self.regional_office_code == user.ro_code
        if user.user_type in ["oo_user", "coinsurance_hub_user"]:
            return self.operating_office_code == user.oo_code
        return False

    def require_access(self, user):
        if not self.has_access(user):
            abort(404)

    def check_status(self):
        return bool(self.utr_number)
