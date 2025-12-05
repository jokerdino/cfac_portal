import pandas as pd
from flask import redirect, render_template, url_for, flash, request
from flask_login import login_required, current_user
from markupsafe import Markup

from . import refund_dqr_bp
from .models import DqrRefund, DqrMachines
from .forms import UploadFileForm, DQRMachineEditForm, DQRRefundEditForm
from set_view_permissions import admin_required, oo_user_only
from extensions import db

from app.main.table_helper import Table, Column


@refund_dqr_bp.route("/add", methods=["GET", "POST"])
@login_required
@oo_user_only
def dqr_refund_add():
    user_type = current_user.user_type

    if user_type == "oo_user":
        dqr = db.session.scalar(
            db.select(DqrMachines).where(
                DqrMachines.office_code == current_user.oo_code
            )
        )

        form = DQRRefundEditForm(obj=dqr)
        form.ro_code.choices = [current_user.ro_code]
        form.office_code.choices = [current_user.oo_code]
        form.ro_code.data = current_user.ro_code
        form.office_code.data = current_user.oo_code
    elif user_type == "ro_user":
        office_list = db.session.scalars(
            db.select(DqrMachines.office_code)
            .where(DqrMachines.ro_code == current_user.ro_code)
            .order_by(DqrMachines.office_code)
        ).all()

        form = DQRRefundEditForm()

        form.ro_code.choices = [current_user.ro_code]
        form.office_code.choices = office_list
        form.ro_code.data = current_user.ro_code

    elif user_type == "admin":
        ro_list = db.session.scalars(
            db.select(
                db.func.distinct(DqrMachines.ro_code).label("ro_code"),
            ).order_by(DqrMachines.ro_code)
        ).all()

        form = DQRRefundEditForm()
        form.ro_code.choices = ro_list
        if request.method == "POST":
            ro_code = request.form.get("ro_code")
            office_list = db.session.scalars(
                db.select(DqrMachines.office_code)
                .where(DqrMachines.ro_code == ro_code)
                .order_by(DqrMachines.office_code)
            ).all()
            form.office_code.choices = office_list

    if form.validate_on_submit():
        dqr_refund = DqrRefund()

        form.populate_obj(dqr_refund)

        db.session.add(dqr_refund)
        db.session.commit()
        return redirect(url_for(".dqr_refund_view", id=dqr_refund.id))

    return render_template(
        "refund_dqr_form_edit.html", form=form, title="Add DQR refund", fetch=True
    )


@refund_dqr_bp.route("/edit/<int:id>/", methods=["GET", "POST"])
@login_required
@oo_user_only
def dqr_refund_edit(id):
    dqr_refund = db.get_or_404(DqrRefund, id)
    dqr_refund.require_access(current_user)
    form = DQRRefundEditForm(obj=dqr_refund)
    form.ro_code.choices = [dqr_refund.ro_code]
    form.office_code.choices = [dqr_refund.office_code]
    form.ro_code.data = dqr_refund.ro_code
    form.office_code.data = dqr_refund.office_code
    if form.validate_on_submit():
        form.populate_obj(dqr_refund)
        db.session.commit()
        return redirect(url_for(".dqr_refund_view", id=dqr_refund.id))
    return render_template(
        "refund_dqr_form_edit.html", form=form, title="Edit DQR refund"
    )


@refund_dqr_bp.route("/view/<int:id>/", methods=["GET", "POST"])
@login_required
@oo_user_only
def dqr_refund_view(id):
    dqr_refund = db.get_or_404(DqrRefund, id)
    dqr_refund.require_access(current_user)

    return render_template(
        "dqr_refund_view.html", refund=dqr_refund, title="View DQR refund"
    )


@refund_dqr_bp.route("/", methods=["GET"])
@login_required
@oo_user_only
def dqr_refund_list():
    role = current_user.user_type

    query = db.select(DqrRefund).order_by(DqrRefund.id)
    pending = db.select(DqrRefund).where(DqrRefund.refund_status == "Refund pending")
    completed = db.select(DqrRefund).where(
        DqrRefund.refund_status == "Refund completed"
    )
    if role == "ro_user":
        ro_filter = DqrRefund.ro_code == current_user.ro_code
        query = query.where(ro_filter)
        pending = pending.where(ro_filter)
        completed = completed.where(ro_filter)

    elif role == "oo_user":
        oo_filter = DqrRefund.office_code == current_user.oo_code
        query = query.where(oo_filter)
        pending = pending.where(oo_filter)
        completed = completed.where(oo_filter)

    column_names = [
        "organisation",
        "ro_code",
        "office_code",
        "device_serial_number",
        "refund_amount",
        "txn_date",
        "txn_currency",
        "refund_currency",
        "auth_code",
        "mid",
        "tid",
        "txn_amt",
        "rrn",
        "account_number",
        "reason_for_refund",
        "date_of_email_sent_to_bank",
        "refund_ref_no",
        "refund_date",
        "ro_remarks",
        "refund_status",
    ]
    all_table = Table(
        query,
        classes="table table-striped table-bordered",
        id="dqr_refund_table",
        paginate=False,
        only=column_names,
        extra_columns=[
            (
                "view",
                Column(
                    "View",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.dqr_refund_view', id=u.id)}'>View</a>"
                    ),
                    is_html=True,
                ),
            ),
            (
                "edit",
                Column(
                    "Edit",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.dqr_refund_edit', id=u.id)}'>Edit</a>"
                    ),
                    is_html=True,
                ),
            ),
        ],
    )

    pending_table = Table(
        pending,
        classes="table table-striped table-bordered",
        id="dqr_pending_refund_table",
        paginate=False,
        only=column_names,
        extra_columns=[
            (
                "view",
                Column(
                    "View",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.dqr_refund_view', id=u.id)}'>View</a>"
                    ),
                    is_html=True,
                ),
            ),
            (
                "edit",
                Column(
                    "Edit",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.dqr_refund_edit', id=u.id)}'>Edit</a>"
                    ),
                    is_html=True,
                ),
            ),
        ],
    )
    completed_table = Table(
        completed,
        classes="table table-striped table-bordered",
        id="dqr_completed_table",
        paginate=False,
        only=column_names,
        extra_columns=[
            (
                "view",
                Column(
                    "View",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.dqr_refund_view', id=u.id)}'>View</a>"
                    ),
                    is_html=True,
                ),
            ),
            (
                "edit",
                Column(
                    "Edit",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.dqr_refund_edit', id=u.id)}'>Edit</a>"
                    ),
                    is_html=True,
                ),
            ),
        ],
    )

    return render_template(
        "dqr_refund_list.html",
        all_table=all_table,
        pending_table=pending_table,
        completed_table=completed_table,
        title="All DQR refunds",
        pending_title="Pending DQR refunds",
        completed_title="Completed DQR refunds",
    )


