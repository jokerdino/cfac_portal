from dataclasses import asdict
from datetime import datetime, date, timedelta
from math import floor
import decimal

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import case, func, and_
from sqlalchemy.exc import IntegrityError

from extensions import db

from . import leave_mgmt_bp
from .leave_forms import (
    AddEmployeeLeaveBalanceForm,
    EmployeeDataForm,
    LeaveApplicationForm,
    LeaveAttendanceRegisterForm,
    UpdateLeaveTypeForm,
    LeaveSubmittedDateForm,
    LeaveEncashmentForm,
    LeaveBalanceCloseForm,
)
from .leave_model import (
    AttendanceRegister,
    EmployeeData,
    LeaveApplication,
    LeaveBalance,
    LeaveSubmissionData,
)


def num_of_days(start_date, end_date):
    return (end_date - start_date).days


@leave_mgmt_bp.route("/home/")
@login_required
def leave_home():
    if current_user.username == "bar44515":
        return redirect(
            url_for(".edit_attendance", date_string=date.today().strftime("%d%m%Y"))
        )
    else:
        return redirect(url_for(".leaves_taken_list", status="pending"))


@leave_mgmt_bp.route("/attendance/")
@login_required
def leave_attendance_list():
    attendance_status_list = [
        "Present",
        "On leave",
        "On leave-half day",
        "On duty",
        "On tour",
    ]
    case_status = {
        k: case(
            (
                AttendanceRegister.status_of_attendance == v,
                AttendanceRegister.status_of_attendance,
            )
        )
        for k, v in zip(attendance_status_list, attendance_status_list)
    }
    entities_list = [func.count(case_status[i]) for i in attendance_status_list]
    list = db.session.execute(
        db.select(
            AttendanceRegister.date_of_attendance,
            *entities_list,
            func.count(AttendanceRegister.status_of_attendance),
        )
        .group_by(AttendanceRegister.date_of_attendance)
        .order_by(AttendanceRegister.date_of_attendance.desc())
    )

    return render_template("leave_attendance_list.html", list=list)


@leave_mgmt_bp.route("/attendance/<string:date_string>/", methods=["GET", "POST"])
@login_required
def edit_attendance(date_string):
    param_date = datetime.strptime(date_string, "%d%m%Y")
    populate_attendance_register(param_date)

    attendance = db.session.scalars(
        db.select(AttendanceRegister).where(
            AttendanceRegister.date_of_attendance == param_date
        )
    )
    data = {"daily_attendance": attendance}

    form = LeaveAttendanceRegisterForm(data=data)
    if form.validate_on_submit():
        for attendance_form in form.daily_attendance.data:
            person = db.get_or_404(AttendanceRegister, attendance_form["id"])
            person.status_of_attendance = attendance_form["status_of_attendance"]

        db.session.commit()

        return redirect(url_for(".leave_attendance_list"))

    return render_template("daily_attendance.html", form=form, date_string=param_date)


@leave_mgmt_bp.route("/attendance/pending_leaves/", methods=["GET", "POST"])
@login_required
def pending_leaves_list():
    pending = db.session.execute(
        db.select(
            AttendanceRegister.employee_name,
            func.count(AttendanceRegister.status_of_attendance),
        )
        .where(
            (
                AttendanceRegister.status_of_attendance.in_(
                    ["On leave", "On leave-half day"]
                )
            )
            & (AttendanceRegister.type_of_leave.is_(None))
        )
        .group_by(AttendanceRegister.employee_name)
    )
    return render_template("pending_leaves_count.html", pending=pending)


@leave_mgmt_bp.route("/leave_application/")
@login_required
def leave_application_list():
    leave_balance = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == current_user.username[-5:])
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )
    list = db.session.scalars(
        db.select(LeaveApplication)
        .where(
            (LeaveApplication.employee_number == current_user.username[-5:])
            & (LeaveApplication.current_status != "Deleted")
        )
        .order_by(LeaveApplication.start_date.desc())
    )
    return render_template(
        "leave_application_list.html",
        list=list,
        leave_balance=leave_balance,
    )


