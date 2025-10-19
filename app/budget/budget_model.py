from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from extensions import db


class BudgetAllocation(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)

    str_financial_year: Mapped[str]
    str_type: Mapped[str]  # original, revised
    str_ro_code: Mapped[str]

    str_expense_head: Mapped[str]
    int_budget_allocated: Mapped[float] = mapped_column(db.Numeric(15, 2))

    # meta data
    current_status: Mapped[Optional[str]]

    date_created_date: Mapped[datetime]
    date_updated_date: Mapped[Optional[datetime]]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[str]
    updated_by: Mapped[Optional[str]]
    deleted_by: Mapped[Optional[str]]


class BudgetUtilization(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)

    str_financial_year: Mapped[str]
    str_quarter: Mapped[str]  # first, second, third, fourth
    str_ro_code: Mapped[str]

    str_expense_head: Mapped[str]
    int_budget_utilized: Mapped[float] = mapped_column(db.Numeric(15, 2))

    # meta data
    current_status: Mapped[Optional[str]]

    date_created_date: Mapped[datetime]
    date_updated_date: Mapped[Optional[datetime]]
    date_deleted_date: Mapped[Optional[datetime]]

    created_by: Mapped[str]
    updated_by: Mapped[Optional[str]]
    deleted_by: Mapped[Optional[str]]
