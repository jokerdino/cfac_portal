from datetime import datetime
import calendar
from sqlalchemy.sql import exists, select
from typing import List, Any

import pandas as pd

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_weasyprint import HTML, render_pdf
from flask_login import current_user, login_required
from sqlalchemy import create_engine, func

from app.brs import brs_bp
from app.brs.models import BRS, BRS_month, Outstanding
from app.brs.forms import BRSForm, BRS_entry, DashboardForm, RawDataForm

from app.tickets.tickets_routes import humanize_datetime


@brs_bp.route("/home", methods=["POST", "GET"])
@login_required
def brs_home_page():
    if current_user.user_type == "oo_user":
        brs_entries = BRS.query.filter(BRS.uiic_office_code == current_user.oo_code)
    elif current_user.user_type in ["admin", "ro_user"]:
        return redirect(url_for("brs.brs_dashboard"))
    else:
        return "No permission"
    return render_template(
        "brs_home.html",
        brs_entries=brs_entries,
        colour_check=colour_check,
        percent_completed=percent_completed,
    )


@brs_bp.route("/<string:ro_code>/<string:month>", methods=["POST", "GET"])
@login_required
def brs_ro_wise(ro_code, month):
    if current_user.user_type == "admin" or (
        current_user.user_type == "ro_user" and current_user.ro_code == ro_code
    ):
        brs_entries = BRS.query.filter(
            BRS.uiic_regional_code == ro_code, BRS.month == month
        )
    else:
        abort(404)
    return render_template(
        "brs_home.html",
        brs_entries=brs_entries,
        colour_check=colour_check,
        percent_completed=percent_completed,
    )


@brs_bp.route("/dashboard", methods=["POST", "GET"])
@login_required
def brs_dashboard():
    form = DashboardForm()

    month_choices = BRS.query.with_entities(BRS.month).distinct()
    form.month.choices = ["View all"] + [x.month for x in month_choices]

    query = BRS.query.with_entities(
        BRS.uiic_regional_code,
        BRS.month,
        func.count(BRS.cash_bank),
        func.count(BRS.cash_brs_id),
        func.count(BRS.cheque_bank),
        func.count(BRS.cheque_brs_id),
        func.count(BRS.pg_bank),
        func.count(BRS.pg_brs_id),
        func.count(BRS.pos_bank),
        func.count(BRS.pos_brs_id),
        func.count(BRS.bbps_bank),
        func.count(BRS.bbps_brs_id),
        func.count(BRS.local_collection_bank),
        func.count(BRS.local_collection_brs_id),
    ).group_by(BRS.uiic_regional_code, BRS.month)

    if current_user.user_type == "ro_user":
        query = query.filter(BRS.uiic_regional_code == current_user.ro_code)

    if form.validate_on_submit():
        month = form.data["month"]
        if month != "View all":
            query = query.filter(BRS.month == month)
        return render_template("brs_dashboard.html", query=query, form=form)

    return render_template("brs_dashboard.html", query=query, form=form)


def colour_check(brs_key):
    brs_entry = BRS.query.get_or_404(brs_key)

    bool_cash = bool(brs_entry.cash_brs_id) if brs_entry.cash_bank else True
    bool_cheque = bool(brs_entry.cheque_brs_id) if brs_entry.cheque_bank else True
    bool_pg = bool(brs_entry.pg_brs_id) if brs_entry.pg_bank else True
    bool_pos = bool(brs_entry.pos_brs_id) if brs_entry.pos_bank else True
    bool_bbps = bool(brs_entry.bbps_brs_id) if brs_entry.bbps_bank else True
    bool_local_collection = (
        bool(brs_entry.local_collection_brs_id)
        if brs_entry.local_collection_bank
        else True
    )

    colour_code = all(
        [bool_cash, bool_cheque, bool_pg, bool_pos, bool_bbps, bool_local_collection]
    )
    return colour_code


