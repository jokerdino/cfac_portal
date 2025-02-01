from dataclasses import asdict
from datetime import datetime, date, timedelta
from math import floor
import decimal
from itertools import chain

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
import pandas as pd
from sqlalchemy import case, func, and_, create_engine
from sqlalchemy.exc import IntegrityError

import calplot
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("agg")

from extensions import db
from set_view_permissions import leave_managers, admin_required

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
    UploadFileForm,
)
from .leave_model import (
    AttendanceRegister,
    EmployeeData,
    LeaveApplication,
    LeaveBalance,
    LeaveSubmissionData,
    PublicHoliday,
)


def num_of_days(start_date, end_date):
    return (end_date - start_date).days


@leave_mgmt_bp.route("/home/")
@login_required
@admin_required
def leave_home():
    if current_user.role and "leave_manager" in current_user.role:
        return redirect(
            url_for(".edit_attendance", date_string=date.today().strftime("%d%m%Y"))
        )
    else:
        return redirect(url_for(".leaves_taken_list", status="pending"))


@leave_mgmt_bp.route("/attendance/", methods=["GET", "POST"])
@login_required
@leave_managers
def leave_attendance_list():
    attendance_status_list = [
        "Present",
        "On leave",
        "On leave-half day",
        "On duty",
        "On tour",
    ]
    case_status = {
        status: case(
            (
                AttendanceRegister.status_of_attendance == status,
                AttendanceRegister.status_of_attendance,
            )
        )
        for status in attendance_status_list
    }
    entities_list = [
        func.count(case_status[status]) for status in attendance_status_list
    ]
    attendance_list = db.session.execute(
        db.select(
            AttendanceRegister.date_of_attendance,
            *entities_list,
            func.count(AttendanceRegister.status_of_attendance),
        )
        .group_by(AttendanceRegister.date_of_attendance)
        .order_by(AttendanceRegister.date_of_attendance.desc())
    )

    if request.method == "POST":
        list_date_keys = request.form.getlist("date_keys")

        date_list = [datetime.strptime(item, "%Y-%m-%d") for item in list_date_keys]

        db.session.query(AttendanceRegister).filter(
            AttendanceRegister.date_of_attendance.in_(date_list)
        ).delete()

        db.session.commit()

        flash(
            f"Given date(s) {', '.join(date_item.strftime('%d/%m/%Y') for date_item in date_list)} have been deleted."
        )

        return redirect(url_for(".leave_attendance_list"))
    return render_template("leave_attendance_list.html", list=attendance_list)


@leave_mgmt_bp.route("/attendance/<string:date_string>/", methods=["GET", "POST"])
@login_required
@leave_managers
def edit_attendance(date_string):
    param_date = datetime.strptime(date_string, "%d%m%Y")
    populate_attendance_register(param_date)

    case_designation = order_by_designation(AttendanceRegister)
    attendance = db.session.scalars(
        db.select(AttendanceRegister)
        .where(AttendanceRegister.date_of_attendance == param_date)
        .order_by(
            case_designation.desc(), AttendanceRegister.date_of_joining_current_cadre
        )
    )
    form_data = {"daily_attendance": attendance}

    form = LeaveAttendanceRegisterForm(data=form_data)
    if form.validate_on_submit():
        for attendance_form in form.daily_attendance.data:
            person = db.get_or_404(AttendanceRegister, attendance_form["id"])
            person.status_of_attendance = attendance_form["status_of_attendance"]

        db.session.commit()

        return redirect(url_for(".leave_attendance_list"))

    return render_template("daily_attendance.html", form=form, date_string=param_date)


