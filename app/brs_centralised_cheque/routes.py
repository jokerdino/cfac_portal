from dataclasses import asdict
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from math import fabs

from flask import flash, redirect, render_template, send_file, url_for
import pandas as pd
import sqlalchemy
from sqlalchemy import func
from flask_login import current_user, login_required
from flask_weasyprint import HTML, render_pdf

from . import brs_cc_bp

from .forms import (
    CentralisedChequeBankReconForm,
    CentralisedChequeDashboardForm,
    EnableDeleteMonthForm,
    DeleteMonthForm,
    BulkUploadCentralisedChequeSummary,
)

from .models import (
    CentralisedChequeSummary,
    CentralisedChequeDetails,
    CentralisedChequeInstrumentStaleDetails,
    CentralisedChequeInstrumentUnencashedDetails,
    CentralisedChequeEnableDelete,
)

from set_view_permissions import admin_required, ro_user_only
from utils import datetime_format

from extensions import db


@brs_cc_bp.route("/summary/upload/", methods=["GET", "POST"])
@login_required
@admin_required
def upload_brs_cc_summary():
    form = BulkUploadCentralisedChequeSummary()
    if form.validate_on_submit():
        file = form.data["file_upload"]
        df_brs_cc_summary = pd.read_excel(
            file,
            dtype={
                "regional_office_code": str,
                "operating_office_code": str,
            },
        )

        df_brs_cc_summary["created_on"] = datetime.now()
        df_brs_cc_summary["created_by"] = current_user.username

        df_brs_cc_summary.to_sql(
            "centralised_cheque_summary",
            db.engine,
            if_exists="append",
            index=False,
        )
        flash("BRS Centralised cheque details have been uploaded successfully.")
    return render_template(
        "brs_cc_upload_file_template.html",
        form=form,
        title="Upload BRS Centralised cheque details",
    )


@brs_cc_bp.route("/dashboard/", methods=["GET", "POST"])
@login_required
@ro_user_only
def brs_cc_dashboard():
    form = CentralisedChequeDashboardForm()

    month_choices = db.session.scalars(
        db.select(
            CentralisedChequeSummary.month, CentralisedChequeSummary.date_of_month
        )
        .distinct()
        .order_by(CentralisedChequeSummary.date_of_month.desc())
    )

    form.month.choices = ["View all"] + [month for month in month_choices]
    query = (
        db.select(
            CentralisedChequeSummary.regional_office_code,
            CentralisedChequeSummary.month,
            func.count(CentralisedChequeSummary.centralised_cheque_bank),
            func.count(CentralisedChequeSummary.centralised_cheque_brs_id),
            CentralisedChequeSummary.date_of_month,
        )
        .group_by(
            CentralisedChequeSummary.regional_office_code,
            CentralisedChequeSummary.month,
            CentralisedChequeSummary.date_of_month,
        )
        .order_by(CentralisedChequeSummary.date_of_month.desc())
    )

    if current_user.user_type == "ro_user":
        query = query.where(
            CentralisedChequeSummary.regional_office_code == current_user.ro_code
        )
    if form.validate_on_submit():
        month = form.month.data
        if month != "View all":
            query = query.where(CentralisedChequeSummary.month == month)
    result = db.session.execute(query)
    return render_template("brs_cc_dashboard.html", query=result, form=form)


@brs_cc_bp.route("/<string:month>/<string:ro_code>/")
@login_required
@ro_user_only
def brs_cc_homepage(month, ro_code):
    if current_user.user_type == "ro_user":
        ro_code = current_user.ro_code
    query = db.session.scalars(
        db.select(CentralisedChequeSummary)
        .where(
            CentralisedChequeSummary.regional_office_code == ro_code,
            CentralisedChequeSummary.month == month,
        )
        .order_by(CentralisedChequeSummary.operating_office_code)
    )
    return render_template("brs_cc_homepage.html", query=query)