@leave_mgmt_bp.route("/leave_application/edit/<int:id>/", methods=["GET", "POST"])
@login_required
def leave_application_edit(id):
    leave = db.get_or_404(LeaveApplication, id)
    form = LeaveApplicationForm(obj=leave)
    if form.validate_on_submit():
        form.populate_obj(leave)
        leave.current_status = "Submitted"
        db.session.commit()
        return redirect(url_for(".leave_application_list"))
    return render_template("leave_application_edit.html", form=form, leave=leave)


@leave_mgmt_bp.route("/leave_application/view/<int:id>/", methods=["GET", "POST"])
@login_required
def leave_application_view(id):
    leave = db.get_or_404(LeaveApplication, id)

    if request.method == "POST":
        leave.current_status = "Deleted"
        register_days = (
            db.session.query(AttendanceRegister)
            .filter(AttendanceRegister.id.in_(leave.list_attendance_register_days))
            .update({"type_of_leave": None})
        )
        delete_leave_application(id)
        db.session.commit()
        return redirect(url_for(".leaves_taken_list", status="pending"))

    return render_template("leave_application_view.html", leave=leave)


def delete_leave_application(leave_id):
    employee_number, leave_type, days_on_leave = db.session.execute(
        db.select(
            LeaveApplication.employee_number,
            LeaveApplication.type_of_leave,
            LeaveApplication.number_of_days_leave,
        ).where(LeaveApplication.id == leave_id)
    ).one()
    employee = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == employee_number)
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )
    leave_taken_attribute = get_leave_taken_attribute(leave_type)

    leave_balance_attribute = get_leave_balance_attribute(leave_type)

    setattr(
        employee,
        leave_taken_attribute,
        getattr(employee, leave_taken_attribute) - days_on_leave,
    )
    if leave_balance_attribute:
        setattr(
            employee,
            leave_balance_attribute,
            getattr(employee, leave_balance_attribute) + days_on_leave,
        )


@leave_mgmt_bp.route("/leave_application/print/<int:id>/", methods=["GET", "POST"])
@login_required
def leave_application_print(id):
    leave = db.get_or_404(LeaveApplication, id)

    return render_template("leave_application_print.html", leave=leave)


@leave_mgmt_bp.route("/employee/data/")
@login_required
def employee_data_list():
    list = db.session.scalars(db.select(EmployeeData))
    return render_template("employee_data_list.html", list=list)


@leave_mgmt_bp.route("/employee/data/add", methods=["GET", "POST"])
@login_required
def add_employee_data():
    form = EmployeeDataForm()
    if form.validate_on_submit():
        employee = EmployeeData()
        form.populate_obj(employee)
        try:
            db.session.add(employee)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("An employee with this data already exists.", "error")
            return render_template("flask_form_edit.html", form=form)

        return redirect(url_for(".employee_data_list"))

    return render_template("flask_form_edit.html", form=form)


@leave_mgmt_bp.route("/employee/data/edit/<int:id>/", methods=["GET", "POST"])
@login_required
def edit_employee_data(id):
    employee = db.get_or_404(EmployeeData, id)
    form = EmployeeDataForm(obj=employee)
    if form.validate_on_submit():
        try:
            form.populate_obj(employee)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("An employee with this data already exists.", "error")
            return render_template("flask_form_edit.html", form=form)

        return redirect(url_for(".employee_data_list"))

    return render_template("flask_form_edit.html", form=form)


@leave_mgmt_bp.route("/employee/leave_balance/")
@login_required
def leave_balance_list():
    column_names = db.session.query(LeaveBalance).statement.columns.keys()
    list = db.session.scalars(db.select(LeaveBalance).order_by(LeaveBalance.id))
    return render_template(
        "leave_balance_list.html", list=list, column_names=column_names
    )