@refund_dqr_bp.get("/fetch-oo-code")
@login_required
def fetch_oo_code():
    ro_code = request.args.get("ro_code")

    office_code_choices = db.session.scalars(
        db.select(DqrMachines.office_code).where(DqrMachines.ro_code == ro_code)
    ).all()
    data = [{"value": oo_code, "label": oo_code} for oo_code in office_code_choices]

    return data


@refund_dqr_bp.get("/fetch-machine-details")
@login_required
def fetch_machine_details():
    office_code = request.args.get("office_code")

    machine_details = (
        db.session.execute(
            db.select(
                DqrMachines.device_serial_number, DqrMachines.mid, DqrMachines.tid
            ).where(DqrMachines.office_code == office_code)
        )
        .mappings()
        .first()
    )

    return dict(machine_details)


@refund_dqr_bp.route("/dqr_machines/add", methods=["GET", "POST"])
@login_required
@admin_required
def dqr_machines_add():
    dqr_machine = DqrMachines()

    if request.method == "POST":
        form = DQRMachineEditForm(request.form, obj=dqr_machine)
        if form.validate():
            form.populate_obj(dqr_machine)

            db.session.add(dqr_machine)
            db.session.commit()

            return redirect(url_for(".dqr_machine_list"))
    else:
        form = DQRMachineEditForm()
    return render_template(
        "refund_dqr_form_edit.html", title="Add DQR machine", form=form
    )


@refund_dqr_bp.route("/dqr_machines/edit/<int:id>/", methods=["GET", "POST"])
@login_required
@admin_required
def dqr_machines_edit(id):
    dqr_machine = db.get_or_404(DqrMachines, id)

    if request.method == "POST":
        form = DQRMachineEditForm(request.form, obj=dqr_machine)
        if form.validate():
            form.populate_obj(dqr_machine)

            db.session.add(dqr_machine)
            db.session.commit()

            return redirect(url_for(".dqr_machine_list"))
    else:
        form = DQRMachineEditForm(obj=dqr_machine)
    return render_template(
        "refund_dqr_form_edit.html", title="Add DQR machine", form=form
    )


@refund_dqr_bp.route("/dqr_machines/", methods=["GET"])
@login_required
@admin_required
def dqr_machines_list():
    table = Table(
        DqrMachines,
        classes="table table-striped table-bordered",
        id="dqr_refund_table",
        paginate=False,
        only=[
            "ro_code",
            "merchant_name",
            "merchant_dba_name",
            "mid",
            "tid",
            "mcc_code",
            "office_code",
            "address",
            "city",
            "pincode",
            "state",
            "name",
            "login",
            "user_id",
            "password",
            "device_name",
            "status",
            "device_serial_number",
            "installation_date",
        ],
        extra_columns=[
            (
                "edit",
                Column(
                    "Edit",
                    formatter=lambda u: Markup(
                        f"<a href='{url_for('.dqr_machines_edit', id=u.id)}'>Edit</a>"
                    ),
                    is_html=True,
                ),
            ),
        ],
    )

    return render_template("dqr_refund_list.html", table=table, title="DQR machines")


@refund_dqr_bp.route("/dqr_machines/upload", methods=["GET", "POST"])
@login_required
@admin_required
def dqr_machines_bulk_upload():
    form = UploadFileForm()

    if form.validate_on_submit():
        df = pd.read_excel(form.data["file"])
        df.columns = df.columns.str.lower().str.strip().str.replace(" ", "_")

        df = df.drop("sl_no", axis=1)

        df["ro_code"] = (df["ro_code"] * 10000).astype(str).str.zfill(6)
        df["office_code"] = df["office_code"].astype(str).str.zfill(6)

        string_columns = ["mcc_code", "office_code", "login", "device_serial_number"]
        for col in string_columns:
            df[col] = df[col].astype(str)

        df["installation_date"] = pd.to_datetime(
            df["installation_date"], errors="coerce"
        )
        df["installation_date"] = df[
            "installation_date"
        ].dt.date  # convert to Python date
        df = df.where(pd.notnull(df), None)
        db.session.execute(db.insert(DqrMachines), df.to_dict(orient="records"))
        db.session.commit()

        flash("DQR machines details have been uploaded successfully.")
    return render_template(
        "refund_dqr_form_edit.html", form=form, title="Bulk upload DQR machines data"
    )