@brs_cc_bp.route("/<int:key>/", methods=["GET", "POST"])
@login_required
@ro_user_only
def brs_cc_view_status(key):
    brs = db.get_or_404(CentralisedChequeSummary, key)

    delete_button: bool = db.session.scalars(
        db.select(CentralisedChequeEnableDelete.enable_delete).where(
            CentralisedChequeEnableDelete.date_of_month == brs.date_of_month
        )
    ).first()

    form = DeleteMonthForm()
    if form.validate_on_submit():
        brs.centralised_cheque_brs_id = None
        for detail in brs.details:
            detail.brs_status = "Deleted"
        db.session.commit()
        flash("BRS entry has been deleted.")
        return redirect(url_for(".brs_cc_view_status", key=key))

    return render_template(
        "brs_cc_view_status.html",
        brs=brs,
        form=form,
        delete_button=delete_button,
    )


def get_prev_month_closing_balance(brs_id):
    brs_summary = db.get_or_404(CentralisedChequeSummary, brs_id)

    previous_month = brs_summary.date_of_month.replace(day=1) - timedelta(days=1)

    previous_month_brs = db.session.scalars(
        db.select(CentralisedChequeDetails)
        .where(
            CentralisedChequeDetails.summary_id == CentralisedChequeSummary.id,
            CentralisedChequeSummary.operating_office_code
            == brs_summary.operating_office_code,
            CentralisedChequeSummary.date_of_month == previous_month,
        )
        .order_by(CentralisedChequeDetails.id.desc())
    ).first()
    if previous_month_brs:
        return (
            previous_month_brs.closing_balance_unencashed,
            previous_month_brs.closing_balance_stale,
        )
    else:
        return 0, 0


@brs_cc_bp.route("/<int:key>/add/", methods=["POST", "GET"])
@login_required
@ro_user_only
def brs_cc_data_entry(key):
    brs = db.get_or_404(CentralisedChequeSummary, key)
    form = CentralisedChequeBankReconForm(obj=brs)

    if form.validate_on_submit():
        brs_entry = CentralisedChequeDetails()
        form.populate_obj(brs_entry)
        brs_entry.summary_id = brs.id
        db.session.add(brs_entry)
        db.session.commit()
        brs.centralised_cheque_brs_id = brs_entry.id
        db.session.commit()
        required_columns = [
            "voucher_number",
            "voucher_date",
            "transaction_id",
            "instrument_number",
            "instrument_date",
            "instrument_amount",
            "payee_name",
            "remarks",
        ]
        # upload unencashed entries
        if form.data["unencashed_cheques_file"]:
            df_unencashed = pd.read_excel(
                form.data["unencashed_cheques_file"],
                usecols=required_columns,
            )
            df_unencashed["centralised_cheque_details_id"] = brs_entry.id
            df_unencashed.to_sql(
                "centralised_cheque_instrument_unencashed_details",
                db.engine,
                if_exists="append",
                index=False,
            )
        # upload stale entries
        if form.data["stale_cheques_file"]:
            df_stale = pd.read_excel(
                form.data["stale_cheques_file"],
                usecols=required_columns,
            )
            df_stale["centralised_cheque_details_id"] = brs_entry.id
            df_stale.to_sql(
                "centralised_cheque_instrument_stale_details",
                db.engine,
                if_exists="append",
                index=False,
            )
        return redirect(url_for(".brs_cc_view_status", key=brs.id))

    unencashed, stale = get_prev_month_closing_balance(brs.id)
    form.opening_balance_stale.data = stale
    form.opening_balance_unencashed.data = unencashed
    return render_template("brs_cc_data_entry.html", brs=brs, form=form)


@brs_cc_bp.route("/view/<int:key>/", methods=["POST", "GET"])
@login_required
@ro_user_only
def brs_cc_view_entry(key):
    brs = db.get_or_404(CentralisedChequeDetails, key)
    column_labels = {
        "opening_balance_unencashed": (
            "Opening balance: Unencashed cheques",
            datetime_format(brs.summary.month, "%B-%Y", "previous"),
        ),
        "cheques_issued": ("Add: Cheques issued", brs.summary.month),
        "cheques_reissued_unencashed": ("Add: Cheques reissued", brs.summary.month),
        "opening_balance_stale": (
            "Opening balance: Stale cheques",
            datetime_format(brs.summary.month, "%B-%Y", "previous"),
        ),
        "cheques_reissued_stale": ("Less: Cheques reissued", brs.summary.month),
        "cheques_cleared": ("Less: Cheques cleared", brs.summary.month),
        "cheques_cancelled": ("Less: Cheques cancelled", brs.summary.month),
        "closing_balance_unencashed": (
            "Closing balance: Unencashed cheques",
            datetime_format(brs.summary.month, "%B-%Y", "current"),
        ),
        "closing_balance_stale": (
            "Closing balance: Stale cheques",
            datetime_format(brs.summary.month, "%B-%Y", "current"),
        ),
    }
    return render_template(
        "brs_cc_view_entry.html",
        brs=brs,
        column_labels=column_labels,
    )