@leave_mgmt_bp.route("/attendance/pending_leaves/", methods=["GET", "POST"])
@login_required
@leave_managers
def pending_leaves_list():
    pending = db.session.execute(
        db.select(
            AttendanceRegister.employee_name,
            AttendanceRegister.employee_number,
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
        .group_by(AttendanceRegister.employee_name, AttendanceRegister.employee_number)
    )
    return render_template("pending_leaves_count.html", pending=pending)


def get_employee_number(employee_number):
    """
    Return the employee number, defaulting to the last 5 characters of the current_user's username
    if the current_user is not a leave_manager and no employee_number is given.
    """
    if current_user.role and "leave_manager" not in current_user.role:
        return current_user.username[-5:]
    elif employee_number is None:
        return current_user.username[-5:]
    else:
        return employee_number


@leave_mgmt_bp.route("/leave_application/", defaults={"employee_number": None})
@leave_mgmt_bp.route("/leave_application/<int:employee_number>/")
@login_required
@admin_required
def leave_application_list(employee_number):
    employee_number = get_employee_number(employee_number)
    leave_balance = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == employee_number)
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )

    leave_application_list_days = (
        db.session.query(LeaveApplication)
        .filter(
            and_(
                LeaveApplication.employee_number == employee_number,
                LeaveApplication.current_status != "Deleted",
            )
        )
        .order_by(LeaveApplication.start_date.desc())
    )

    #   get_leave_days_list(leave_application_list_days)
    return render_template(
        "leave_application_list.html",
        list=leave_application_list_days,
        leave_balance=leave_balance,
    )


def get_leave_days_list(list_leave_applications):
    leave_days_list = list(
        chain.from_iterable(
            [leave_app.list_of_days for leave_app in list_leave_applications]
        )
    )

    #  print(leave_days_list)

    return leave_days_list


@leave_mgmt_bp.route("/leave_application/edit/<int:id>/", methods=["GET", "POST"])
@login_required
@admin_required
def leave_application_edit(id):
    leave = db.get_or_404(LeaveApplication, id)
    form = LeaveApplicationForm(obj=leave)
    if form.validate_on_submit():
        form.populate_obj(leave)
        leave.current_status = "Submitted"
        db.session.commit()
        return redirect(
            url_for(".leave_application_list", employee_number=leave.employee_number)
        )
    return render_template("leave_application_edit.html", form=form, leave=leave)


@leave_mgmt_bp.route("/leave_application/view/<int:id>/", methods=["GET", "POST"])
@login_required
@admin_required
def leave_application_view(id):
    leave = db.get_or_404(LeaveApplication, id)

    if request.method == "POST":
        leave.current_status = "Deleted"

        db.session.query(AttendanceRegister).filter(
            AttendanceRegister.id.in_(leave.list_attendance_register_days)
        ).update({"type_of_leave": None})

        delete_leave_application(id)
        db.session.commit()
        return redirect(
            url_for(
                ".leaves_taken_list",
                status="pending",
                employee_number=leave.employee_number,
            )
        )

    return render_template("leave_application_view.html", leave=leave)


def delete_leave_application(leave_id):
    """Delete a leave application and update the leave balance accordingly."""
    query = db.session.execute(
        db.select(
            LeaveApplication.employee_number,
            LeaveApplication.type_of_leave,
            LeaveApplication.number_of_days_leave,
        ).where(LeaveApplication.id == leave_id)
    )
    employee_number, leave_type, days_on_leave = query.one()
    employee = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == employee_number)
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )
    leave_taken_attribute = get_leave_taken_attribute(leave_type)
    leave_balance_attribute = get_leave_balance_attribute(leave_type)

    employee_leave_taken = getattr(employee, leave_taken_attribute)
    setattr(employee, leave_taken_attribute, employee_leave_taken - days_on_leave)
    if leave_balance_attribute:
        employee_leave_balance = getattr(employee, leave_balance_attribute)
        setattr(
            employee, leave_balance_attribute, employee_leave_balance + days_on_leave
        )


@leave_mgmt_bp.route("/leave_application/print/<int:id>/", methods=["GET", "POST"])
@login_required
@admin_required
def leave_application_print(id):
    leave = db.get_or_404(LeaveApplication, id)

    return render_template("leave_application_print.html", leave=leave)


@leave_mgmt_bp.route("/employee/data/")
@login_required
@leave_managers
def employee_data_list():
    case_designation = order_by_designation(EmployeeData)

    query = db.session.scalars(
        db.select(EmployeeData).order_by(
            case_designation.desc(), EmployeeData.date_of_joining_current_cadre
        )
    )
    return render_template("employee_data_list.html", list=query)


def order_by_designation(model):
    designation_list = [
        "Assistant",
        "Senior Assistant",
        "Admin Officer",
        "Assistant Manager",
        "Deputy Manager",
        "Manager",
        "Chief Manager",
    ]

    case_designation = case(
        *[
            (getattr(model, "employee_designation") == value, index)
            for index, value in enumerate(designation_list)
        ],
        else_=len(designation_list),  # Fallback for values not in the list
    )
    return case_designation


