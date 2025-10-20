from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Numeric


from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class TimestampMixin:
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class EmployeeData:
    calendar_year: Mapped[int]
    employee_name: Mapped[str]
    employee_number: Mapped[int]
    employee_designation: Mapped[str]
    employee_ro_code: Mapped[str]
    employee_oo_code: Mapped[str]


class PrivilegeLeaveBalance(TimestampMixin, EmployeeData, db.Model):
    id: Mapped[IntPK]
    opening_balance: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    leave_accrued: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    leave_availed: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    leave_encashed: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    leave_lapsed: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    closing_balance: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))


class SickLeaveBalance(TimestampMixin, EmployeeData, db.Model):
    id: Mapped[IntPK]
    opening_balance: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    leave_accrued: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    leave_availed: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    leave_lapsed: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    closing_balance: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
