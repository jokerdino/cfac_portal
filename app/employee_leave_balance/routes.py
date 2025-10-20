from datetime import datetime
from io import BytesIO
from flask import (
    abort,
    flash,
    redirect,
    render_template,
    url_for,
    send_file,
)
from flask_login import current_user, login_required
from sqlalchemy import case, func
import pandas as pd

from extensions import db
from set_view_permissions import admin_required, ro_user_only

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

        df_employee_list["employee_ro_code"] = (
            df_employee_list["employee_ro_code"].astype(str).str.zfill(6)
        )
        df_employee_list["employee_oo_code"] = (
            df_employee_list["employee_oo_code"].astype(str).str.zfill(6)
        )
        df_employee_list["created_on"] = datetime.now()
        df_employee_list["created_by"] = current_user.username

        df_employee_list.to_sql(
            "privilege_leave_balance",
            db.engine,
            if_exists="append",
            index=False,
        )
        df_employee_list.to_sql(
            "sick_leave_balance",
            db.engine,
            if_exists="append",
            index=False,
        )
        flash("Employee list has been uploaded successfully.")

    return render_template(
        "leave_balance_file_upload.html", form=form, title="Upload employee list"
    )


@leave_balance_bp.route("/pl/", defaults={"oo_code": None}, methods=["GET", "POST"])
@leave_balance_bp.route("/pl/<string:oo_code>/", methods=["GET", "POST"])
@login_required
def update_pl(oo_code):
    oo_code = get_oo_code(oo_code)
    case_designation = order_by_designation(PrivilegeLeaveBalance)
    pl_data = db.session.scalars(
        db.select(PrivilegeLeaveBalance)
        .where(PrivilegeLeaveBalance.employee_oo_code == oo_code)
        .order_by(
            case_designation.asc(),
            PrivilegeLeaveBalance.employee_number.asc(),
        )
    )
    form_data = {"privilege_leave": pl_data}
    form = PrivilegeLeaveBulkUpdateForm(data=form_data)
    if form.validate_on_submit():
        for pl_form in form.privilege_leave.entries:
            person = db.get_or_404(PrivilegeLeaveBalance, pl_form.data["id"])
            pl_form.form.populate_obj(person)
        db.session.commit()
        flash("Employee leave balance has been updated successfully.")
        return redirect(url_for(".update_pl", oo_code=oo_code))

    return render_template("pl_balance_update.html", form=form)


@leave_balance_bp.route("/sl/", defaults={"oo_code": None}, methods=["GET", "POST"])
@leave_balance_bp.route("/sl/<string:oo_code>/", methods=["GET", "POST"])
@login_required
def update_sl(oo_code):
    oo_code = get_oo_code(oo_code)
    case_designation = order_by_designation(SickLeaveBalance)
    sl_data = db.session.scalars(
        db.select(SickLeaveBalance)
        .where(SickLeaveBalance.employee_oo_code == oo_code)
        .order_by(
            case_designation.asc(),
            SickLeaveBalance.employee_number.asc(),
        )
    )
    form_data = {"sick_leave": sl_data}
    form = SickLeaveBulkUpdateForm(data=form_data)
    if form.validate_on_submit():
        for sl_form in form.sick_leave.entries:  # Use .entries instead of .data
            person = db.get_or_404(SickLeaveBalance, sl_form.data["id"])
            sl_form.form.populate_obj(person)  # Use form instance to populate object
        db.session.commit()
        flash("Employee leave balance has been updated successfully.")
        return redirect(url_for(".update_sl", oo_code=oo_code))

    return render_template("sl_balance_update.html", form=form)


@leave_balance_bp.route(
    "/dashboard/", defaults={"ro_code": None}, methods=["GET", "POST"]
)
@leave_balance_bp.route("/dashboard/<string:ro_code>/", methods=["GET", "POST"])
@login_required
@ro_user_only
def view_ro_dashboard(ro_code):
    ro_code = get_oo_code(ro_code)
    stmt = (
        db.select(
            PrivilegeLeaveBalance.employee_ro_code,
            PrivilegeLeaveBalance.employee_oo_code,
            func.count(PrivilegeLeaveBalance.id).label("employee_count"),
            (
                func.count(PrivilegeLeaveBalance.id)
                - func.count(PrivilegeLeaveBalance.closing_balance)
            ).label("pending_pl_data"),
            (
                func.count(PrivilegeLeaveBalance.id)
                - func.count(SickLeaveBalance.closing_balance)
            ).label("pending_sl_data"),
        )
        .join(
            SickLeaveBalance,
            SickLeaveBalance.employee_number == PrivilegeLeaveBalance.employee_number,
        )
        .where(PrivilegeLeaveBalance.employee_ro_code == ro_code)
        .group_by(
            PrivilegeLeaveBalance.employee_ro_code,
            PrivilegeLeaveBalance.employee_oo_code,
        )
        .order_by(
            PrivilegeLeaveBalance.employee_ro_code,
            PrivilegeLeaveBalance.employee_oo_code,
        )
    )
    query = db.session.execute(stmt)
    return render_template("view_ro_dashboard.html", query=query)


