from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

import pandas as pd
from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from set_view_permissions import admin_required
from extensions import db

from . import brs_local_collection
from .forms import (
    BankReconEntryForm,
    BankReconDeleteForm,
    AddBankReconLocalCollectionSummaryForm,
    MonthFilterForm,
)
from .models import (
    BankReconLocalCollectionSummary,
    BankReconLocalCollectionDetails,
    BankReconLocalCollectionOutstanding,
    BankReconLocalCollectionShortCredit,
    BankReconLocalCollectionExcessCredit,
    BankReconLocalCollectionDelete,
)


@brs_local_collection.route("/add", methods=["POST", "GET"])
@login_required
@admin_required
def add_brs_details_item():
    form = AddBankReconLocalCollectionSummaryForm()
    if form.validate_on_submit():
        brs = BankReconLocalCollectionSummary()
        form.populate_obj(brs)
        db.session.add(brs)
        db.session.commit()
        flash("BRS details for local collection successfully added.")
        # return redirect(url_for("brs"))

    return render_template(
        "brs_local_collection_form.html", form=form, title="Add BRS details item"
    )


@brs_local_collection.route("/dashboard", methods=["POST", "GET"])
@login_required
def brs_local_collection_dashboard():
    form = MonthFilterForm()

    month_choices = db.session.scalars(
        db.select(BankReconLocalCollectionSummary.month.distinct())
    )
    list_period = [datetime.strptime(item, "%B-%Y") for item in month_choices]
    list_period.sort(reverse=True)
    form.month.choices = ["View all"] + [item.strftime("%B-%Y") for item in list_period]

    query = db.select(
        BankReconLocalCollectionSummary.regional_office,
        BankReconLocalCollectionSummary.month,
        db.func.count(BankReconLocalCollectionSummary.local_collection_bank_name),
        db.func.count(BankReconLocalCollectionSummary.local_collection_brs_month_id),
    ).group_by(
        BankReconLocalCollectionSummary.regional_office,
        BankReconLocalCollectionSummary.month,
    )

    if current_user.user_type == "ro_user":
        query = query.where(
            BankReconLocalCollectionSummary.regional_office == current_user.ro_code
        )
    if form.validate_on_submit():
        month = form.month.data
        if month != "View all":
            query = query.where(BankReconLocalCollectionSummary.month == month)
    result = db.session.execute(query)
    return render_template("brs_lc_dashboard.html", query=result, form=form)


@brs_local_collection.route("/<string:month>/<string:ro_code>/")
@login_required
def brs_lc_homepage(month, ro_code):
    if current_user.user_type == "ro_user":
        ro_code = current_user.ro_code
    query = db.session.scalars(
        db.select(BankReconLocalCollectionSummary)
        .where(
            BankReconLocalCollectionSummary.regional_office == ro_code,
            BankReconLocalCollectionSummary.month == month,
        )
        .order_by(BankReconLocalCollectionSummary.operating_office)
    )
    return render_template("brs_lc_homepage.html", query=query)


@brs_local_collection.route("/view/<int:key>/", methods=["GET", "POST"])
@login_required
def brs_lc_view_status(key):
    brs = db.get_or_404(BankReconLocalCollectionSummary, key)
    brs.require_access(current_user)
    delete_button: bool = db.session.scalar(
        db.select(BankReconLocalCollectionDelete.enable_delete).where(
            BankReconLocalCollectionDelete.month == brs.month
        )
    )

    form = BankReconDeleteForm()
    if form.validate_on_submit():
        brs.local_collection_brs_month_id = None
        brs.details.status = "Deleted"
        db.session.commit()
        flash("BRS entry has been deleted.")
        return redirect(url_for(".brs_lc_view_status", key=key))

    return render_template(
        "brs_lc_view_status.html",
        brs=brs,
        form=form,
        delete_button=delete_button,
    )


@brs_local_collection.route("/<int:key>/add/", methods=["POST", "GET"])
@login_required
def brs_lc_data_entry(key):
    brs = db.get_or_404(BankReconLocalCollectionSummary, key)

    last_date_of_month = datetime.strptime(brs.month, "%B-%Y") + relativedelta(
        months=1, day=1
    )
    brs.require_access(current_user)
    form = BankReconEntryForm(obj=brs)
    form.last_date_of_month.data = last_date_of_month

    if form.validate_on_submit():
        brs_entry = BankReconLocalCollectionDetails()
        form.populate_obj(brs_entry)
        brs_entry.brs_id = brs.id
        db.session.add(brs_entry)
        db.session.commit()
        brs.local_collection_brs_month_id = brs_entry.id
        db.session.commit()

        # Upload unencashed cheques
        process_cheque_file(
            form.data.get("unencashed_cheques_file"),
            "centralised_cheque_instrument_unencashed_details",
            brs_entry.id,
        )

        # Upload stale cheques
        process_cheque_file(
            form.data.get("stale_cheques_file"),
            "centralised_cheque_instrument_stale_details",
            brs_entry.id,
        )
        return redirect(url_for(".brs_lc_view_status", key=brs.id))

    unencashed, stale = get_prev_month_closing_balance(brs.id)
    #  form.opening_balance_stale.data = stale
    # form.opening_balance_unencashed.data = unencashed
    return render_template("brs_lc_data_entry.html", brs=brs, form=form)


def process_cheque_file(file, table_name, brs_entry_id):
    if not file:
        return

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
    str_columns = [
        "voucher_number",
        "transaction_id",
        "instrument_number",
        "payee_name",
        "remarks",
    ]
    date_columns = ["instrument_date", "voucher_date"]
    df = pd.read_excel(file, usecols=required_columns)

    # Convert date columns
    for date_col in date_columns:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(
                df[date_col], errors="coerce", format="%d/%m/%Y"
            )

    # Convert string columns
    df[str_columns] = df[str_columns].astype(str)

    # Add foreign key
    df["centralised_cheque_details_id"] = brs_entry_id

    # Save to database
    df.to_sql(table_name, db.engine, if_exists="append", index=False)


def get_prev_month_closing_balance(brs_id):
    brs_summary = db.get_or_404(BankReconLocalCollectionSummary, brs_id)

    # need to be rectified
    # previous_month = brs_summary.month.replace(day=1) - timedelta(days=1)

    prev_month = datetime.strptime(brs_summary.month, "%B-%Y") - relativedelta(months=1)
    prev_month_str = prev_month.strftime("%B-%Y")

    previous_month_brs = db.session.scalar(
        db.select(BankReconLocalCollectionDetails)
        .where(
            BankReconLocalCollectionDetails.brs_id
            == BankReconLocalCollectionSummary.id,
            BankReconLocalCollectionSummary.operating_office
            == brs_summary.operating_office,
            BankReconLocalCollectionSummary.month == prev_month_str,
        )
        .order_by(BankReconLocalCollectionDetails.id.desc())
    )
    if previous_month_brs:
        return (
            previous_month_brs.closing_balance_unencashed,
            previous_month_brs.closing_balance_stale,
        )
    else:
        return 0, 0