@leave_mgmt_bp.route("/employee/leave_balance/add", methods=["GET", "POST"])
@login_required
def add_employee_leave_balance():
    form = AddEmployeeLeaveBalanceForm()
    if form.validate_on_submit():
        try:
            employee = LeaveBalance()
            form.populate_obj(employee)
            db.session.add(employee)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Employee already exists.", "danger")
        else:
            return redirect(url_for(".leave_balance_list"))

    return render_template("flask_form_edit.html", form=form)


@leave_mgmt_bp.route("/employee/leave_balance/edit/<int:id>/", methods=["GET", "POST"])
@login_required
def edit_employee_leave_balance(id):
    employee = db.get_or_404(LeaveBalance, id)
    form = AddEmployeeLeaveBalanceForm(obj=employee)
    if form.validate_on_submit():
        try:
            form.populate_obj(employee)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Employee already exists.", "danger")
        else:
            return redirect(url_for(".leave_balance_list"))
    return render_template("flask_form_edit.html", form=form)


@leave_mgmt_bp.route("/leaves_submitted/", methods=["GET", "POST"])
def update_leave_submitted_data():
    leave_date = db.session.scalars(db.select(LeaveSubmissionData)).one_or_none()
    form = LeaveSubmittedDateForm(obj=leave_date)
    if form.validate_on_submit():
        form.populate_obj(leave_date)
        db.session.commit()
        flash("Data has been saved successfully.")

    return render_template("flask_form_edit.html", form=form)


@leave_mgmt_bp.route("/leave_encashment/add", methods=["GET", "POST"])
def leave_encashment_add():
    leave_balance = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == current_user.username[-5:])
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )
    form = LeaveEncashmentForm()
    if leave_balance.leave_encashment_days:
        flash("Leave encashment already exhausted for given period.")

    elif form.validate_on_submit():
        # need to verify if sufficient balance is available
        earned_leave_balance = calculate_earned_leave(
            current_user.username[-5:], form.date_of_leave_encashment.data
        )
        if earned_leave_balance > form.leave_encashment_days.data:
            # if available, need to debit from earned leave balance.
            form.populate_obj(leave_balance)

            db.session.commit()
            flash("Leave encashment has been added.")
        else:
            flash("Insufficent earned leave balance for leave encashment.")
    return render_template("flask_form_edit.html", form=form)


@leave_mgmt_bp.route("/leave_balance/close", methods=["GET", "POST"])
def leave_balance_open_list():
    form = LeaveBalanceCloseForm()
    list = db.session.scalars(
        db.Select(LeaveBalance).where(LeaveBalance.current_status == "Open")
    )
    if form.validate_on_submit():
        list_leave_balance_keys = request.form.getlist("leave_balance_keys")
        for key in list_leave_balance_keys:
            leave_balance_close(db.get_or_404(LeaveBalance, key))
        flash("Leave balance has been closed for selected employees.")
        return redirect(url_for(".leave_balance_open_list"))
    return render_template("leave_balance_close_list.html", list=list, form=form)


def leave_balance_close(leave_balance):
    if not leave_balance.calendar_year >= date.today().year:
        leave_balance.current_status = "Closed"
        leave_balance.closing_balance_date = date(leave_balance.calendar_year, 12, 31)
        leave_balance.closing_casual_leave_balance = (
            leave_balance.current_casual_leave_balance
        )
        leave_balance.closing_sick_leave_balance = (
            leave_balance.current_sick_leave_balance
        )
        leave_balance.closing_rh_balance = leave_balance.current_rh_balance
        leave_balance.closing_privileged_leave_balance = calculate_earned_leave(
            leave_balance.employee_number, leave_balance.closing_balance_date
        )
        new_leave_balance = LeaveBalance(
            calendar_year=leave_balance.calendar_year + 1,
            employee_name=leave_balance.employee_name,
            employee_number=leave_balance.employee_number,
            opening_casual_leave_balance=12,
            opening_sick_leave_balance=min(
                leave_balance.current_sick_leave_balance + 30, 240
            ),
            opening_rh_balance=2,
            opening_privileged_leave_balance=calculate_earned_leave(
                leave_balance.employee_number, leave_balance.closing_balance_date
            ),
        )
        new_leave_balance.opening_balance_date = date(
            new_leave_balance.calendar_year, 1, 1
        )
        db.session.add(new_leave_balance)
        db.session.commit()

    else:
        return "Year not over."