def percent_completed(brs_key):
    brs_entry = BRS.query.get_or_404(brs_key)

    denom = 0
    numerator = 0

    if brs_entry.cash_bank:
        denom += 1
        if brs_entry.cash_brs_id:
            numerator += 1

    if brs_entry.cheque_bank:
        denom += 1
        if brs_entry.cheque_brs_id:
            numerator += 1

    if brs_entry.pg_bank:
        denom += 1
        if brs_entry.pg_brs_id:
            numerator += 1

    if brs_entry.pos_bank:
        denom += 1
        if brs_entry.pos_brs_id:
            numerator += 1

    if brs_entry.bbps_bank:
        denom += 1
        if brs_entry.bbps_brs_id:
            numerator += 1

    if brs_entry.local_collection_bank:
        denom += 1
        if brs_entry.local_collection_brs_id:
            numerator += 1

    try:
        return (numerator / denom) * 100
    except ZeroDivisionError:
        return 100


@brs_bp.route("/bulk_upload", methods=["POST", "GET"])
@login_required
def bulk_upload_brs():
    if request.method == "POST":
        upload_file = request.files.get("file")
        df_user_upload = pd.read_csv(
            upload_file, dtype={"uiic_regional_code": str, "uiic_office_code": str}
        )
        df_user_upload["timestamp"] = datetime.now()
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        df_user_upload.to_sql("brs", engine, if_exists="append", index=False)
        flash("BRS records have been uploaded to database.")

    return render_template("bulk_brs_upload.html")


@brs_bp.route("/upload_brs/<int:brs_key>", methods=["POST", "GET"])
@login_required
def upload_brs(brs_key):
    from server import db

    # list_months_delete contains list of months that are enabled for soft deletion.
    # If the month is not mentioned in the list,
    # the months will not be available for deletion by admin or RO user.
    # When a new month base file is uploaded, the month has to be manually added to the list right now.
    # TODO: Build a frontend for the same to enable or disable?
    brs_entry = BRS.query.get_or_404(brs_key)
    list_months_delete = ["January-2024", "February-2024"]

    # list_delete_brs contains list of roles enabled for deleting BRS entered by Operating office and Regional office
    # As per requirement, both HO user and RO user can soft delete the BRS data.

    list_delete_brs = []
    if brs_entry.month in list_months_delete:
        list_delete_brs = ["admin", "ro_user"]

    form = BRSForm()
    if form.validate_on_submit():
        if form.data["delete_cash_brs"]:
            current_id = brs_entry.cash_brs_id
            brs_entry.cash_brs_id = None
        if form.data["delete_cheque_brs"]:
            current_id = brs_entry.cheque_brs_id
            brs_entry.cheque_brs_id = None
        if form.data["delete_pos_brs"]:
            current_id = brs_entry.pos_brs_id
            brs_entry.pos_brs_id = None
        if form.data["delete_pg_brs"]:
            current_id = brs_entry.pg_brs_id
            brs_entry.pg_brs_id = None
        if form.data["delete_bbps_brs"]:
            current_id = brs_entry.bbps_brs_id
            brs_entry.bbps_brs_id = None
        if form.data["delete_local_collection_brs"]:
            current_id = brs_entry.local_collection_brs_id
            brs_entry.local_collection_brs_id = None
        brs_month = BRS_month.query.get_or_404(current_id)
        brs_month.status = "Deleted"
        db.session.commit()
        return redirect(url_for("brs.upload_brs", brs_key=brs_key))
    return render_template(
        "open_brs.html", brs_entry=brs_entry, form=form, list_delete_brs=list_delete_brs
    )


