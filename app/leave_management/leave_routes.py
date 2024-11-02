from dataclasses import asdict
from datetime import datetime

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from sqlalchemy import func, case


from . import leave_mgmt_bp
from .leave_model import (
    LeaveApplication,
    LeaveBalance,
    EmployeeData,
    AttendanceRegister,
)

from .leave_forms import (
    AddEmployeeLeaveBalanceForm,
    EmployeeDataForm,
    LeaveAttendanceRegisterForm,
    UpdateLeaveTypeForm,
    LeaveApplicationForm,
)

from extensions import db


def num_of_days(start_date, end_date):
    return (end_date - start_date).days


@leave_mgmt_bp.route("/attendance/")
@login_required
def leave_attendance_list():

    # status_query = db.session.execute(
    #     db.select(AttendanceRegister.status_of_attendance).distinct()
    # )
    attendance_status_list = ["Present", "On leave", "On duty", "On tour"]
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
    print(list)
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
    return render_template("daily_attendance.html", form=form)


@leave_mgmt_bp.route("/leave_application/")
@login_required
def leave_application_list():
    list = db.session.scalars(
        db.select(LeaveApplication).where(
            LeaveApplication.employee_number == current_user.username[-5:]
        )
    )
    return render_template("leave_application_list.html", list=list)


@leave_mgmt_bp.route("/leave_application/edit/<int:id>/", methods=["GET", "POST"])
@login_required
def leave_application_edit(id):
    leave = db.get_or_404(LeaveApplication, id)
    form = LeaveApplicationForm(obj=leave)
    if form.validate_on_submit():
        form.populate_obj(leave)
        db.session.commit()
        return redirect(url_for(".leave_application_list"))
    return render_template("leave_application_edit.html", form=form, leave=leave)


@leave_mgmt_bp.route("/leave_application/view/<int:id>/", methods=["GET", "POST"])
@login_required
def leave_application_view(id):
    leave = db.get_or_404(LeaveApplication, id)

    return render_template("leave_application_view.html", leave=leave)


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
        db.session.add(employee)
        db.session.commit()

    return render_template("flask_form_edit.html", form=form)


@leave_mgmt_bp.route("/employee/data/edit/<int:id>/", methods=["GET", "POST"])
@login_required
def edit_employee_data(id):
    employee = db.get_or_404(EmployeeData, id)
    form = EmployeeDataForm(obj=employee)
    if form.validate_on_submit():

        form.populate_obj(employee)

        db.session.commit()

    return render_template("flask_form_edit.html", form=form)


@leave_mgmt_bp.route("/employee/")
@login_required
def leave_balance_list():
    column_names = db.session.query(LeaveBalance).statement.columns.keys()
    list = db.session.scalars(db.select(LeaveBalance).order_by(LeaveBalance.id))
    return render_template(
        "leave_balance_list.html", list=list, column_names=column_names
    )


@leave_mgmt_bp.route("/employee/add", methods=["GET", "POST"])
@login_required
def add_employee_leave_balance():
    form = AddEmployeeLeaveBalanceForm()
    if form.validate_on_submit():
        employee = LeaveBalance()
        form.populate_obj(employee)
        db.session.add(employee)
        db.session.commit()

    return render_template("flask_form_edit.html", form=form)


@leave_mgmt_bp.route("/employee/edit/<int:id>/", methods=["GET", "POST"])
@login_required
def edit_employee_leave_balance(id):
    employee = db.get_or_404(LeaveBalance, id)
    form = AddEmployeeLeaveBalanceForm(obj=employee)
    if form.validate_on_submit():

        form.populate_obj(employee)

        db.session.commit()

    return render_template("flask_form_edit.html", form=form)


@leave_mgmt_bp.route("/leaves_taken/", methods=["GET", "POST"])
@login_required
def leaves_list():
    form = UpdateLeaveTypeForm()
    leaves_taken = db.session.scalars(
        db.select(AttendanceRegister).where(
            (AttendanceRegister.employee_number == current_user.username[-5:])
            & (AttendanceRegister.status_of_attendance == "On leave")
            & (AttendanceRegister.type_of_leave.is_(None))
        )
    )
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

            ...
        else:
            flash(f"Not enough leave balance for {form.leave_type.data}")
    return render_template("leaves_list.html", leaves_taken=leaves_taken, form=form)


def validate_leave(leave_type, employee_number, start_date, end_date, list_leave_keys):
    employee = (
        db.session.query(LeaveBalance).filter_by(employee_number=employee_number).one()
    )
    days_on_leave = num_of_days(start_date, end_date) + 1

    dict_leave_balance_attribute = {
        "Privilege leave": "current_privileged_leave_balance",
        "Casual leave": "current_casual_leave_balance",
        "Restricted holiday": "current_rh_balance",
        "Sick leave-half pay": "current_sick_leave_balance",
        "Sick leave-full pay": "current_sick_leave_balance",
    }
    dict_leave_taken_attribute = {
        "Casual leave": "casual_leaves_taken",
        "Restricted holiday": "restricted_holidays_taken",
        "Sick leave-half pay": "sick_leaves_taken",
        "Sick leave-full pay": "sick_leaves_taken",
        "Privilege leave": "privilege_leaves_taken",
        "Strike": "strike_taken",
        "Loss of pay": "lop_taken",
        "Paternity leave": "paternity_leave_taken",
        "Maternity leave": "maternity_leave_taken",
        "Special leave": "special_leave_taken",
    }

    leave_taken_attribute = dict_leave_taken_attribute.get(leave_type, None)

    leave_balance_attribute = dict_leave_balance_attribute.get(leave_type, None)

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
        elif leave_type == "Sick leave-full pay":
            days_on_leave = days_on_leave * 2

        if (getattr(employee, leave_balance_attribute) - days_on_leave) >= 0:
            setattr(
                employee,
                leave_taken_attribute,
                getattr(employee, leave_taken_attribute) + days_on_leave,
            )

            setattr(
                employee,
                leave_balance_attribute,
                getattr(employee, leave_balance_attribute) - days_on_leave,
            )
            update_leave_balance(
                leave_type,
                start_date,
                end_date,
                days_on_leave,
                list_leave_keys,
                employee_number,
                getattr(employee, leave_balance_attribute),
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
    # print(employee_data_dict)
    leave_application = LeaveApplication(
        **employee_data_dict,
        type_of_leave=leave_type,
        number_of_days_leave=days_on_leave,
        start_date=start_date,
        end_date=end_date,
        list_attendance_register_days=list_leave_keys,
        available_leave_credit=available_leave_credit,
    )
    db.session.add(leave_application)
    db.session.commit()


def populate_attendance_register(date):
    # list of all employees currently populated in register

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
