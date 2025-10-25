from datetime import datetime
from typing import Optional, Literal

from sqlalchemy.orm import Mapped, mapped_column
from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn

AllocationStatus = Literal["Original", "Revised"]
UtilizationQuarter = Literal["I", "II", "III", "IV"]


class BudgetAllocation(db.Model):
    id: Mapped[IntPK]

    str_financial_year: Mapped[str]
    str_type: Mapped[AllocationStatus]  # original, revised
    str_ro_code: Mapped[str]

    str_expense_head: Mapped[str]
    int_budget_allocated: Mapped[float] = mapped_column(db.Numeric(15, 2))

    # meta data
    current_status: Mapped[Optional[str]]

    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]


class BudgetUtilization(db.Model):
    id: Mapped[IntPK]

    str_financial_year: Mapped[str]
    str_quarter: Mapped[UtilizationQuarter]  # first, second, third, fourth
    str_ro_code: Mapped[str]

    str_expense_head: Mapped[str]
    int_budget_utilized: Mapped[float] = mapped_column(db.Numeric(15, 2))

    # meta data
    current_status: Mapped[Optional[str]]

    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
    deleted_by: Mapped[Optional[str]]
