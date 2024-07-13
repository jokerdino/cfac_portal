from datetime import datetime
from math import fabs

import pandas as pd
from flask import render_template, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user

from wtforms.validators import DataRequired

from sqlalchemy import func, create_engine

from app.ho_ro_recon import ho_ro_recon_bp

from app.ho_ro_recon.ho_ro_recon_form import (
    ReconEntriesForm,
    RegionalOfficeAcceptForm,
    HeadOfficeAcceptForm,
    ReconSummaryForm,
    UploadFileForm,
)
from app.ho_ro_recon.ho_ro_recon_model import ReconEntries, ReconSummary

from app.users.user_model import User


@ho_ro_recon_bp.route("/add", methods=["POST", "GET"])
@login_required
def add_ho_ro_recon():

    from extensions import db

    form = ReconEntriesForm()

    if form.str_department_inter_region.data == "RO":
        form.str_ro_code.validators = [DataRequired()]
    elif form.str_department_inter_region.data == "HO":
        form.str_department.validators = [DataRequired()]
    if form.str_ro_code.data == current_user.ro_code:
        flash("Selected RO code cannot be same as the RO code of the user.")
    elif form.validate_on_submit():
        str_period = form.str_period.data
        str_target_ro_code = (
            form.str_ro_code.data
            if form.str_department_inter_region.data == "RO"
            else None
        )
        str_department = (
            form.str_department.data
            if form.str_department_inter_region.data == "HO"
            else None
        )
        text_remarks = form.text_remarks.data
        str_dr_cr = form.str_debit_credit.data
        amount_recon = form.amount_recon.data
        #      print(str_dept)
        entry = ReconEntries(
            str_regional_office_code=current_user.ro_code,
            str_period=str_period,
            str_department=str_department or None,
            str_target_ro_code=str_target_ro_code or None,
            txt_remarks=text_remarks,
            str_debit_credit=str_dr_cr,
            str_head_office_status="Pending",
            amount_recon=amount_recon,
            created_by=current_user.username,
            date_created_date=datetime.now(),
        )
        db.session.add(entry)
        db.session.commit()
        #
        return redirect(url_for("ho_ro_recon.recon_home"))
    return render_template(
        "ho_ro_recon_add.html",
        form=form,
        edit=False,
    )


def check_for_status(recon):
    update_status = True
    if recon.str_head_office_status != "Pending":
        update_status = False
    return update_status


@ho_ro_recon_bp.route("/edit/<int:key>", methods=["POST", "GET"])
@login_required
def update_source_ro(key):
    from extensions import db

    recon = ReconEntries.query.get_or_404(key)
    if not recon.str_regional_office_code == current_user.ro_code:
        abort(404)
    form = ReconEntriesForm()
    if form.str_department_inter_region.data == "RO":
        form.str_ro_code.validators = [DataRequired()]
    elif form.str_department_inter_region.data == "HO":
        form.str_department.validators = [DataRequired()]
    if not check_for_status(recon):
        flash("Cannot edit the entry as the status is no longer pending.")
    elif form.str_ro_code.data == current_user.ro_code:
        flash("Selected RO code cannot be same as the RO code of the user.")
    elif form.validate_on_submit():
        # print(form.data)
        if form.delete_button.data:

            recon.str_head_office_status = "Deleted"
            recon.deleted_by = current_user.username
            recon.date_deleted_date = datetime.now()

        else:
            recon.str_period = form.str_period.data
            if form.str_department_inter_region.data == "HO":
                recon.str_department = form.str_department.data
                recon.str_target_ro_code = None
            elif form.str_department_inter_region.data == "RO":
                recon.str_target_ro_code = form.str_ro_code.data
                recon.str_department = None
            recon.amount_recon = form.amount_recon.data
            recon.txt_remarks = form.text_remarks.data
            recon.str_debit_credit = form.str_debit_credit.data
            recon.updated_by = current_user.username
            recon.date_updated_date = datetime.now()
        db.session.commit()
        return redirect(url_for("ho_ro_recon.recon_home"))

    form.str_period.data = recon.str_period
    if recon.str_department:
        form.str_department_inter_region.data = "HO"
        form.str_department.data = recon.str_department
    elif recon.str_target_ro_code:
        form.str_department_inter_region.data = "RO"
        form.str_ro_code.data = recon.str_target_ro_code
    form.amount_recon.data = recon.amount_recon
    form.text_remarks.data = recon.txt_remarks
    form.str_debit_credit.data = recon.str_debit_credit

    return render_template(
        "ho_ro_recon_add.html",
        form=form,
        edit=True,
        recon=recon,
        check_for_status=check_for_status,
    )