@brs_cc_bp.route("/upload_previous_month/")
def brs_auto_upload_prev_month():
    """
    View function to upload fresh BRS entries from previous month's entries.
    Also adds the month to DeleteEntry table.

    URL will be fetched using cron at the start of new month.
    current_month will be the month that just ended.
    New entries will be fetched from the previous month data.

    Returns:
        string: "Success" is returned as response
    """

    # current_month refers to month that just ended
    current_month = date.today().replace(day=1) - timedelta(days=1)

    # prev_month is the month before current_month
    prev_month = current_month.replace(day=1) - timedelta(days=1)

    fresh_entries = []
    brs_entries = db.session.scalars(
        db.select(CentralisedChequeSummary).where(
            CentralisedChequeSummary.date_of_month == prev_month
        )
    )
    for entry in brs_entries:
        new_entry = CentralisedChequeSummary(
            **asdict(entry),
            date_of_month=current_month,
            created_by="AUTOUPLOAD",
        )

        fresh_entries.append(new_entry)

    db.session.add_all(fresh_entries)

    delete_month_entry = CentralisedChequeEnableDelete(
        date_of_month=current_month, created_by="AUTOUPLOAD"
    )
    db.session.add(delete_month_entry)
    db.session.commit()

    return "Success"


@brs_cc_bp.route("/download_format/")
@login_required
@ro_user_only
def download_format():
    return send_file("download_formats/brs_cc_cheques_upload_format.xlsx")


@brs_cc_bp.route("/list_brs_data/", methods=["POST", "GET"])
@login_required
@ro_user_only
def list_brs_data():
    form = CentralisedChequeDashboardForm()
    month_choices = db.session.scalars(
        db.select(
            CentralisedChequeSummary.month, CentralisedChequeSummary.date_of_month
        )
        .distinct()
        .order_by(CentralisedChequeSummary.date_of_month.desc())
    )

    form.month.choices = [month for month in month_choices]
    if form.validate_on_submit():
        month = form.month.data
        query = (
            db.select(CentralisedChequeDetails)
            .join(CentralisedChequeSummary)
            .where(
                (CentralisedChequeSummary.month == month)
                & (CentralisedChequeDetails.brs_status.is_(None))
            )
            .order_by(
                CentralisedChequeSummary.regional_office_code,
                CentralisedChequeSummary.operating_office_code,
            )
        )

        if current_user.user_type == "ro_user":
            query = query.where(
                CentralisedChequeSummary.regional_office_code == current_user.ro_code
            )
        result = db.session.scalars(query)
        return render_template("brs_list_summary.html", result=result)
    return render_template("brs_summary_form.html", form=form)


@brs_cc_bp.route("/list_unencashed_entries/", methods=["POST", "GET"])
@login_required
@ro_user_only
def list_unencashed_entries():
    form = CentralisedChequeDashboardForm()
    month_choices = db.session.scalars(
        db.select(
            CentralisedChequeSummary.month, CentralisedChequeSummary.date_of_month
        )
        .distinct()
        .order_by(CentralisedChequeSummary.date_of_month.desc())
    )
    form.month.choices = [month for month in month_choices]

    if form.validate_on_submit():
        month = form.month.data
        query = (
            db.select(CentralisedChequeInstrumentUnencashedDetails)
            .join(CentralisedChequeDetails)
            .join(CentralisedChequeSummary)
            .where(
                (CentralisedChequeSummary.month == month)
                & (CentralisedChequeDetails.brs_status.is_(None))
            )
            .order_by(
                CentralisedChequeSummary.regional_office_code,
                CentralisedChequeSummary.operating_office_code,
            )
        )

        if current_user.user_type == "ro_user":
            query = query.where(
                CentralisedChequeSummary.regional_office_code == current_user.ro_code
            )
        result = db.session.scalars(query)
        return render_template("brs_list_unencashed.html", result=result)
    return render_template("brs_summary_form.html", form=form)