@brs_bp.route("/view_consolidated/<int:brs_key>")
@login_required
def view_consolidated_brs(brs_key):
    brs_entry = BRS.query.get_or_404(brs_key)

    cash_brs = (
        BRS_month.query.get_or_404(brs_entry.cash_brs_id)
        if brs_entry.cash_brs_id
        else None
    )

    cheque_brs = (
        BRS_month.query.get_or_404(brs_entry.cheque_brs_id)
        if brs_entry.cheque_brs_id
        else None
    )
    pg_brs = (
        BRS_month.query.get_or_404(brs_entry.pg_brs_id) if brs_entry.pg_brs_id else None
    )
    pos_brs = (
        BRS_month.query.get_or_404(brs_entry.pos_brs_id)
        if brs_entry.pos_brs_id
        else None
    )
    bbps_brs = (
        BRS_month.query.get_or_404(brs_entry.bbps_brs_id)
        if brs_entry.bbps_brs_id
        else None
    )
    local_collection_brs = (
        BRS_month.query.get_or_404(brs_entry.local_collection_brs_id)
        if brs_entry.local_collection_brs_id
        else None
    )
    return render_template(
        "view_consolidated_brs.html",
        brs_month=brs_entry,
        cash_brs=cash_brs,
        cheque_brs=cheque_brs,
        pg_brs=pg_brs,
        pos_brs=pos_brs,
        bbps_brs=bbps_brs,
        local_collection_brs=local_collection_brs,
        pdf=False,
    )


@brs_bp.route("/pdf_consolidated/<int:brs_key>")
@login_required
def view_consolidated_brs_pdf(brs_key):
    brs_entry = BRS.query.get_or_404(brs_key)

    cash_brs = (
        BRS_month.query.get_or_404(brs_entry.cash_brs_id)
        if brs_entry.cash_brs_id
        else None
    )

    cheque_brs = (
        BRS_month.query.get_or_404(brs_entry.cheque_brs_id)
        if brs_entry.cheque_brs_id
        else None
    )
    pg_brs = (
        BRS_month.query.get_or_404(brs_entry.pg_brs_id) if brs_entry.pg_brs_id else None
    )
    pos_brs = (
        BRS_month.query.get_or_404(brs_entry.pos_brs_id)
        if brs_entry.pos_brs_id
        else None
    )
    bbps_brs = (
        BRS_month.query.get_or_404(brs_entry.bbps_brs_id)
        if brs_entry.bbps_brs_id
        else None
    )
    local_collection_brs = (
        BRS_month.query.get_or_404(brs_entry.local_collection_brs_id)
        if brs_entry.local_collection_brs_id
        else None
    )
    html = render_template(
        "view_consolidated_brs.html",
        brs_month=brs_entry,
        cash_brs=cash_brs,
        cheque_brs=cheque_brs,
        pg_brs=pg_brs,
        pos_brs=pos_brs,
        bbps_brs=bbps_brs,
        local_collection_brs=local_collection_brs,
        pdf=True,
    )
    return render_pdf(HTML(string=html))


@brs_bp.route("/download_format/<string:requirement>")
@login_required
def download_format(requirement):
    if requirement == "cash":
        return send_file("outstanding_cash_upload_format.csv")
    else:
        return send_file("outstanding_cheques_upload_format.csv")


@brs_bp.route("/view/<int:brs_key>")
@login_required
def view_brs(brs_key):
    brs_entry = BRS_month.query.get_or_404(brs_key)
    # brs = BRS.query.get_or_404(brs_entry.brs_id)
    # brs_outstanding_entries = Outstanding.query.filter(
    #   Outstanding.brs_month_id == brs_key
    # ).filter(Outstanding.instrument_amount.is_not(None))
    return render_template(
        "view_brs_entry.html",
        #     brs=brs,
        brs_entry=brs_entry,
        #    outstanding=brs_outstanding_entries,
        get_brs_bank=get_brs_bank,
        pdf=False,
    )


