from dataclasses import dataclass, field
from datetime import datetime, timedelta

from flask_login import current_user

from sqlalchemy import func
from sqlalchemy.orm import column_property

from extensions import db


@dataclass
class EmployeeData(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    employee_name: str = db.Column(db.String)
    employee_number: int = db.Column(db.Integer, unique=True)
    employee_designation: str = db.Column(db.String)

    current_status = db.Column(db.String, default="Active")
    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


@dataclass
class AttendanceRegister(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)

    date_of_attendance: datetime.date = db.Column(db.Date)
    employee_name: str = db.Column(db.String)
    employee_number: int = db.Column(db.Integer)
    employee_designation: str = db.Column(db.String)
    status_of_attendance: str = db.Column(db.String)

    type_of_leave = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


class LeaveApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    type_of_leave = db.Column(db.String)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    number_of_days_leave = db.Column(db.Numeric(6, 2))
    number_of_days_off_duty = db.Column(db.Numeric(6, 2))

    employee_name = db.Column(db.String)
    employee_number = db.Column(db.Integer)
    employee_designation = db.Column(db.String)

    available_leave_credit = db.Column(db.Numeric(6, 2))

    purpose_of_leave = db.Column(db.Text)
    leave_approved_by = db.Column(db.String)
    leave_approver_designation = db.Column(db.String)

    # linking to primary key of attendance_register table
    list_attendance_register_days = db.Column(db.ARRAY(db.Integer))

    current_status = db.Column(db.String, default="Pending")

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)

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
    id = db.Column(db.Integer, primary_key=True)

    calendar_year = db.Column(db.Integer)
    employee_name = db.Column(db.String)
    employee_number = db.Column(db.Integer)

    opening_casual_leave_balance = db.Column(db.Numeric(6, 2))
    opening_sick_leave_balance = db.Column(db.Numeric(6, 2))
    opening_rh_balance = db.Column(db.Numeric(6, 2))
    opening_privileged_leave_balance = db.Column(db.Numeric(6, 2))

    current_casual_leave_balance = db.Column(
        db.Numeric(6, 2), default=same_as("opening_casual_leave_balance")
    )
    current_sick_leave_balance = db.Column(
        db.Numeric(6, 2), default=same_as("opening_sick_leave_balance")
    )
    current_rh_balance = db.Column(
        db.Numeric(6, 2), default=same_as("opening_rh_balance")
    )
    current_privileged_leave_balance = db.Column(
        db.Numeric(6, 2), default=same_as("opening_privileged_leave_balance")
    )

    closing_casual_leave_balance = db.Column(db.Numeric(6, 2))
    closing_sick_leave_balance = db.Column(db.Numeric(6, 2))
    closing_rh_balance = db.Column(db.Numeric(6, 2))
    closing_privileged_leave_balance = db.Column(db.Numeric(6, 2))

    casual_leaves_taken = db.Column(db.Numeric(6, 2), default=0.0)
    casual_leaves_half_day_taken = db.Column(db.Numeric(6, 2), default=0.0)
    sick_leaves_taken = db.Column(db.Numeric(6, 2), default=0.0)
    privilege_leaves_taken = db.Column(db.Numeric(6, 2), default=0.0)
    restricted_holidays_taken = db.Column(db.Numeric(6, 2), default=0.0)
    joining_leave_taken = db.Column(db.Numeric(6, 2), default=0.0)
    lop_taken = db.Column(db.Numeric(6, 2), default=0.0)
    strike_taken = db.Column(db.Numeric(6, 2), default=0.0)
    special_leave_taken = db.Column(db.Numeric(6, 2), default=0.0)
    maternity_leave_taken = db.Column(db.Numeric(6, 2), default=0.0)
    paternity_leave_taken = db.Column(db.Numeric(6, 2), default=0.0)

    leave_encashment_days = db.Column(db.Numeric(6, 2))
    leave_encashment_block_year = db.Column(db.String)
    date_of_leave_encashment = db.Column(db.Date)

    opening_balance_date = db.Column(db.Date)
    closing_balance_date = db.Column(db.Date)

    current_status = db.Column(db.String, default="Open")

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


class LeaveSubmissionData(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    leaves_submitted_to_est_dept = db.Column(db.Date)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


@dataclass
class PublicHoliday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_of_holiday: datetime.date = db.Column(db.Date)
    name_of_holiday: str = db.Column(db.String)
    type_of_holiday: str = db.Column(db.String)
    type_of_list: str = db.Column(db.String)

    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)

    year = column_property(func.to_char(date_of_holiday, "YYYY"))
    holiday_value: str = field(init=False)

    @property
    def holiday_value(self) -> int | None:
        holiday_dict = {"PUBLIC HOLIDAY": 1, "TAMIL NADU": 2, "ALL INDIA": 3}
        return holiday_dict.get(self.type_of_list, 0)