@ho_ro_recon_bp.route("/accept/<int:key>", methods=["POST", "GET"])
@login_required
def update_target_ro(key):
    recon = ReconEntries.query.get_or_404(key)
    form = RegionalOfficeAcceptForm()
    if not recon.str_target_ro_code == current_user.ro_code:
        abort(404)
    from extensions import db

    if not check_for_status(recon):
        flash("Cannot edit the entry as the status is no longer pending.")

    elif form.validate_on_submit():
        recon.str_head_office_status = form.str_accept.data
        recon.txt_head_office_remarks = f"{form.text_remarks.data}; {form.str_accept.data} by {current_user.ro_code}"
        recon.updated_by = current_user.username
        recon.date_updated_date = datetime.now()

        # create contra entry if accepted
        if form.str_accept.data == "Accepted":
            str_debit_credit = "DR" if recon.str_debit_credit == "CR" else "CR"
            recon = ReconEntries(
                str_regional_office_code=current_user.ro_code,
                str_period=recon.str_period,
                str_target_ro_code=recon.str_regional_office_code,
                str_debit_credit=str_debit_credit,
                txt_remarks=recon.txt_remarks,
                amount_recon=recon.amount_recon,
                str_head_office_status="Accepted",
                txt_head_office_remarks=f"Accepted original entry of {recon.str_regional_office_code} by {current_user.ro_code}",
                created_by=current_user.username,
                date_created_date=datetime.now(),
            )
            db.session.add(recon)
        db.session.commit()
        return redirect(url_for("ho_ro_recon.recon_home"))
    form.text_remarks.data = recon.txt_head_office_remarks
    form.str_accept.data = recon.str_head_office_status
    return render_template(
        "target_ro_accept.html",
        form=form,
        recon=recon,
        check_for_status=check_for_status,
    )


@ho_ro_recon_bp.route("/ho/<int:key>", methods=["POST", "GET"])
@login_required
def update_ho(key):
    if not current_user.user_type == "admin":
        abort(404)
    from extensions import db

    recon = ReconEntries.query.get_or_404(key)

    form = HeadOfficeAcceptForm()
    ho_staff = User.query.filter(User.user_type == "admin").order_by(User.username)
    form.str_assigned_to.choices = [
        person.username.upper() for person in ho_staff if "admin" not in person.username
    ]
    if current_user.username not in ["bar44515", "hem27596", "jan27629", "ush25768"]:
        form.str_assigned_to.choices = [current_user.username.upper()]
    #  if not check_for_status(recon):
    #     flash("Cannot edit the entry as the status is no longer pending.")
    if form.validate_on_submit():

        recon.str_assigned_to = (
            form.str_assigned_to.data
            if form.str_assigned_to.data
            else recon.str_assigned_to
        )
        recon.str_head_office_status = form.str_head_office_status.data
        recon.txt_head_office_remarks = form.text_head_office_remarks.data or None
        recon.str_head_office_voucher = form.str_head_office_voucher_number.data or None
        recon.date_head_office_voucher = form.date_head_office_voucher.data or None

        recon.updated_by = current_user.username
        recon.date_updated_date = datetime.now()
        db.session.commit()
        return redirect(url_for("ho_ro_recon.recon_home"))

    form.str_assigned_to.data = recon.str_assigned_to
    form.str_head_office_status.data = recon.str_head_office_status
    form.text_head_office_remarks.data = recon.txt_head_office_remarks
    form.str_head_office_voucher_number.data = recon.str_head_office_voucher
    form.date_head_office_voucher.data = recon.date_head_office_voucher
    return render_template(
        "ho_accept.html", recon=recon, form=form, check_for_status=check_for_status
    )


