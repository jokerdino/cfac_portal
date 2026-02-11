from datetime import datetime
from io import BytesIO

import pandas as pd
from flask import flash, redirect, render_template, url_for, request, send_file
from flask_login import login_required, current_user


from extensions import db
from set_view_permissions import admin_required

from . import direct_debits_bp
from .model import DirectDebit, Status

from .form import (
    RegionalOfficeForm,
    BulkDirectDebitForm,
    JournalVoucherUpdateForm,
    JournalVoucerRemarksForm,
    MonthFilterForm,
    HeadOfficeForm,
)

VIEW_ALL = "View all"


@direct_debits_bp.route("/upload", methods=["GET", "POST"])
@login_required
@admin_required
def direct_debit_bulk_upload():
    form = BulkDirectDebitForm()
    if form.validate_on_submit():
        dd_file = form.file_upload.data

        df = pd.read_excel(dd_file, dtype={"ro_code": str})
        df.columns = df.columns.str.lower().str.replace(" ", "_")
        df["ro_code"] = df["ro_code"].astype(str).str.zfill(6)
        df["status"] = Status.DEBITED

        db.session.execute(db.insert(DirectDebit), df.to_dict(orient="records"))

        db.session.commit()
        flash(f"Successfully uploaded {len(df)} direct debits.", "success")

        return redirect(url_for(".direct_debit_bulk_upload"))

    return render_template(
        "direct_debit_form.html", title="Upload DD debits", form=form
    )


@direct_debits_bp.route("/", methods=["GET", "POST"])
@login_required
def direct_debit_list():
    filter_form = MonthFilterForm()
    query = db.select(DirectDebit)
    if current_user.user_type in ["ro_motor_tp", "ro_user"]:
        query = query.where(DirectDebit.ro_code == current_user.ro_code)

    populate_month(query, filter_form)

    if filter_form.validate_on_submit():
        month = filter_form.month.data
        if month != VIEW_ALL:
            query = query.where(DirectDebit.month_string == month)
    direct_debits = db.session.scalars(query)

    required_columns = [
        "ro_code",
        "ro_name",
        "transaction_date",
        "particulars",
        "debit",
        "status",
        "dd_reversal_date",
        "ho_iot_jv_number",
        "ho_iot_jv_date",
        "ro_jv_number",
        "ro_jv_date",
        "remarks",
    ]

    return render_template(
        "direct_debit_list.html",
        direct_debits=direct_debits,
        required_columns=required_columns,
        filter_form=filter_form,
    )


@direct_debits_bp.route("/edit/<int:dd_id>/", methods=["POST", "GET"])
@login_required
def direct_debit_edit(dd_id):
    dd = db.get_or_404(DirectDebit, dd_id)
    dd.require_access(current_user)

    if current_user.user_type == "admin":
        form = HeadOfficeForm(obj=dd)
        form.status.choices = [(e, e.value) for e in Status]
    else:
        form = RegionalOfficeForm(obj=dd)

    if form.validate_on_submit():
        form.populate_obj(dd)
        db.session.commit()
        return redirect(url_for(".direct_debit_view", dd_id=dd.id))
    return render_template(
        "direct_debit_edit.html", form=form, title="Edit DD debit", dd=dd
    )


@direct_debits_bp.get("/view/<int:dd_id>")
@login_required
def direct_debit_view(dd_id):
    dd = db.get_or_404(DirectDebit, dd_id)
    dd.require_access(current_user)
    return render_template("direct_debit_view.html", dd=dd)


