from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class FundInflowSummary(db.Model):
    id: Mapped[IntPK]

    type_of_collection: Mapped[str]
    bank_vendor_name: Mapped[str]
    mode_of_collection: Mapped[str]
    month: Mapped[str]

    number_of_transactions: Mapped[Optional[int]]
    amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class FundOutflowSummary(db.Model):
    id: Mapped[IntPK]

    bank_name: Mapped[str]
    mode_of_payment: Mapped[str]
    month: Mapped[str]

    number_of_transactions: Mapped[Optional[int]]
    amount: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class FundFlowBankCharges(db.Model):
    id: Mapped[IntPK]

    bank_name: Mapped[str]
    month: Mapped[str]

    fixed_charges: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))
    variable_charges: Mapped[Optional[float]] = mapped_column(db.Numeric(15, 2))

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]
    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    @hybrid_property
    def total_charges(self) -> float:
        return (self.fixed_charges or 0) + (self.variable_charges or 0)