@brs_bp.route("/pdf/<int:brs_key>")
@login_required
def view_brs_pdf(brs_key):
    brs_entry = BRS_month.query.get_or_404(brs_key)
    # brs_month = BRS.query.get_or_404(brs_entry.brs_id)
    # brs_outstanding_entries = Outstanding.query.filter(
    #     Outstanding.brs_month_id == brs_key
    # ).filter(Outstanding.instrument_amount.is_not(None))
    html = render_template(
        "view_brs_entry.html",
        #        brs_month=brs_month,
        brs_entry=brs_entry,
        #       outstanding=brs_outstanding_entries,
        get_brs_bank=get_brs_bank,
        pdf=True,
    )
    return render_pdf(HTML(string=html))


def get_prev_month_amount(requirement: str, brs_id: int) -> (float, float):
    brs_entry = BRS.query.get_or_404(brs_id)

    datetime_object = datetime.strptime(brs_entry.month, "%B-%Y")
    if datetime_object.month - 1 > 0:
        month_number = datetime_object.month - 1
        year = datetime_object.year
    else:
        month_number = 12
        year = datetime_object.year - 1
    prev_month: str = f"{calendar.month_name[month_number]}-{year}"
    prev_brs_entry: bool = (
        BRS.query.filter(BRS.uiic_office_code == brs_entry.uiic_office_code)
        .filter(BRS.month == prev_month)
        .first()
    )
    if prev_brs_entry:
        if requirement == "cash":
            brs_entry_id = prev_brs_entry.cash_brs_id
        elif requirement == "cheque":
            brs_entry_id = prev_brs_entry.cheque_brs_id
        elif requirement == "pg":
            brs_entry_id = prev_brs_entry.pg_brs_id
        elif requirement == "pos":
            brs_entry_id = prev_brs_entry.pos_brs_id
        elif requirement == "bbps":
            brs_entry_id = prev_brs_entry.bbps_brs_id
        elif requirement == "local_collection":
            brs_entry_id = prev_brs_entry.local_collection_brs_id
        if brs_entry_id:
            prev_brs = BRS_month.query.get_or_404(brs_entry_id)
            return prev_brs.int_closing_balance, prev_brs.int_closing_on_hand
        else:
            return 0, 0
    else:
        return 0, 0


def prevent_duplicate_brs(requirement: str, brs_id: int) -> bool:
    brs_entry = BRS.query.get_or_404(brs_id)

    brs_available: bool = False
    if requirement == "cash":
        brs_available = True if brs_entry.cash_brs_id else False
    elif requirement == "cheque":
        brs_available = True if brs_entry.cheque_brs_id else False
    elif requirement == "pg":
        brs_available = True if brs_entry.pg_brs_id else False
    elif requirement == "pos":
        brs_available = True if brs_entry.pos_brs_id else False
    elif requirement == "bbps":
        brs_available = True if brs_entry.bbps_brs_id else False
    elif requirement == "local_collection":
        brs_available = True if brs_entry.local_collection_brs_id else False

    return brs_available