@ho_ro_recon_bp.route("/", methods=["POST", "GET"])
@login_required
def recon_home():
    query = ReconEntries.query.filter(
        ReconEntries.str_head_office_status != "Deleted"
    ).order_by(ReconEntries.id)
    if current_user.user_type == "ro_user":
        query = query.filter(
            ReconEntries.str_regional_office_code == current_user.ro_code
        )
    return render_template(
        "ho_ro_recon_home.html",
        query=query,
    )


@ho_ro_recon_bp.route("/pending", methods=["POST", "GET"])
@login_required
def recon_pending_at_ro():
    query = ReconEntries.query.filter(
        (ReconEntries.str_head_office_status != "Deleted")
        & (ReconEntries.str_head_office_status == "Pending")
    ).order_by(ReconEntries.id)
    if current_user.user_type == "ro_user":
        query = query.filter(ReconEntries.str_target_ro_code == current_user.ro_code)
    return render_template(
        "ho_ro_recon_home.html",
        query=query,
    )


@ho_ro_recon_bp.route("/summary/")
@login_required
def list_recon_summary():
    query = ReconSummary.query.filter(ReconSummary.str_period == "Jun-24").order_by(
        ReconSummary.id
    )
    if current_user.user_type == "ro_user":
        query = query.filter(
            ReconSummary.str_regional_office_code == current_user.ro_code
        )

    return render_template("ho_ro_recon_summary_list.html", query=query)


def calculate_amount(ro_code):
    query = (
        ReconEntries.query.with_entities(func.sum(ReconEntries.amount_recon))
        .filter(ReconEntries.str_regional_office_code == ro_code)
        .group_by(ReconEntries.str_head_office_status)
    )

    pending_amount = query.filter(ReconEntries.str_head_office_status == "Pending")
    pending_amount_dr = pending_amount.filter(
        ReconEntries.str_debit_credit == "DR"
    ).first() or [0]
    pending_amount_cr = pending_amount.filter(
        ReconEntries.str_debit_credit == "CR"
    ).first() or [0]
    # print(pending_amount_dr[0], pending_amount_cr[0])
    not_passed = query.filter(
        (ReconEntries.str_head_office_status == "Accepted")
        & (ReconEntries.str_head_office_voucher.is_(None))
    )
    #    print(not_passed.all())
    not_passed_dr = not_passed.filter(
        ReconEntries.str_debit_credit == "DR"
    ).first() or [0]
    not_passed_cr = not_passed.filter(
        ReconEntries.str_debit_credit == "CR"
    ).first() or [0]
    #   print(not_passed_dr.all(), not_passed_cr.all())
    return (
        pending_amount_dr[0]
        - pending_amount_cr[0]
        + not_passed_dr[0]
        - not_passed_cr[0]
    )