@leave_mgmt_bp.route("/leaves_taken/<string:status>/", methods=["GET", "POST"])
@login_required
def leaves_taken_list(status):
    form = UpdateLeaveTypeForm(status="all")
    leave_balance = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == current_user.username[-5:])
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )
    calculate_earned_leave(current_user.username[-5:])
    query = (
        db.select(AttendanceRegister)
        .where(
            (AttendanceRegister.employee_number == current_user.username[-5:])
            & (AttendanceRegister.status_of_attendance == "On leave")
        )
        .order_by(AttendanceRegister.date_of_attendance)
    )

    if status == "submitted":
        query = query.where(AttendanceRegister.type_of_leave.is_not(None))
    elif status == "pending":
        query = query.where(AttendanceRegister.type_of_leave.is_(None))

    leaves_taken = db.session.scalars(query)

    if form.validate_on_submit():
        list_leave_keys = request.form.getlist("leave_keys")
        leaves = (
            db.session.query(AttendanceRegister)
            .with_entities(AttendanceRegister.date_of_attendance)
            .filter(AttendanceRegister.id.in_(list_leave_keys))
        )
        end_date, start_date = max(leaves)[0], min(leaves)[0]

        validate_status = validate_leave(
            form.leave_type.data,
            current_user.username[-5:],
            start_date,
            end_date,
            list_leave_keys,
        )
        if validate_status:
            return redirect(url_for(".leave_application_list"))
        else:
            flash(f"Not enough leave balance for {form.leave_type.data}")
    return render_template(
        "leaves_list.html",
        leaves_taken=leaves_taken,
        form=form,
        status=status,
        leave_balance=leave_balance,
    )


def get_leave_taken_attribute(leave_type):
    dict_leave_taken_attribute = {
        "Casual leave": "casual_leaves_taken",
        "Casual leave-half day": "casual_leaves_half_day_taken",
        "Restricted holiday": "restricted_holidays_taken",
        "Sick leave-half pay": "sick_leaves_taken",
        "Sick leave-full pay": "sick_leaves_taken",
        "Privilege leave": "privilege_leaves_taken",
        "Strike": "strike_taken",
        "Loss of pay": "lop_taken",
        "Joining leave": "joining_leave_taken",
        "Paternity leave": "paternity_leave_taken",
        "Maternity leave": "maternity_leave_taken",
        "Special leave": "special_leave_taken",
    }

    return dict_leave_taken_attribute.get(leave_type, None)


def get_leave_balance_attribute(leave_type):
    dict_leave_balance_attribute = {
        "Privilege leave": "current_privileged_leave_balance",
        "Casual leave": "current_casual_leave_balance",
        "Casual leave-half day": "current_casual_leave_balance",
        "Restricted holiday": "current_rh_balance",
        "Sick leave-half pay": "current_sick_leave_balance",
        "Sick leave-full pay": "current_sick_leave_balance",
    }
    return dict_leave_balance_attribute.get(leave_type, None)