@leave_mgmt_bp.route("/employee/data/add", methods=["GET", "POST"])
@login_required
@leave_managers
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

    return render_template("flask_form_edit.html", form=form, title="Add employee data")


@leave_mgmt_bp.route("/employee/data/edit/<int:id>/", methods=["GET", "POST"])
@login_required
@leave_managers
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

    return render_template(
        "flask_form_edit.html", form=form, title="Edit employee data"
    )


@leave_mgmt_bp.route("/employee/leave_balance/")
@login_required
@leave_managers
def leave_balance_list():
    column_names = db.session.query(LeaveBalance).statement.columns.keys()
    list = db.session.scalars(db.select(LeaveBalance).order_by(LeaveBalance.id))
    return render_template(
        "leave_balance_list.html", list=list, column_names=column_names
    )


@leave_mgmt_bp.route("/employee/leave_balance/add", methods=["GET", "POST"])
@login_required
@leave_managers
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

    return render_template("flask_form_edit.html", form=form, title="Add leave balance")


@leave_mgmt_bp.route("/employee/leave_balance/edit/<int:id>/", methods=["GET", "POST"])
@login_required
@leave_managers
def edit_employee_leave_balance(id):
    employee = db.get_or_404(LeaveBalance, id)
    if not employee.current_status == "Open":
        abort(404)
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
    return render_template(
        "flask_form_edit.html", form=form, title="Edit leave balance"
    )


@leave_mgmt_bp.route("/leaves_submitted/", methods=["GET", "POST"])
@login_required
@leave_managers
def update_leave_submitted_data():
    leave_date = db.session.scalars(db.select(LeaveSubmissionData)).one_or_none()
    form = LeaveSubmittedDateForm(obj=leave_date)
    if form.validate_on_submit():
        form.populate_obj(leave_date)
        db.session.commit()
        flash("Data has been saved successfully.")

    return render_template(
        "flask_form_edit.html",
        form=form,
        title="Update date of leave data submitted to establishment department",
    )


@leave_mgmt_bp.route(
    "/leave_encashment/add", defaults={"employee_number": None}, methods=["GET", "POST"]
)
@leave_mgmt_bp.route(
    "/leave_encashment/add/<int:employee_number>/", methods=["GET", "POST"]
)
@login_required
@admin_required
def leave_encashment_add(employee_number):
    employee_number = get_employee_number(employee_number)
    leave_balance = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == employee_number)
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )
    form = LeaveEncashmentForm()
    if leave_balance.leave_encashment_days:
        flash("Leave encashment already exhausted for given period.")

    elif form.validate_on_submit():
        # need to verify if sufficient balance is available
        earned_leave_balance = calculate_earned_leave(
            employee_number, form.date_of_leave_encashment.data
        )
        if earned_leave_balance >= form.leave_encashment_days.data:
            # if available, need to debit from earned leave balance.
            form.populate_obj(leave_balance)
            db.session.commit()
            flash("Leave encashment has been added.")
        else:
            flash("Insufficient earned leave balance for leave encashment.")
    return render_template(
        "flask_form_edit.html", form=form, title="Apply for leave encashment"
    )


@leave_mgmt_bp.route("/leave_balance/close", methods=["GET", "POST"])
@login_required
@leave_managers
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


@leave_mgmt_bp.route("/holiday/", defaults={"year": None})
@leave_mgmt_bp.route("/holiday/<string:year>/")
@login_required
@admin_required
def holiday_list(year):
    if not year:
        year = str(date.today().year)
    generate_holiday_plot(year)
    holiday_list = db.session.scalars(
        db.select(PublicHoliday).where(PublicHoliday.year == year)
    )
    image_source = f"holiday_plot_{year}.png"
    return render_template(
        "holiday_list.html", holiday_list=holiday_list, image=image_source, year=year
    )


@leave_mgmt_bp.route("/holiday/upload/", methods=["GET", "POST"])
@login_required
@leave_managers
def holiday_list_upload():
    form = UploadFileForm()
    if form.validate_on_submit():
        holiday_list = form.data["file_upload"]
        df_holiday_list = pd.read_excel(holiday_list)
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        df_holiday_list["created_on"] = datetime.now()
        df_holiday_list["created_by"] = current_user.username

        df_holiday_list.to_sql(
            "public_holiday",
            engine,
            if_exists="append",
            index=False,
        )
        flash("Public holiday list has been uploaded successfully.")

    return render_template(
        "leave_file_upload.html", form=form, title="Upload holiday list"
    )