@brs_bp.route("/<int:brs_id>/<string:requirement>/add_brs", methods=["POST", "GET"])
@login_required
def enter_brs(requirement, brs_id):
    brs_entry = BRS.query.get_or_404(brs_id)
    form = BRS_entry()
    from server import db

    if prevent_duplicate_brs(requirement, brs_id):
        flash("BRS has already been submitted.")
    elif form.validate_on_submit():
        prepared_by = form.data["prepared_by"]
        prepared_by_employee_number = form.data["prepared_by_employee_number"]
        opening_balance = form.data["opening_balance"] or 0
        opening_on_hand = form.data["opening_on_hand"] or 0
        transactions = form.data["transactions"] or 0
        cancellations = form.data["cancellations"] or 0
        fund_transfer = form.data["fund_transfer"] or 0
        bank_charges = form.data["bank_charges"] or 0
        closing_on_hand = form.data["closing_on_hand"] or 0
        closing_balance = (
            opening_balance
            + opening_on_hand
            + transactions
            - cancellations
            - fund_transfer
            - bank_charges
            - closing_on_hand
        )
        brs_remarks = form.data["remarks"] or None
        if closing_balance < 0:
            flash("Closing balance cannot be less than 0.")
        else:
            brs = BRS_month(
                brs_id=brs_id,
                brs_type=requirement,
                int_opening_balance=opening_balance,
                int_opening_on_hand=opening_on_hand,
                int_transactions=transactions,
                int_cancellations=cancellations,
                int_fund_transfer=fund_transfer,
                int_bank_charges=bank_charges,
                int_closing_on_hand=closing_on_hand,
                int_closing_balance=closing_balance,
                remarks=brs_remarks,
                timestamp=datetime.now(),
                prepared_by=prepared_by,
                prepared_by_employee_number=prepared_by_employee_number,
            )

            if closing_balance > 0:
                try:
                    if requirement == "cash":
                        date_columns = ["date_of_collection"]
                        df_outstanding_entries = pd.read_csv(
                            form.data["outstanding_entries"],
                            parse_dates=date_columns,
                            dtype={"instrument_amount": float},
                        )
                    else:
                        date_columns = ["date_of_instrument", "date_of_collection"]
                        df_outstanding_entries = pd.read_csv(
                            form.data["outstanding_entries"],
                            parse_dates=date_columns,
                            dtype={
                                "instrument_amount": float,
                                "instrument_number": str,
                            },
                        )

                    try:
                        sum_os_entries = df_outstanding_entries[
                            "instrument_amount"
                        ].sum()
                        if not float(sum_os_entries) == float(closing_balance):
                            flash(
                                f"Closing balance {closing_balance} is not matching with sum of outstanding entries {sum_os_entries}."
                            )

                        else:
                            db.session.add(brs)
                            db.session.commit()
                            if requirement == "cash":
                                brs_entry.cash_brs_id = brs.id
                            elif requirement == "cheque":
                                brs_entry.cheque_brs_id = brs.id
                            elif requirement == "pg":
                                brs_entry.pg_brs_id = brs.id
                            elif requirement == "pos":
                                brs_entry.pos_brs_id = brs.id
                            elif requirement == "bbps":
                                brs_entry.bbps_brs_id = brs.id
                            elif requirement == "local_collection":
                                brs_entry.local_collection_brs_id = brs.id

                            df_outstanding_entries["brs_month_id"] = brs.id
                            engine = create_engine(
                                current_app.config.get("SQLALCHEMY_DATABASE_URI")
                            )

                            df_outstanding_entries.dropna(
                                subset=["instrument_amount"]
                            ).to_sql(
                                "outstanding", engine, if_exists="append", index=False
                            )
                            db.session.commit()
                            return redirect(url_for("brs.upload_brs", brs_key=brs_id))
                    except Exception as e:
                        flash(f"Please upload in prescribed format.")
                except pd.errors.EmptyDataError:
                    flash(
                        "Please upload details of Closing balance in prescribed format."
                    )
                except Exception as e:
                    flash(f"Please upload in prescribed format.")
            else:
                db.session.add(brs)
                db.session.commit()

                if requirement == "cash":
                    brs_entry.cash_brs_id = brs.id
                elif requirement == "cheque":
                    brs_entry.cheque_brs_id = brs.id
                elif requirement == "pg":
                    brs_entry.pg_brs_id = brs.id
                elif requirement == "pos":
                    brs_entry.pos_brs_id = brs.id
                elif requirement == "bbps":
                    brs_entry.bbps_brs_id = brs.id
                elif requirement == "local_collection":
                    brs_entry.local_collection_brs_id = brs.id

                db.session.commit()

                return redirect(url_for("brs.upload_brs", brs_key=brs_id))

    form.opening_balance.data: float = get_prev_month_amount(requirement, brs_id)[0]
    form.opening_on_hand.data: float = get_prev_month_amount(requirement, brs_id)[1]

    return render_template(
        "add_brs_entry.html",
        form=form,
        brs_entry=brs_entry,
        requirement=requirement,
        get_brs_bank=get_brs_bank,
    )