def validate_leave(leave_type, employee_number, start_date, end_date, list_leave_keys):
    employee = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == employee_number)
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )
    days_on_leave = num_of_days(start_date, end_date) + 1

    leave_taken_attribute = get_leave_taken_attribute(leave_type)

    leave_balance_attribute = get_leave_balance_attribute(leave_type)

    if not leave_balance_attribute:
        setattr(
            employee,
            leave_taken_attribute,
            getattr(employee, leave_taken_attribute) + days_on_leave,
        )
        update_leave_balance(
            leave_type,
            start_date,
            end_date,
            days_on_leave,
            list_leave_keys,
            employee_number,
        )
        return True
    else:
        if leave_type in ["Casual leave", "Restricted holiday"]:
            days_on_leave = len(list_leave_keys)
        elif leave_type == "Casual leave-half day":
            days_on_leave = decimal.Decimal(len(list_leave_keys) / 2)

        elif leave_type == "Sick leave-full pay":
            days_on_leave = days_on_leave * 2
        if leave_type == "Privilege leave":
            available_leave_credit = calculate_earned_leave(
                employee_number,
                start_date + timedelta(days=-1),  # - 1
            )
        else:
            available_leave_credit = getattr(employee, leave_balance_attribute)
        if (available_leave_credit - days_on_leave) >= 0:
            setattr(
                employee,
                leave_taken_attribute,
                getattr(employee, leave_taken_attribute) + days_on_leave,
            )

            setattr(
                employee,
                leave_balance_attribute,
                available_leave_credit - days_on_leave,
            )
            update_leave_balance(
                leave_type,
                start_date,
                end_date,
                days_on_leave,
                list_leave_keys,
                employee_number,
                available_leave_credit,
            )
            return True
        else:
            return False


def update_leave_balance(
    leave_type,
    start_date,
    end_date,
    days_on_leave,
    list_leave_keys,
    employee_number,
    available_leave_credit=0,
):
    db.session.query(AttendanceRegister).filter(
        AttendanceRegister.id.in_(list_leave_keys)
    ).update({"type_of_leave": leave_type})

    employee = db.session.execute(
        db.select(EmployeeData).where(EmployeeData.employee_number == employee_number)
    ).one()
    employee_data_dict = [asdict(employee) for employee in employee][0]

    if leave_type == "Sick leave-full pay":
        num_of_days_off_duty = days_on_leave / 2
    elif leave_type in [
        "Sick leave-half pay",
        "Privilege leave",
        "Strike",
        "Loss of pay",
        "Paternity leave",
        "Maternity leave",
    ]:
        num_of_days_off_duty = days_on_leave
    else:
        num_of_days_off_duty = 0

    leave_application = LeaveApplication(
        **employee_data_dict,
        type_of_leave=leave_type,
        number_of_days_leave=days_on_leave,
        number_of_days_off_duty=num_of_days_off_duty,
        start_date=start_date,
        end_date=end_date,
        list_attendance_register_days=list_leave_keys,
        available_leave_credit=available_leave_credit,
    )
    db.session.add(leave_application)
    db.session.commit()


def populate_attendance_register(date):
    """
    Populates the attendance register for a given date with active employees who do not already have entries.

    Args:
        date (datetime.date): The date for which the attendance register is to be populated.

    The function checks if the attendance data for the given date has been submitted to the establishment department.
    If not, it retrieves a list of employee numbers already present in the attendance register for that date and
    compares it with the list of active employees. Any active employees missing from the register are added with a
    new entry for the given date.
    """

    if not last_leave_submitted_date(date):
        attendance_register_list = db.session.scalars(
            db.Select(AttendanceRegister.employee_number).where(
                AttendanceRegister.date_of_attendance == date
            )
        ).all()

        active_employee_list = db.session.scalars(
            db.Select(EmployeeData.employee_number).where(
                EmployeeData.current_status == "Active"
            )
        ).all()

        missing_active_employee_list = list(
            set(active_employee_list) - set(attendance_register_list)
        )

        if missing_active_employee_list:
            employee_data = db.session.scalars(
                db.Select(EmployeeData).where(
                    EmployeeData.employee_number.in_(missing_active_employee_list)
                )
            )

            attendance_entries = []
            for employee in employee_data:
                new_entry = AttendanceRegister(
                    **asdict(employee),
                    date_of_attendance=date,
                )
                attendance_entries.append(new_entry)
            db.session.add_all(attendance_entries)
            db.session.commit()