@leave_balance_bp.route("/ho_dashboard/", methods=["GET", "POST"])
@login_required
@admin_required
def view_ho_dashboard():
    stmt = (
        db.select(
            PrivilegeLeaveBalance.employee_ro_code,
            func.count(PrivilegeLeaveBalance.id).label("employee_count"),
            (
                func.count(PrivilegeLeaveBalance.id)
                - func.count(PrivilegeLeaveBalance.closing_balance)
            ).label("pending_pl_data"),
            (
                func.count(PrivilegeLeaveBalance.id)
                - func.count(SickLeaveBalance.closing_balance)
            ).label("pending_sl_data"),
        )
        .join(
            SickLeaveBalance,
            SickLeaveBalance.employee_number == PrivilegeLeaveBalance.employee_number,
        )
        .group_by(
            PrivilegeLeaveBalance.employee_ro_code,
        )
        .order_by(
            PrivilegeLeaveBalance.employee_ro_code,
        )
    )
    query = db.session.execute(stmt)

    return render_template("view_ho_dashboard.html", query=query)


@leave_balance_bp.route("/download/")
@login_required
@admin_required
def download_data():
    pl_query = db.select(
        PrivilegeLeaveBalance.calendar_year,
        PrivilegeLeaveBalance.employee_ro_code,
        PrivilegeLeaveBalance.employee_oo_code,
        PrivilegeLeaveBalance.employee_name,
        PrivilegeLeaveBalance.employee_designation,
        PrivilegeLeaveBalance.employee_number,
        PrivilegeLeaveBalance.opening_balance,
        PrivilegeLeaveBalance.leave_accrued,
        PrivilegeLeaveBalance.leave_availed,
        PrivilegeLeaveBalance.leave_encashed,
        PrivilegeLeaveBalance.leave_lapsed,
        PrivilegeLeaveBalance.closing_balance,
    ).order_by(
        PrivilegeLeaveBalance.calendar_year,
        PrivilegeLeaveBalance.employee_ro_code,
        PrivilegeLeaveBalance.employee_oo_code,
        PrivilegeLeaveBalance.employee_designation,
    )
    sl_query = db.select(
        SickLeaveBalance.calendar_year,
        SickLeaveBalance.employee_ro_code,
        SickLeaveBalance.employee_oo_code,
        SickLeaveBalance.employee_name,
        SickLeaveBalance.employee_designation,
        SickLeaveBalance.employee_number,
        SickLeaveBalance.opening_balance,
        SickLeaveBalance.leave_accrued,
        SickLeaveBalance.leave_availed,
        SickLeaveBalance.leave_lapsed,
        SickLeaveBalance.closing_balance,
    ).order_by(
        SickLeaveBalance.calendar_year,
        SickLeaveBalance.employee_ro_code,
        SickLeaveBalance.employee_oo_code,
        SickLeaveBalance.employee_designation,
    )
    with db.engine.connect() as conn:
        df_pl = pd.read_sql(pl_query, conn)
        df_sl = pd.read_sql(sl_query, conn)

    output = BytesIO()
    with pd.ExcelWriter(output) as writer:
        df_pl.to_excel(writer, sheet_name="Privilege Leave", index=False)
        df_sl.to_excel(writer, sheet_name="Sick Leave", index=False)

    # Set the buffer position to the beginning
    output.seek(0)

    filename = f"leave_balance_data_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"

    return send_file(output, as_attachment=True, download_name=filename)


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


def get_oo_code(oo_code):
    if oo_code is None:
        return current_user.oo_code
    elif current_user.user_type == "oo_user":
        return current_user.oo_code
    elif current_user.user_type == "ro_user":
        if ((int(oo_code) // 10000) * 10000) == int(current_user.ro_code):
            return oo_code
        return current_user.ro_code
    elif current_user.user_type == "admin":
        return oo_code