@brs_bp.route("/dashboard/view_raw_data", methods=["GET", "POST"])
@login_required
def list_brs_entries():
    """Function to return genuine BRS entries to be considered for passing JV
    a. Entries which are not deleted AND
    b. Entries which have no closing balance AND
    c. Entries which have closing balance and corresponding outstanding entries."""
    form = RawDataForm()

    month_choices = BRS.query.with_entities(BRS.month).distinct()

    list_period = [datetime.strptime(item[0], "%B-%Y") for item in month_choices]

    # sorting the items of list_period in reverse order
    # newer months will be above
    list_period.sort(reverse=True)
    # list_period is now dynamically added as dropdown choice list to the SelectField
    form.month.choices = [item.strftime("%B-%Y") for item in list_period]

    if form.validate_on_submit():
        month = form.data["month"]
        brs_type = form.data["brs_type"]

        list_all_brs_entries = (
            BRS_month.query.join(BRS, BRS.id == BRS_month.brs_id)
            #   .join(Outstanding, Outstanding.brs_month_id == BRS_month.id)
            .filter(
                (BRS_month.status.is_(None))
                & (BRS.month == month)
                & (BRS_month.brs_type == brs_type)
            )
        )

        subquery = (
            Outstanding.query.with_entities(Outstanding.brs_month_id)
            .distinct()
            .subquery()
        )

        list_all_brs_entries = list_all_brs_entries.filter(
            (BRS_month.int_closing_balance == 0)
            | (
                (BRS_month.int_closing_balance > 0)
                # & (Outstanding.brs_month_id == BRS_month.id)
                & (BRS_month.id.in_(select(subquery)))
            )
        )

        if current_user.user_type == "ro_user":
            list_all_brs_entries = list_all_brs_entries.filter(
                BRS.uiic_regional_code == current_user.ro_code
            )

        return render_template(
            "view_brs_raw_data.html",
            brs_entries=list_all_brs_entries,
            get_brs_bank=get_brs_bank,
            humanize_datetime=humanize_datetime,
        )
    return render_template("brs_raw_data_form.html", form=form)


@brs_bp.route("/dashboard/view_raw_data/exceptions")
@login_required
def list_brs_entries_exceptions():
    """Function to return exceptions - BRS monthly records for the following conditions
    1. The BRS monthly record is deleted OR
    2.
        a. The BRS monthly record is not deleted AND
        b. Closing balance is greater than zero AND
        c. Outstanding entries are not present for the BRS monthly record."""

    list_all_brs_entries = BRS_month.query.filter(
        (BRS_month.status == "Deleted")
        | (BRS_month.status.is_(None))
        & (
            (BRS_month.int_closing_balance > 0)
            & (~exists().where(Outstanding.brs_month_id == BRS_month.id))
        )
    )

    return render_template(
        "view_brs_raw_data.html",
        brs_entries=list_all_brs_entries,
        get_brs_bank=get_brs_bank,
        humanize_datetime=humanize_datetime,
    )


@brs_bp.route("/dashboard/outstanding")
@login_required
def list_outstanding_entries():
    outstanding_entries = (
        Outstanding.query.join(BRS_month, BRS_month.id == Outstanding.brs_month_id)
        .join(BRS, BRS_month.brs_id == BRS.id)
        .filter(BRS_month.status.is_(None))
    )
    return render_template(
        "view_outstanding_entries.html",
        outstanding=outstanding_entries,
        get_brs_bank=get_brs_bank,
    )


def get_brs_bank(brs_id, requirement):
    brs_entry = BRS.query.get_or_404(brs_id)
    if requirement == "cash":
        return brs_entry.cash_bank
    elif requirement == "cheque":
        return brs_entry.cheque_bank
    elif requirement == "pos":
        return brs_entry.pos_bank
    elif requirement == "pg":
        return brs_entry.pg_bank
    elif requirement == "bbps":
        return brs_entry.bbps_bank
    elif requirement == "local_collection":
        return brs_entry.local_collection_bank
