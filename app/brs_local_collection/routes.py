from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

import pandas as pd
from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from set_view_permissions import admin_required
from extensions import db
from utils import datetime_format

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


@brs_local_collection.route("/", methods=["POST", "GET"])
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


@brs_local_collection.route("/view/brs/<int:brs_key>/")
@login_required
def view_brs(brs_key):
    brs_entry = db.get_or_404(BankReconLocalCollectionDetails, brs_key)
    brs_entry.summary.require_access(current_user)

    gl_column_labels = {
        "opening_balance": (
            "Opening balance as per GL",
            datetime_format(brs_entry.summary.month, "%B-%Y", "previous"),
            True,
        ),
        "opening_on_hand": (
            "Add: Opening on hand",
            datetime_format(brs_entry.summary.month, "%B-%Y", "previous"),
            False,
        ),
        "transactions": (
            "Add: Collections during the month",
            brs_entry.summary.month,
            False,
        ),
        "cancellations": (
            "Less: Cancellations / cheque dishonours during the month",
            brs_entry.summary.month,
            False,
        ),
        "balance_before_fund_transfer": (
            "Balance before fund transfer",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            True,
        ),
        "fund_transfer": ("Less: Fund transfer", brs_entry.summary.month, False),
        "bank_charges": ("Less: Bank charges", brs_entry.summary.month, False),
        "closing_on_hand": (
            "Less: Closing On hand",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            False,
        ),
        "closing_balance": (
            "Closing balance as per GL",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            True,
        ),
    }
    bank_recon_column_labels = {
        "closing_balance": (
            "Closing balance as per GL",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            True,
        ),
        "deposited_not_credited": (
            "Less: Deposited but not credited",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            False,
        ),
        "short_credited": (
            "Less: Short credit entries",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            False,
        ),
        "excess_credited": (
            "Add: Excess credit entries",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            False,
        ),
        "balance_as_per_bank": (
            "Closing balance as per bank statement",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            True,
        ),
    }

    return render_template(
        "brs_lc_view_brs_entry.html",
        brs_entry=brs_entry,
        gl_column_labels=gl_column_labels,
        bank_recon_column_labels=bank_recon_column_labels,
        # get_brs_bank=get_brs_bank,
        # display=display,
    )
    # if display == "html":
    #     return html
    # elif display == "pdf":
    #     return render_pdf(HTML(string=html))


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

        # Upload outstanding cheques
        process_cheque_file(
            form.data.get("file_outstanding_entries"),
            "bank_recon_local_collection_outstanding",
            brs_entry.id,
        )

        # Upload short_credit cheques
        process_cheque_file(
            form.data.get("file_short_credit_entries"),
            "bank_recon_local_collection_short_credit",
            brs_entry.id,
        )

        # Upload excess_credit cheques
        process_cheque_file(
            form.data.get("file_excess_credit_entries"),
            "bank_recon_local_collection_excess_credit",
            brs_entry.id,
        )
        return redirect(url_for(".brs_lc_view_status", key=brs_entry.id))

    opening_balance, opening_on_hand = get_prev_month_closing_balance(brs.id)
    form.opening_balance.data = opening_balance
    form.opening_on_hand.data = opening_on_hand
    return render_template("brs_lc_data_entry_v2.html", brs_entry=brs, form=form)


@brs_local_collection.route("/view/<int:key>/", methods=["POST", "GET"])
@login_required
def brs_lc_view_entry(key):
    brs = db.get_or_404(BankReconLocalCollectionDetails, key)
    brs.summary.require_access(current_user)
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
        "brs_lc_view_entry.html",
        brs=brs,
        column_labels=column_labels,
    )


def process_cheque_file(file, table_name, brs_entry_id):
    if not file:
        return

    required_columns = [
        "mode_of_collection",
        "instrument_number",
        "instrument_amount",
        "date_of_instrument",
        "date_of_collection",
        "remarks",
    ]
    str_columns = ["instrument_number", "remarks", "mode_of_collection"]
    date_columns = ["date_of_instrument", "date_of_collection"]
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
    df["brs_details_id"] = brs_entry_id

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
            previous_month_brs.closing_balance,
            previous_month_brs.closing_on_hand,
        )
    else:
        return 0, 0
