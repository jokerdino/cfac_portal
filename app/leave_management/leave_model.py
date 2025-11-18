from datetime import timedelta, date
from typing import Optional


from sqlalchemy import func
from sqlalchemy.orm import column_property, Mapped, mapped_column

from extensions import db, IntPK, CreatedOn, UpdatedOn, CreatedBy, UpdatedBy


class EmployeeData(db.Model):
    id: Mapped[IntPK]

    employee_name: Mapped[str]
    employee_number: Mapped[int] = mapped_column(unique=True)
    employee_designation: Mapped[str]
    date_of_joining_current_cadre: Mapped[date]

    current_status: Mapped[str] = mapped_column(default="Active")
    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class AttendanceRegister(db.Model):
    id: Mapped[IntPK]

    date_of_attendance: Mapped[date] = mapped_column(db.Date)
    employee_name: Mapped[str]
    employee_number: Mapped[int]
    employee_designation: Mapped[str]
    date_of_joining_current_cadre: Mapped[date]
    status_of_attendance: Mapped[Optional[str]]

    type_of_leave: Mapped[Optional[str]]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    month: Mapped[str] = column_property(func.to_char(date_of_attendance, "YYYY-MM"))
    month_string: Mapped[str] = column_property(
        func.to_char(date_of_attendance, "Mon-YY")
    )


class LeaveApplication(db.Model):
    id: Mapped[IntPK]

    type_of_leave: Mapped[str]
    start_date: Mapped[date]
    end_date: Mapped[date]
    number_of_days_leave: Mapped[float] = mapped_column(db.Numeric(6, 2))
    number_of_days_off_duty: Mapped[float] = mapped_column(db.Numeric(6, 2))

    employee_name: Mapped[str]
    employee_number: Mapped[int]
    employee_designation: Mapped[str]
    date_of_joining_current_cadre: Mapped[Optional[date]]

    available_leave_credit: Mapped[float] = mapped_column(db.Numeric(6, 2))

    purpose_of_leave: Mapped[Optional[str]] = mapped_column(db.Text)
    leave_approved_by: Mapped[Optional[str]]
    leave_approver_designation: Mapped[Optional[str]]

    # linking to primary key of attendance_register table
    list_attendance_register_days: Mapped[list[int]] = mapped_column(
        db.ARRAY(db.Integer)
    )

    current_status: Mapped[str] = mapped_column(default="Pending")

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    @property
    def list_of_days(self):
        return [date for date in self.get_list_of_days(self.end_date, self.start_date)]

    @staticmethod
    def get_list_of_days(start_date, end_date):
        for n in range(int((end_date - start_date).days) + 1):
            yield start_date + timedelta(n)


# credit SO answer: https://stackoverflow.com/a/42973595/1037268
# lambda function to set default value depending on another column


def same_as(col):
    return lambda ctx: ctx.current_parameters.get(col)


class LeaveBalance(db.Model):
    id: Mapped[IntPK]

    calendar_year: Mapped[int]
    employee_name: Mapped[str]
    employee_number: Mapped[int]

    opening_casual_leave_balance: Mapped[float] = mapped_column(db.Numeric(6, 2))
    opening_sick_leave_balance: Mapped[float] = mapped_column(db.Numeric(6, 2))
    opening_rh_balance: Mapped[float] = mapped_column(db.Numeric(6, 2))
    opening_privileged_leave_balance: Mapped[float] = mapped_column(db.Numeric(6, 2))

    current_casual_leave_balance: Mapped[float] = mapped_column(
        db.Numeric(6, 2), default=same_as("opening_casual_leave_balance")
    )
    current_sick_leave_balance: Mapped[float] = mapped_column(
        db.Numeric(6, 2), default=same_as("opening_sick_leave_balance")
    )
    current_rh_balance: Mapped[float] = mapped_column(
        db.Numeric(6, 2), default=same_as("opening_rh_balance")
    )
    current_privileged_leave_balance: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2), default=same_as("opening_privileged_leave_balance")
    )

    closing_casual_leave_balance: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2)
    )
    closing_sick_leave_balance: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2)
    )
    closing_rh_balance: Mapped[Optional[float]] = mapped_column(db.Numeric(6, 2))
    closing_privileged_leave_balance: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2)
    )

    casual_leaves_taken: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2), default=0.0
    )
    casual_leaves_half_day_taken: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2), default=0.0
    )
    sick_leaves_taken: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2), default=0.0
    )
    privilege_leaves_taken: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2), default=0.0
    )
    restricted_holidays_taken: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2), default=0.0
    )
    joining_leave_taken: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2), default=0.0
    )
    lop_taken: Mapped[Optional[float]] = mapped_column(db.Numeric(6, 2), default=0.0)
    strike_taken: Mapped[Optional[float]] = mapped_column(db.Numeric(6, 2), default=0.0)
    special_leave_taken: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2), default=0.0
    )
    maternity_leave_taken: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2), default=0.0
    )
    paternity_leave_taken: Mapped[Optional[float]] = mapped_column(
        db.Numeric(6, 2), default=0.0
    )

    leave_encashment_days: Mapped[Optional[float]] = mapped_column(db.Numeric(6, 2))
    leave_encashment_block_year: Mapped[Optional[str]]
    date_of_leave_encashment: Mapped[Optional[date]]

    opening_balance_date: Mapped[date]
    closing_balance_date: Mapped[Optional[date]]

    current_status: Mapped[str] = mapped_column(default="Open")

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class LeaveSubmissionData(db.Model):
    id: Mapped[IntPK]
    leaves_submitted_to_est_dept: Mapped[date]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]


class PublicHoliday(db.Model):
    id: Mapped[IntPK]
    date_of_holiday: Mapped[date] = mapped_column(db.Date)
    name_of_holiday: Mapped[str]
    type_of_holiday: Mapped[str]
    type_of_list: Mapped[str]

    created_by: Mapped[CreatedBy]
    created_on: Mapped[CreatedOn]

    updated_by: Mapped[UpdatedBy]
    updated_on: Mapped[UpdatedOn]

    year: Mapped[str] = column_property(func.to_char(date_of_holiday, "YYYY"))
    #    holiday_value: str = field(init=False)

    @property
    def holiday_value(self) -> int | None:
        holiday_dict = {"PUBLIC HOLIDAY": 1, "TAMIL NADU": 2, "ALL INDIA": 3}
        return holiday_dict.get(self.type_of_list, 0)