def last_leave_submitted_date(leave_date) -> bool:
    """
    Check if the given leave date is on or before the last submitted date to establishment dept.

    Args:
        leave_date (datetime.date or datetime.datetime): The date to be checked.

    Returns:
        bool: True if the date is on or before the last submitted date, False otherwise.
    """

    if isinstance(leave_date, datetime):
        leave_date = datetime.date(leave_date)

    if submitted_date := (
        db.session.scalars(
            db.select(LeaveSubmissionData.leaves_submitted_to_est_dept)
        ).one_or_none()
    ):
        return leave_date <= submitted_date
    else:
        submitted_date = LeaveSubmissionData(
            leaves_submitted_to_est_dept=datetime(2024, 12, 1)
        )
        db.session.add(submitted_date)
        db.session.commit()


@leave_mgmt_bp.context_processor
def get_leave_submission():
    return dict(
        leave_submitted=last_leave_submitted_date,
        calculate_earned_leave=calculate_earned_leave,
        to_mixed_fraction_11=to_mixed_fraction_11,
    )


def get_days_off_duty(employee_number, opening_balance_date, end_date=date.today()):
    off_duty_count = (
        db.session.query(func.sum(LeaveApplication.number_of_days_off_duty))
        .filter(
            and_(
                LeaveApplication.employee_number == employee_number,
                LeaveApplication.start_date >= opening_balance_date,
                LeaveApplication.start_date <= end_date,
                LeaveApplication.current_status != "Deleted",
            )
        )
        .scalar()
    )

    return off_duty_count or 0


def get_days_on_duty(employee_number, opening_balance_date, end_date=date.today()):
    off_duty_count = get_days_off_duty(employee_number, opening_balance_date, end_date)
    on_duty_count = num_of_days(opening_balance_date, end_date) - off_duty_count + 1

    return on_duty_count


def get_leave_balance_start_date(employee_number):
    leave_balance = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == employee_number)
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )

    return leave_balance.opening_balance_date


def get_earned_leave_taken(
    employee_number, opening_balance_date, end_date=date.today()
):
    earned_leave_count = (
        db.session.query(func.sum(LeaveApplication.number_of_days_leave))
        .filter(
            and_(
                LeaveApplication.employee_number == employee_number,
                LeaveApplication.type_of_leave == "Privilege leave",
                LeaveApplication.start_date >= opening_balance_date,
                LeaveApplication.start_date <= end_date,
                LeaveApplication.current_status != "Deleted",
            )
        )
        .scalar()
    )

    return earned_leave_count or 0


def get_leave_encashment_days(leave_balance, date_of_calculation=date.today()):
    if leave_balance.date_of_leave_encashment:
        return (
            leave_balance.leave_encashment_days
            if leave_balance.date_of_leave_encashment <= date_of_calculation
            else 0
        )
    else:
        return 0


def calculate_earned_leave(employee_number, date_of_calculation=date.today()):
    leave_balance = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == employee_number)
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )
    opening_earned_leave = float(leave_balance.opening_privileged_leave_balance)

    opening_balance_date = get_leave_balance_start_date(employee_number)

    on_duty_days = float(
        get_days_on_duty(
            employee_number, opening_balance_date, end_date=date_of_calculation
        )
    )
    earned_leave_count = float(
        get_earned_leave_taken(
            employee_number, opening_balance_date, end_date=date_of_calculation
        )
    )

    leave_encashment = float(
        get_leave_encashment_days(leave_balance, date_of_calculation)
    )
    closing_earned_leave = (
        opening_earned_leave
        - (earned_leave_count)
        - leave_encashment
        + on_duty_days / 11
    )

    return min(closing_earned_leave, 270)


def to_mixed_fraction_11(number):
    if not isinstance(number, (int, float, decimal.Decimal)):
        return "Invalid input. Please provide a number."

    # Get the integer part
    integer_part = floor(number)

    # Get the fractional part
    fractional_part = number - integer_part

    # Convert fractional part to a numerator with denominator 11
    numerator = round(fractional_part * 11)

    # Simplify if numerator equals the denominator (e.g., 11/11 = 1)
    if numerator == 11:
        return f"{integer_part + 1}"

    # If there's no fractional part, return only the integer
    if numerator == 0:
        return f"{integer_part}"

    # Return the mixed fraction
    return f"{integer_part if integer_part > 0 else ""} {numerator}/11"