@direct_debits_bp.route("/jv_pending", methods=["POST", "GET"])
@login_required
@admin_required
def direct_debit_jv_pending():
    filter_form = MonthFilterForm()

    form = JournalVoucherUpdateForm()
    query = db.select(DirectDebit).where(DirectDebit.bool_jv_passed.is_(False))
    populate_month(query, filter_form)

    if filter_form.validate_on_submit():
        month = filter_form.month.data
        if month != VIEW_ALL:
            query = query.where(DirectDebit.month_string == month)

    show_checkbox = True if current_user.user_type in ["admin"] else False
    direct_debits = db.session.scalars(query)

    required_columns = [
        "ro_code",
        "ro_name",
        "transaction_date",
        "particulars",
        "debit",
        "status",
        "dd_reversal_date",
        "ho_iot_jv_number",
        "ho_iot_jv_date",
        "ro_jv_number",
        "ro_jv_date",
        "remarks",
    ]

    return render_template(
        "direct_debit_list.html",
        direct_debits=direct_debits,
        required_columns=required_columns,
        show_checkbox=show_checkbox,
        form=form,
        filter_form=filter_form,
    )


@direct_debits_bp.post("/mark_as_jv_passed/")
@login_required
@admin_required
def mark_jv_passed():
    form = JournalVoucherUpdateForm()

    selected_ids = request.form.getlist("selected_ids")
    selected_ids = [int(id) for id in selected_ids]

    if not selected_ids:
        flash("No rows selected", "warning")
        return redirect(url_for(".direct_debit_jv_pending"))

    if not form.validate_on_submit():
        flash("Please enter valid JV details", "danger")
        return redirect(url_for(".direct_debit_jv_pending"))

    stmt = (
        db.update(DirectDebit)
        .where(DirectDebit.id.in_(selected_ids))
        .values(
            {
                DirectDebit.bool_jv_passed: True,
                DirectDebit.ho_iot_jv_number: form.ho_iot_jv_number.data,
                DirectDebit.ho_iot_jv_date: form.ho_iot_jv_date.data,
                DirectDebit.jv_passed_as_on: datetime.now(),
            }
        )
    )

    db.session.execute(stmt)
    db.session.commit()

    flash(f"{len(selected_ids)} rows marked as JV passed", "success")
    return redirect(url_for(".direct_debit_jv_pending"))


@direct_debits_bp.route("/download_jv/", methods=["POST", "GET"])
@login_required
@admin_required
def direct_debit_download_jv():
    form = JournalVoucerRemarksForm()
    if form.validate_on_submit():
        remarks = form.remarks.data
        credit_query = db.select(
            db.literal("000100").label("Office Location"),
            db.literal("9111330100").label("GL Code"),
            db.literal("12111003").label("SL Code"),
            db.literal("CR").label("DR/CR"),
            db.func.sum(DirectDebit.debit).label("Amount"),
            db.literal(remarks).label("Remarks"),
        ).where(DirectDebit.bool_jv_passed.is_(False))

        debit_query = db.select(
            db.literal("000100").label("Office Location"),
            db.literal("5121901000").label("GL Code"),
            db.func.concat("9", DirectDebit.ro_code).label("SL Code"),
            db.literal("DR").label("DR/CR"),
            DirectDebit.debit.label("Amount"),
            db.literal(remarks).label("Remarks"),
        ).where(DirectDebit.bool_jv_passed.is_(False))

        union_query = db.union_all(credit_query, debit_query)
        with db.engine.connect() as conn:
            df = pd.read_sql(union_query, conn)
        output = BytesIO()
        df.to_excel(output, index=False)

        output.seek(0)
        filename = f"dd_debits_jv_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return send_file(output, as_attachment=True, download_name=filename)

    return render_template("direct_debit_form.html", form=form, title="Download JV")


def populate_month(stmt, form, view_all=True):
    subq = stmt.subquery()

    rows = db.session.execute(
        db.select(
            db.distinct(subq.c.month).label("month"),
            subq.c.month_string.label("month_string"),
        ).order_by(subq.c.month)
    ).all()

    month_choices = [r.month_string for r in rows]

    if view_all:
        form.month.choices = [VIEW_ALL] + month_choices
    else:
        form.month.choices = month_choices