@brs_cc_bp.route("/list_stale_entries/", methods=["POST", "GET"])
@login_required
@ro_user_only
def list_stale_entries():
    form = CentralisedChequeDashboardForm()
    month_choices = db.session.scalars(
        db.select(
            CentralisedChequeSummary.month, CentralisedChequeSummary.date_of_month
        )
        .distinct()
        .order_by(CentralisedChequeSummary.date_of_month.desc())
    )
    form.month.choices = [month for month in month_choices]

    if form.validate_on_submit():
        month = form.month.data
        query = (
            db.select(CentralisedChequeInstrumentStaleDetails)
            .join(CentralisedChequeDetails)
            .join(CentralisedChequeSummary)
            .where(
                (CentralisedChequeSummary.month == month)
                & (CentralisedChequeDetails.brs_status.is_(None))
            )
            .order_by(
                CentralisedChequeSummary.regional_office_code,
                CentralisedChequeSummary.operating_office_code,
            )
        )

        if current_user.user_type == "ro_user":
            query = query.where(
                CentralisedChequeSummary.regional_office_code == current_user.ro_code
            )
        result = db.session.scalars(query)
        return render_template("brs_list_stale.html", result=result)
    return render_template("brs_summary_form.html", form=form)


@brs_cc_bp.route(
    "/api/v1/view_brs_cc/<string:office_code>/<string:month>/", methods=["POST", "GET"]
)
def view_brs_cc_api(office_code, month):
    response = {"office_code": office_code, "month": month}
    brs = db.session.scalars(
        db.select(CentralisedChequeDetails)
        .join(CentralisedChequeSummary)
        .outerjoin(CentralisedChequeInstrumentUnencashedDetails)
        .outerjoin(CentralisedChequeInstrumentStaleDetails)
        .where(
            (CentralisedChequeDetails.brs_status.is_(None))
            & (CentralisedChequeSummary.month == month)
            & (CentralisedChequeSummary.operating_office_code == office_code)
        )
    ).first()

    if brs:
        response["summary"] = asdict(brs.summary)
        response["brs"] = asdict(brs)
        if brs.unencashed_cheques:
            response["brs"]["unencashed_cheques"] = [
                asdict(unencashed_cheque)
                for unencashed_cheque in brs.unencashed_cheques
            ]
        if brs.stale_cheques:
            response["brs"]["stale_cheques"] = [
                asdict(stale_cheque) for stale_cheque in brs.stale_cheques
            ]

    return response


@brs_cc_bp.route("/enable_delete/add/", methods=["POST", "GET"])
@login_required
@admin_required
def enable_month_deletion():
    form = EnableDeleteMonthForm()

    if form.validate_on_submit():
        delete_entries = CentralisedChequeEnableDelete()
        form.populate_obj(delete_entries)
        db.session.add(delete_entries)
        db.session.commit()
        flash("Added.")
    return render_template("brs_cc_enable_month_delete.html", form=form)


# edit month
@brs_cc_bp.route("/enable_delete/edit/<int:month_id>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_month_deletion(month_id):
    delete_entries = CentralisedChequeEnableDelete.query.get_or_404(month_id)
    form = EnableDeleteMonthForm(obj=delete_entries)
    if form.validate_on_submit():
        form.populate_obj(delete_entries)
        db.session.commit()
        flash("Updated.")
    return render_template("brs_cc_enable_month_delete.html", form=form)


# list months
@brs_cc_bp.route("/enable_delete/")
@login_required
@admin_required
def list_month_deletions():
    list_months = CentralisedChequeEnableDelete.query.order_by(
        CentralisedChequeEnableDelete.date_of_month
    )
    column_names = CentralisedChequeEnableDelete.query.statement.columns.keys()

    return render_template(
        "brs_cc_list_enable_delete.html", list=list_months, column_names=column_names
    )