@ho_ro_recon_bp.route("/summary/edit/<int:id>", methods=["POST", "GET"])
@login_required
def update_recon_summary(id):
    from extensions import db

    summary = ReconSummary.query.get_or_404(id)
    if current_user.user_type == "ro_user":
        if current_user.ro_code != summary.str_regional_office_code:
            abort(404)

    recon_entries = ReconEntries.query.filter(
        ReconEntries.str_regional_office_code == summary.str_regional_office_code
    ).order_by(ReconEntries.id)
    pending_entries = recon_entries.filter(
        ReconEntries.str_head_office_status == "Pending"
    )
    pending_entries_debit = pending_entries.filter(
        ReconEntries.str_debit_credit == "DR"
    )
    pending_entries_credit = pending_entries.filter(
        ReconEntries.str_debit_credit == "CR"
    )
    accepted_but_not_passed_entries = recon_entries.filter(
        (ReconEntries.str_head_office_status == "Accepted")
        & (ReconEntries.str_head_office_voucher.is_(None))
    )
    accepted_but_not_passed_entries_dr = accepted_but_not_passed_entries.filter(
        ReconEntries.str_debit_credit == "DR"
    )
    accepted_but_not_passed_entries_cr = accepted_but_not_passed_entries.filter(
        ReconEntries.str_debit_credit == "CR"
    )
    form = ReconSummaryForm()

    if (
        not fabs(
            int_diff := (
                (form.float_ro_balance.data or 0)
                - calculate_amount(summary.str_regional_office_code)
            )
            - (form.float_ho_balance.data or 0)
        )
        > 0.05
    ):
        flash(f"Amount mismatch {int_diff}.")
    elif form.validate_on_submit():
        summary.input_ro_balance_dr_cr = form.str_ro_balance_dr_cr.data
        summary.input_float_ro_balance = form.float_ro_balance.data
        summary.input_ho_balance_dr_cr = form.str_ho_balance_dr_cr.data
        summary.input_float_ho_balance = form.float_ho_balance.data
        summary.updated_by = current_user.username
        summary.date_updated_date = datetime.now()

        # summary.float_ho_balance =
        db.session.commit()
        return redirect(url_for("ho_ro_recon.list_recon_summary"))

    form.str_ro_balance_dr_cr.data = summary.input_ro_balance_dr_cr
    form.float_ro_balance.data = summary.input_float_ro_balance or 0
    form.str_ho_balance_dr_cr.data = summary.input_ho_balance_dr_cr
    form.float_ho_balance.data = summary.input_float_ho_balance or 0

    return render_template(
        "recon_summary_edit.html",
        form=form,
        summary=summary,
        pending_dr=pending_entries_debit,
        pending_cr=pending_entries_credit,
        not_passed_dr=accepted_but_not_passed_entries_dr,
        not_passed_cr=accepted_but_not_passed_entries_cr,
    )


@ho_ro_recon_bp.route("/upload_summary_template", methods=["GET", "POST"])
@login_required
def upload_summary_template():

    form = UploadFileForm()

    if form.validate_on_submit():
        summary_template = form.data["file_upload"]
        df_summary_template = pd.read_excel(
            summary_template,
            dtype={
                "str_period": str,
                "str_regional_office_code": str,
            },
        )
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        df_summary_template["date_created_date"] = datetime.now()
        df_summary_template["created_by"] = current_user.username

        df_summary_template.to_sql(
            "recon_summary",
            engine,
            if_exists="append",
            index=False,
        )
        flash("HO RO recon summary has been uploaded successfully.")
    return render_template(
        "ho_ro_upload_file_template.html",
        form=form,
        title="Upload HO RO recon summary",
    )


# # @ho_ro_recon_bp.route("/pending_count", methods=["POST", "GET"])
# # @login_required
# def count_recon_pending_at_ro():
#     count = (
#         ReconEntries.query.with_entities(
#             func.count(ReconEntries.str_target_ro_code)
#         ).filter(
#             (ReconEntries.str_head_office_status != "Deleted")
#             & (ReconEntries.str_head_office_status == "Pending")
#         )
#         # .order_by(ReconEntries.id)
#     )
#     if current_user.user_type == "ro_user":
#         count = count.filter(
#             ReconEntries.str_target_ro_code == current_user.ro_code
#         ).group_by(ReconEntries.str_target_ro_code)
#     #    print(query)
#     print(count[0][0])
#     # print(f"{count[0][0]}")
#     return f"{count[0][0]}"
#     # dict_count = {'count':count[0][0]}
#     # return dict_count