def leave_balance_close(leave_balance):
    """Close a leave balance for a given year and open a new one."""
    if leave_balance.calendar_year < date.today().year:
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

        new_calendar_year = leave_balance.calendar_year + 1
        new_leave_balance = LeaveBalance(
            calendar_year=new_calendar_year,
            employee_name=leave_balance.employee_name,
            employee_number=leave_balance.employee_number,
            opening_casual_leave_balance=12,
            opening_sick_leave_balance=min(
                leave_balance.current_sick_leave_balance + 30, 240
            ),
            opening_rh_balance=2,
            opening_privileged_leave_balance=calculate_earned_leave(
                leave_balance.employee_number,
                date(new_calendar_year, 1, 1),
            ),
        )

        new_leave_balance.opening_balance_date = date(new_calendar_year, 1, 1)

        db.session.add(new_leave_balance)
        db.session.commit()


@leave_mgmt_bp.route(
    "/leaves_taken/<string:status>/",
    defaults={"employee_number": None},
    methods=["GET", "POST"],
)
@leave_mgmt_bp.route(
    "/leaves_taken/<string:status>/<int:employee_number>/", methods=["GET", "POST"]
)
@login_required
@admin_required
def leaves_taken_list(status, employee_number):
    form = UpdateLeaveTypeForm()
    employee_number = get_employee_number(employee_number)
    leave_balance = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == employee_number)
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )
    # calculate_earned_leave(employee_number)
    query = (
        db.select(AttendanceRegister)
        .where(
            (AttendanceRegister.employee_number == employee_number)
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
        try:
            end_date, start_date = max(leaves)[0], min(leaves)[0]
            validate_status = validate_leave(
                form.leave_type.data,
                employee_number,
                start_date,
                end_date,
                list_leave_keys,
            )
            if validate_status:
                return redirect(
                    url_for(".leave_application_list", employee_number=employee_number)
                )
            else:
                flash(f"Not enough leave balance for {form.leave_type.data}")
        except ValueError as e:
            flash("No leave days has been selected.")

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


def validate_leave(
    leave_type: str,
    employee_number: int,
    start_date: date,
    end_date: date,
    list_leave_keys: list,
) -> bool:
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
        available_leave_credit = getattr(employee, leave_balance_attribute)

        if leave_type in ["Casual leave", "Restricted holiday"]:
            days_on_leave = len(list_leave_keys)
        elif leave_type == "Casual leave-half day":
            days_on_leave = decimal.Decimal(len(list_leave_keys) / 2)
        elif leave_type == "Sick leave-full pay":
            days_on_leave = days_on_leave * 2
        elif leave_type == "Privilege leave":
            available_leave_credit = calculate_earned_leave(
                employee_number, start_date + timedelta(days=-1)
            )
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
        today_date=date.today(),
    )


def get_days_off_duty(employee_number, opening_balance_date, end_date):
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


def get_days_on_duty(
    employee_number: int, opening_balance_date: date, end_date: date
) -> int:
    """
    Calculate the number of days an employee was on duty between the given dates.

    Args:
        employee_number (int): The unique identifier of the employee.
        opening_balance_date (date): The start date of the leave balance period.
        end_date (date, optional): The end date of the period. Defaults to today.

    Returns:
        int: The number of days the employee was on duty.
    """

    # Calculate the number of off-duty days
    off_duty_days = get_days_off_duty(employee_number, opening_balance_date, end_date)

    # Calculate the total number of days in the period
    total_days = num_of_days(opening_balance_date, end_date) + 1

    # Calculate the number of on-duty days
    on_duty_days = total_days - off_duty_days

    return on_duty_days


def get_earned_leave_taken(
    employee_number: int, opening_balance_date: date, end_date: date
) -> float:
    """
    Calculate the total number of earned leave days taken by an employee between the opening balance date and the end date.
    """
    earned_leave_taken = (
        db.session.query(func.sum(LeaveApplication.number_of_days_leave))
        .filter(
            LeaveApplication.employee_number == employee_number,
            LeaveApplication.type_of_leave == "Privilege leave",
            LeaveApplication.start_date >= opening_balance_date,
            LeaveApplication.start_date <= end_date,
            LeaveApplication.current_status != "Deleted",
        )
        .scalar()
    )

    return earned_leave_taken or 0


def get_leave_encashment_days(leave_balance, calculation_date):
    if leave_balance.date_of_leave_encashment:
        if leave_balance.date_of_leave_encashment <= calculation_date:
            return leave_balance.leave_encashment_days
    return 0


def calculate_earned_leave(employee_number: int, date_of_calculation: date) -> float:
    """Calculate the earned leave balance of an employee as of a given date."""
    leave_balance = (
        db.session.query(LeaveBalance)
        .filter(LeaveBalance.employee_number == employee_number)
        .order_by(LeaveBalance.calendar_year.desc())
        .first_or_404()
    )

    opening_earned_leave_balance = float(leave_balance.opening_privileged_leave_balance)
    opening_balance_date = leave_balance.opening_balance_date

    on_duty_days = float(
        get_days_on_duty(
            employee_number, opening_balance_date, end_date=date_of_calculation
        )
    )
    earned_leave_taken = float(
        get_earned_leave_taken(
            employee_number, opening_balance_date, end_date=date_of_calculation
        )
    )
    leave_encashment = float(
        get_leave_encashment_days(leave_balance, date_of_calculation)
    )

    closing_earned_leave_balance = (
        opening_earned_leave_balance
        - earned_leave_taken
        - leave_encashment
        + on_duty_days / 11
    )

    return min(closing_earned_leave_balance, 270)


def to_mixed_fraction_11(number) -> str:
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
    return f"{integer_part if integer_part > 0 else ''} {numerator}/11"


def get_all_weekends(year: str) -> pd.DataFrame:
    def generate_date_ranges(target_year: str, frequency: str) -> list:
        next_year = str(int(target_year) + 1)
        date_range = pd.date_range(start=target_year, end=next_year, freq=frequency)
        return date_range.strftime("%m/%d/%Y").tolist()

    weekend_dates = generate_date_ranges(year, "W-SAT") + generate_date_ranges(
        year, "W-SUN"
    )

    weekend_df = pd.DataFrame(weekend_dates, columns=["date_of_holiday"])
    weekend_df["value"] = 5

    weekend_df["date_of_holiday"] = pd.to_datetime(
        weekend_df["date_of_holiday"], yearfirst=True
    )
    weekend_df.set_index("date_of_holiday", inplace=True)

    return weekend_df


def draw_holiday_plot(dataframe: pd.DataFrame, year: str):
    try:
        calplot.calplot(
            dataframe["value"],
            cmap="tab20",
            vmin=0,
            vmax=20,
            # figsize=(16, 20),
            # suptitle=title,
            how="sum",
            colorbar=False,
            # ax=legend
        )
        file_name = f"holiday_plot_{year}.png"
        #   plt.legend(legend)
        plt.savefig("static/" + file_name)
        plt.close()
    except Exception as e:
        print(e)


def generate_holiday_plot(year: str):
    if not year:
        year = str(date.today().year)

    holiday_query = db.session.query(PublicHoliday.date_of_holiday).filter_by(year=year)

    public_holidays = holiday_query.filter_by(type_of_list="PUBLIC HOLIDAY").all()
    state_holidays = holiday_query.filter_by(type_of_list="TAMIL NADU").all()
    all_india_holidays = holiday_query.filter_by(type_of_list="ALL INDIA").all()

    df_public_holidays = generate_pandas_timeseries(public_holidays, 1)
    df_state_holidays = generate_pandas_timeseries(state_holidays, 2)
    df_all_india_holidays = generate_pandas_timeseries(all_india_holidays, 3)

    df_weekends = get_all_weekends(year)

    df_combined = pd.concat(
        [df_public_holidays, df_state_holidays, df_all_india_holidays, df_weekends]
    )
    draw_holiday_plot(df_combined, year)


def generate_pandas_timeseries(dates: list, value: int) -> pd.DataFrame:
    date_list = [date[0] for date in dates]

    df = pd.DataFrame(date_list, columns=["date_of_holiday"])
    df["value"] = value

    df["date_of_holiday"] = pd.to_datetime(df["date_of_holiday"], yearfirst=True)
    df.set_index("date_of_holiday", inplace=True)

    return df
