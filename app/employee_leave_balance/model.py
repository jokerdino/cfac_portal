from datetime import datetime

from flask_login import current_user

from extensions import db


class TimestampMixin:
    created_by = db.Column(db.String, default=lambda: current_user.username)
    created_on = db.Column(db.DateTime, default=datetime.now)

    updated_by = db.Column(db.String, onupdate=lambda: current_user.username)
    updated_on = db.Column(db.DateTime, onupdate=datetime.now)


class EmployeeData:
    calendar_year = db.Column(db.Integer)
    employee_name = db.Column(db.String)
    employee_number = db.Column(db.Integer)
    employee_designation = db.Column(db.String)
    employee_ro_code = db.Column(db.String)
    employee_oo_code = db.Column(db.String)


class PrivilegeLeaveBalance(TimestampMixin, EmployeeData, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    opening_balance = db.Column(db.Numeric(10, 2))
    leave_accrued = db.Column(db.Numeric(10, 2))
    leave_availed = db.Column(db.Numeric(10, 2))
    leave_encashed = db.Column(db.Numeric(10, 2))
    leave_lapsed = db.Column(db.Numeric(10, 2))
    closing_balance = db.Column(db.Numeric(10, 2))


class SickLeaveBalance(TimestampMixin, EmployeeData, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    opening_balance = db.Column(db.Numeric(10, 2))
    leave_accrued = db.Column(db.Numeric(10, 2))
    leave_availed = db.Column(db.Numeric(10, 2))
    leave_lapsed = db.Column(db.Numeric(10, 2))
    closing_balance = db.Column(db.Numeric(10, 2))
