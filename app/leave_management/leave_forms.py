import datetime  # , date
from flask_wtf import FlaskForm, Form

from wtforms import (
    DateField,
    DecimalField,
    FieldList,
    FormField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    InputRequired,
    NumberRange,
    ValidationError,
)

from .leave_model import EmployeeData


class UpdateLeaveTypeForm(FlaskForm):
    leave_type = SelectField(
        choices=(
            "Casual leave",
            "Casual leave-half day",
            "Restricted holiday",
            "Sick leave-half pay",
            "Sick leave-full pay",
            "Privilege leave",
            "Joining leave",
            "Strike",
            "Loss of pay",
            "Paternity leave",
            "Maternity leave",
            "Special leave",
            # "Exam leave",
        ),
        validators=[DataRequired()],
    )


class AddEmployeeLeaveBalanceForm(FlaskForm):
    calendar_year = SelectField(choices=[2024, 2025], validators=[DataRequired()])
    employee_name = StringField(validators=[DataRequired()])
    employee_number = IntegerField(validators=[DataRequired()])

    opening_casual_leave_balance = DecimalField(
        validators=[InputRequired(), NumberRange(min=0, max=12)]
    )
    opening_sick_leave_balance = DecimalField(
        validators=[InputRequired(), NumberRange(min=0, max=240)]
    )
    opening_rh_balance = DecimalField(
        validators=[InputRequired(), NumberRange(min=0, max=2)]
    )
    opening_privileged_leave_balance = DecimalField(
        validators=[InputRequired(), NumberRange(min=0, max=270)]
    )

    opening_balance_date = DateField(validators=[DataRequired()])


class LeaveAttendanceForm(Form):
    date_of_attendance = DateField(render_kw={"readonly": True, "class": "input"})
    employee_name = StringField(render_kw={"readonly": True, "class": "input"})
    employee_number = StringField(render_kw={"readonly": True, "class": "input"})
    employee_designation = StringField(render_kw={"readonly": True, "class": "input"})
    status_of_attendance = SelectField(
        choices=("Present", "On leave", "On leave-half day", "On duty", "On tour"),
    )
    id = HiddenField()


class LeaveAttendanceRegisterForm(FlaskForm):
    daily_attendance = FieldList(
        FormField(LeaveAttendanceForm, default=EmployeeData), min_entries=1
    )


class EmployeeDataForm(FlaskForm):
    employee_name = StringField(validators=[DataRequired()])
    employee_number = IntegerField(validators=[DataRequired()])
    employee_designation = SelectField(
        choices=[
            "Assistant",
            "Senior Assistant",
            "Admin Officer",
            "Assistant Manager",
            "Deputy Manager",
            "Manager",
            "Chief Manager",
        ],
        validators=[DataRequired()],
    )
    current_status = SelectField(
        choices=["Active", "Inactive"], validators=[DataRequired()]
    )


class LeaveApplicationForm(FlaskForm):
    purpose_of_leave = StringField(validators=[DataRequired()])
    leave_approved_by = StringField(validators=[DataRequired()])
    leave_approver_designation = SelectField(
        choices=[
            "Admin Officer",
            "Assistant Manager",
            "Deputy Manager",
            "Manager",
            "Chief Manager",
        ],
        validators=[DataRequired()],
    )


class LeaveEncashmentForm(FlaskForm):
    leave_encashment_days = IntegerField(
        validators=[DataRequired(), NumberRange(min=1, max=15)]
    )
    leave_encashment_block_year = SelectField(
        choices=["2024-25", "2026-27"], validators=[DataRequired()]
    )
    date_of_leave_encashment = DateField(validators=[DataRequired()])

    def validate_date_of_leave_encashment(form, field):
        if field.data > datetime.date.today():
            raise ValidationError("The date cannot be in the future!")


class LeaveSubmittedDateForm(FlaskForm):
    leaves_submitted_to_est_dept = DateField()


class LeaveBalanceCloseForm(FlaskForm):
    submit = SubmitField()
