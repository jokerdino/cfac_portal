from datetime import datetime, date

from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import create_engine, case
import pandas as pd

from extensions import db
from set_view_permissions import admin_required

from . import leave_balance_bp
from .form import UploadFileForm, PrivilegeLeaveBulkUpdateForm, SickLeaveBulkUpdateForm
from .model import PrivilegeLeaveBalance, SickLeaveBalance


@leave_balance_bp.route("/upload/", methods=["GET", "POST"])
@login_required
@admin_required
def employee_list_upload():
    form = UploadFileForm()
    if form.validate_on_submit():
        employee_list = form.data["file_upload"]
        df_employee_list = pd.read_excel(employee_list)
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        df_employee_list["created_on"] = datetime.now()
        df_employee_list["created_by"] = current_user.username

        df_employee_list.to_sql(
            "privilege_leave_balance",
            engine,
            if_exists="append",
            index=False,
        )
        df_employee_list.to_sql(
            "sick_leave_balance",
            engine,
            if_exists="append",
            index=False,
        )
        flash("Employee list has been uploaded successfully.")

    return render_template(
        "leave_balance_file_upload.html", form=form, title="Upload employee list"
    )


@leave_balance_bp.route("/pl/", methods=["GET", "POST"])
@login_required
def update_pl():
    case_designation = order_by_designation(PrivilegeLeaveBalance)
    pl_data = db.session.scalars(
        db.select(PrivilegeLeaveBalance)
        .where(PrivilegeLeaveBalance.employee_oo_code == current_user.oo_code)
        .order_by(
            case_designation.asc(),
            PrivilegeLeaveBalance.employee_number.asc(),
        )
    )
    form_data = {"privilege_leave": pl_data}
    form = PrivilegeLeaveBulkUpdateForm(data=form_data)
    if form.validate_on_submit():
        for pl_form in form.privilege_leave.data:
            person = db.get_or_404(PrivilegeLeaveBalance, pl_form["id"])
            person.opening_balance = pl_form["opening_balance"]
            person.leave_accrued = pl_form["leave_accrued"]
            person.leave_availed = pl_form["leave_availed"]
            person.leave_encashed = pl_form["leave_encashed"]
            person.leave_lapsed = pl_form["leave_lapsed"]
            person.closing_balance = pl_form["closing_balance"]
        db.session.commit()

        return redirect(url_for(".update_pl"))

    return render_template("pl_balance_update.html", form=form)


@leave_balance_bp.route("/sl/", methods=["GET", "POST"])
@login_required
def update_sl():
    case_designation = order_by_designation(SickLeaveBalance)
    pl_data = db.session.scalars(
        db.select(SickLeaveBalance)
        .where(SickLeaveBalance.employee_oo_code == current_user.oo_code)
        .order_by(
            case_designation.asc(),
            SickLeaveBalance.employee_number.asc(),
        )
    )
    form_data = {"sick_leave": pl_data}
    form = SickLeaveBulkUpdateForm(data=form_data)
    if form.validate_on_submit():
        for pl_form in form.sick_leave.data:
            person = db.get_or_404(SickLeaveBalance, pl_form["id"])
            person.opening_balance = pl_form["opening_balance"]
            person.leave_accrued = pl_form["leave_accrued"]
            person.leave_availed = pl_form["leave_availed"]
            person.leave_lapsed = pl_form["leave_lapsed"]
            person.closing_balance = pl_form["closing_balance"]
        db.session.commit()

        return redirect(url_for(".update_sl"))

    return render_template("sl_balance_update.html", form=form)


def order_by_designation(model):
    designation_list = [
        "CMD",
        "Executive Director",
        "General Manager",
        "Deputy General Mngr",
        "Chief Manager",
        "Manager",
        "Deputy Manager",
        "Assistant Manager",
        "Administrative Off",
        "Development Off-I",
        "Senior Assistant",
        "Stenographer",
        "Assistant",
        "Record Clerk",
        "Driver",
        "Sub – Staff",
        " Other Sub Staff",
    ]

    case_designation = case(
        *[
            (getattr(model, "employee_designation") == value, index)
            for index, value in enumerate(designation_list)
        ],
        else_=len(designation_list),  # Fallback for values not in the list
    )
    return case_designation
