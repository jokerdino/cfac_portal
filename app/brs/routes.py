from math import fabs
from datetime import datetime
from dateutil import relativedelta
import calendar
from sqlalchemy.sql import exists, select
import sqlalchemy

import pandas as pd

from flask import (
    abort,
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

from set_view_permissions import admin_required

from app.brs import brs_bp
from app.brs.models import (
    BRS,
    BRS_month,
    Outstanding,
    DeleteEntries,
    BankReconExcessCredit,
    BankReconShortCredit,
    BankReconAccountDetails,
)
from app.brs.forms import (
    BRSForm,
    BRS_entry,
    DashboardForm,
    RawDataForm,
    EnableDeleteMonthForm,
)

# from app.tickets.tickets_routes import humanize_datetime
from app.brs.brs_helper_functions import upload_brs_file


@brs_bp.route("/home", methods=["POST", "GET"])
@login_required
def brs_home_page():
    if current_user.user_type == "oo_user":
        brs_entries = BRS.query.filter(BRS.uiic_office_code == current_user.oo_code)
    elif current_user.user_type in ["admin", "ro_user"]:
        return redirect(url_for("brs.brs_dashboard"))
    else:
        abort(404)
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


@brs_bp.route("/percentage", methods=["POST", "GET"])
@login_required
@admin_required
def brs_percentage():
    form = DashboardForm()

    month_choices = BRS.query.with_entities(BRS.month).distinct()

    list_period = [datetime.strptime(item[0], "%B-%Y") for item in month_choices]
    # sorting the items of list_period in reverse order
    # newer months will be above
    list_period.sort(reverse=True)

    # list_period is now dynamically added as dropdown choice list to the SelectField
    form.month.choices = ["View all"] + [item.strftime("%B-%Y") for item in list_period]

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

    if form.validate_on_submit():
        month = form.data["month"]
        if month != "View all":
            query = query.filter(BRS.month == month)

    return render_template("brs_dashboard_percentage.html", query=query, form=form)


@brs_bp.route("/dashboard", methods=["POST", "GET"])
@login_required
def brs_dashboard():
    form = DashboardForm()

    month_choices = BRS.query.with_entities(BRS.month).distinct()

    list_period = [datetime.strptime(item[0], "%B-%Y") for item in month_choices]
    list_period.sort(reverse=True)

    form.month.choices = ["View all"] + [item.strftime("%B-%Y") for item in list_period]

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
        df_brs_upload = pd.read_csv(
            upload_file, dtype={"uiic_regional_code": str, "uiic_office_code": str}
        )
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        upload_brs_file(df_brs_upload, engine, current_user.username)
        # df_brs_upload["timestamp"] = datetime.now()

        # df_month = df_brs_upload["month"].drop_duplicates().to_frame()
        # df_month = df_month.rename(columns={"month": "txt_month"})
        # df_month["bool_enable_delete"] = True
        # df_month["created_by"] = current_user.username
        # df_month["created_on"] = datetime.now()

        # df_brs_upload.to_sql("brs", engine, if_exists="append", index=False)
        # df_month.to_sql("delete_entries", engine, if_exists="append", index=False)
        flash("BRS records have been uploaded to database.")

    return render_template("bulk_brs_upload.html")


# add month
@brs_bp.route("/enable_delete/add", methods=["POST", "GET"])
@login_required
def enable_month_deletion():
    form = EnableDeleteMonthForm()
    from extensions import db

    if form.validate_on_submit():
        delete_entries = DeleteEntries(
            txt_month=form.data["txt_month"],
            bool_enable_delete=form.data["bool_enable_delete"],
            created_by=current_user.username,
            created_on=datetime.now(),
        )
        db.session.add(delete_entries)
        db.session.commit()
    return render_template("enable_month_delete.html", form=form)


# edit month
@brs_bp.route("/enable_delete/edit/<int:month_id>", methods=["POST", "GET"])
@login_required
def edit_month_deletion(month_id):
    form = EnableDeleteMonthForm()
    from extensions import db

    delete_entries = DeleteEntries.query.get_or_404(month_id)

    if form.validate_on_submit():
        delete_entries.bool_enable_delete = form.data["bool_enable_delete"]
        delete_entries.updated_by = current_user.username
        delete_entries.updated_on = datetime.now()
        db.session.commit()
    form.txt_month.data = delete_entries.txt_month
    form.bool_enable_delete.data = delete_entries.bool_enable_delete
    return render_template("enable_month_delete.html", form=form)


# list months
@brs_bp.route("/enable_delete/list")
@login_required
def list_month_deletions():
    list = DeleteEntries.query.order_by(DeleteEntries.id)
    column_names = DeleteEntries.query.statement.columns.keys()

    return render_template(
        "list_months_delete.html", list=list, column_names=column_names
    )


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
    query_list_months_delete = DeleteEntries.query.with_entities(
        DeleteEntries.txt_month
    ).filter(DeleteEntries.bool_enable_delete == True)
    list_months_delete = [txt_month[0] for txt_month in query_list_months_delete]
    # print(list_months_delete)
    # print(type(list_months_delete))
    # list_months_delete2 = [
    #     "January-2024",
    #     "February-2024",
    #     "March-2024",
    #     "April-2024",
    #     "May-2024",
    # ]

    # list_delete_brs contains list of roles enabled for deleting BRS entered by Operating office and Regional office
    # As per requirement, both HO user and RO user can soft delete the BRS data.

    list_delete_brs = []
    if brs_entry.month in list_months_delete:
        list_delete_brs = ["admin", "ro_user"]

    form = BRSForm()
    if form.validate_on_submit():
        if form.data["delete_cash_brs"]:
            brs_month = BRS_month.query.get_or_404(brs_entry.cash_brs_id)
            brs_month.status = "Deleted"
            brs_entry.cash_brs_id = None
        if form.data["delete_cheque_brs"]:
            brs_month = BRS_month.query.get_or_404(brs_entry.cheque_brs_id)
            brs_month.status = "Deleted"
            brs_entry.cheque_brs_id = None
        if form.data["delete_pos_brs"]:
            brs_month = BRS_month.query.get_or_404(brs_entry.pos_brs_id)
            brs_month.status = "Deleted"
            brs_entry.pos_brs_id = None
        if form.data["delete_pg_brs"]:
            brs_month = BRS_month.query.get_or_404(brs_entry.pg_brs_id)
            brs_month.status = "Deleted"
            brs_entry.pg_brs_id = None
        if form.data["delete_bbps_brs"]:
            brs_month = BRS_month.query.get_or_404(brs_entry.bbps_brs_id)
            brs_month.status = "Deleted"
            brs_entry.bbps_brs_id = None
        if form.data["delete_local_collection_brs"]:
            brs_month = BRS_month.query.get_or_404(brs_entry.local_collection_brs_id)
            brs_month.status = "Deleted"
            brs_entry.local_collection_brs_id = None
        # brs_month = BRS_month.query.get_or_404(current_id)
        # brs_month.status = "Deleted"
        db.session.commit()
        flash("BRS entry has been deleted.")
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
        return send_file("download_formats/outstanding_cash_upload_format.csv")
    else:
        return send_file("download_formats/outstanding_cheques_upload_format.csv")


@brs_bp.route("/view/<int:brs_key>")
@login_required
def view_brs(brs_key):
    brs_entry = BRS_month.query.get_or_404(brs_key)

    return render_template(
        "view_brs_entry.html",
        brs_entry=brs_entry,
        get_brs_bank=get_brs_bank,
        pdf=False,
    )


@brs_bp.route("/pdf/<int:brs_key>")
@login_required
def view_brs_pdf(brs_key):
    brs_entry = BRS_month.query.get_or_404(brs_key)

    html = render_template(
        "view_brs_entry.html",
        brs_entry=brs_entry,
        get_brs_bank=get_brs_bank,
        pdf=True,
    )
    return render_pdf(HTML(string=html))


def get_prev_month_amount(requirement: str, brs_id: int):
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


def validate_outstanding_entries(
    df_form_data_os_entries: pd.DataFrame,
    requirement: str,
    closing_balance: float,
    brs_id: int,
):
    # for cash, instrument amount and date of collection is mandatory
    # for other requirements, instrument amount, instrument date, date of collection and instrument number are mandatory
    # negative values are not allowed to be entered
    from extensions import db

    # find month of BRS period to test if date_of_instrument and date_of_collection are within that time frame
    brs = db.session.query(BRS).get_or_404(brs_id)
    brs_month = datetime.strptime(brs.month, "%B-%Y") + relativedelta.relativedelta(
        months=1, day=1
    )

    if requirement == "cash":
        date_columns: list[str] = ["date_of_collection"]
        try:
            df_os_entries = pd.read_csv(
                df_form_data_os_entries,
                parse_dates=date_columns,
                dtype={"instrument_amount": float},
                dayfirst=True,
            )

            # check for future dated collections
            df_future_date_of_collection = df_os_entries[
                df_os_entries["date_of_collection"] >= brs_month
            ]

            if len(df_future_date_of_collection) > 0:
                return (7, pd.DataFrame, 0)
        except ValueError as e:
            return (6, pd.DataFrame, 0)
        except TypeError as e:
            return (11, pd.DataFrame, 0)
    else:
        date_columns = ["date_of_instrument", "date_of_collection"]
        try:
            df_os_entries = pd.read_csv(
                df_form_data_os_entries,
                parse_dates=date_columns,
                dtype={
                    "instrument_amount": float,
                    "instrument_number": str,
                },
                dayfirst=True,
            )

            # check for future dated instruments
            df_future_date_of_instrument = df_os_entries[
                df_os_entries["date_of_instrument"] >= brs_month
            ]

            if len(df_future_date_of_instrument) > 0:
                return (8, pd.DataFrame, 0)

            # check for future dated collections
            df_future_date_of_collection = df_os_entries[
                df_os_entries["date_of_collection"] >= brs_month
            ]

            if len(df_future_date_of_collection) > 0:
                return (7, pd.DataFrame, 0)

        except ValueError as e:
            return (6, pd.DataFrame, 0)
        except TypeError as e:
            return (12, pd.DataFrame, 0)

    try:
        sum_os_entries: float = df_os_entries["instrument_amount"].sum()
    except KeyError as e:
        # try/except to ensure instrument_amount column is entered in uploaded file
        return (9, pd.DataFrame, 0)

    if (fabs(float(sum_os_entries) - float(closing_balance))) > 0.001:
        return (5, pd.DataFrame, sum_os_entries)

    # checking for negative values
    df_negative_values = df_os_entries[df_os_entries["instrument_amount"].lt(0)]
    if len(df_negative_values) > 0:
        return (3, pd.DataFrame, sum_os_entries)

    df_na_date_of_collection = df_os_entries[
        df_os_entries["date_of_collection"].isnull()
    ]
    if len(df_na_date_of_collection) > 0:
        return (4, pd.DataFrame, sum_os_entries)

    if requirement != "cash":
        df_na_instrument_date = df_os_entries[
            df_os_entries["date_of_instrument"].isnull()
        ]

        # try/except to ensure instrument_number column is entered in uploaded file
        try:
            df_na_instrument_number = df_os_entries[
                df_os_entries["instrument_number"].isnull()
            ]
        except KeyError as e:
            return (13, pd.DataFrame, 0)
        if len(df_na_instrument_date) > 0:
            return (1, pd.DataFrame, sum_os_entries)

        elif len(df_na_instrument_number) > 0:
            return (2, pd.DataFrame, sum_os_entries)

    return 10, df_os_entries, sum_os_entries


def update_brs_id(requirement: str, brs_entry, integer_brs_id: int) -> None:

    if requirement == "cash":
        brs_entry.cash_brs_id = integer_brs_id
    elif requirement == "cheque":
        brs_entry.cheque_brs_id = integer_brs_id
    elif requirement == "pg":
        brs_entry.pg_brs_id = integer_brs_id
    elif requirement == "pos":
        brs_entry.pos_brs_id = integer_brs_id
    elif requirement == "bbps":
        brs_entry.bbps_brs_id = integer_brs_id
    elif requirement == "local_collection":
        brs_entry.local_collection_brs_id = integer_brs_id


# function to render error messages when outstanding entries/short_credit/excess_credit are uploaded


def render_error_message(
    amount_entered_in_form: float,
    nature_of_transaction: str,
    form_data,
    requirement: str,
    brs_id: int,
) -> tuple[int, pd.DataFrame]:

    status_validate_os_entries, df_outstanding_entries, sum_of_instrument_amount = (
        validate_outstanding_entries(
            form_data,
            requirement,
            amount_entered_in_form,
            brs_id,
        )
    )

    # if status_validate_os_entries == 1:
    #     flash("Date of instrument must be entered in dd/mm/yyyy format.")
    # elif status_validate_os_entries == 2:
    #     flash("Instrument number must be entered.")
    # elif status_validate_os_entries == 3:
    #     flash("Please do not enter negative amounts.")
    # elif status_validate_os_entries == 4:
    #     flash("Date of collection must be entered in dd/mm/yyyy format")
    # elif status_validate_os_entries == 5:
    #     flash(
    #         f"{nature_of_transaction} {amount_entered_in_form} is not matching with sum of the uploaded entries {sum_of_instrument_amount}."
    #     )
    # elif status_validate_os_entries == 6:
    #     flash(
    #         "Please upload in prescribed format: Dates in dd/mm/yyyy format and instrument_amount in integer format."
    #     )
    # elif status_validate_os_entries == 7:
    #     flash("Date of collection cannot be after BRS period.")
    # elif status_validate_os_entries == 8:
    #     flash("Date of instrument cannot be after BRS period.")
    # elif status_validate_os_entries == 9:
    #     flash("instrument_amount is not entered in uploaded file.")
    # elif status_validate_os_entries == 11:
    #     flash("Date of collection must be entered in dd/mm/yyyy format.")
    # elif status_validate_os_entries == 12:
    #     flash("Date of instrument/collection must be entered in dd/mm/yyyy format.")

    display_error_messages: dict[int, str] = {
        1: "Date of instrument must be entered in dd/mm/yyyy format.",
        2: "Instrument number must be entered.",
        3: "Please do not enter negative amounts.",
        4: "Date of collection must be entered in dd/mm/yyyy format.",
        5: f"{nature_of_transaction} {amount_entered_in_form} is not matching with sum of the uploaded entries {sum_of_instrument_amount}.",
        6: "Please upload in prescribed format: Dates in dd/mm/yyyy format and instrument_amount in integer format.",
        7: "Date of collection cannot be after BRS period.",
        8: "Date of instrument cannot be after BRS period.",
        9: "'instrument_amount' column is not entered in uploaded file.",
        10: "Successfully uploaded the BRS.",
        11: "Date of collection must be entered in dd/mm/yyyy format.",
        12: "Date of instrument/collection must be entered in dd/mm/yyyy format.",
        13: "'instrument_number' column is not entered in uploaded file.",
    }

    if status_validate_os_entries != 10:
        flash(
            display_error_messages.get(
                status_validate_os_entries, "Error in processing the input."
            )
        )
    return status_validate_os_entries, df_outstanding_entries


def upload_df_entries_to_database(
    df_outstanding_entries, engine, name_of_table, brs_id
):
    df_outstanding_entries["brs_month_id"] = brs_id

    df_outstanding_entries = df_outstanding_entries.loc[
        :, ~df_outstanding_entries.columns.str.match("Unnamed")
    ]
    df_outstanding_entries.dropna(subset=["instrument_amount"]).to_sql(
        name_of_table, engine, if_exists="append", index=False
    )


@brs_bp.route("/<int:brs_id>/<string:requirement>/add_brs", methods=["POST", "GET"])
@login_required
def enter_brs(requirement, brs_id):
    brs_entry = BRS.query.get_or_404(brs_id)
    form = BRS_entry()
    from server import db
    from wtforms.validators import DataRequired  # , Regexp

    if form.data["int_deposited_not_credited"]:
        form.file_outstanding_entries.validators = [DataRequired()]
    if form.data["int_short_credited"]:
        form.file_short_credit_entries.validators = [DataRequired()]
    if form.data["int_excess_credited"]:
        form.file_excess_credit_entries.validators = [DataRequired()]

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
        deposited_not_credited = form.data["int_deposited_not_credited"] or 0
        short_credited = form.data["int_short_credited"] or 0
        excess_credited = form.data["int_excess_credited"] or 0

        # for local collection, we are collecting balance as per bank statement
        # if requirement == "local_collection":
        closing_balance_bank_statement = (
            form.data["int_closing_balance_bank_statement"] or 0
        )
        bank_balance = (
            closing_balance + excess_credited - deposited_not_credited - short_credited
        )

        closing_balance_breakup = (
            deposited_not_credited
            + short_credited
            - excess_credited
            + closing_balance_bank_statement
        )

        brs_remarks = form.data["remarks"] or None
        if (fabs(float(closing_balance_breakup) - float(closing_balance))) > 0.001:
            flash(
                f"Closing balance {closing_balance} must tally with closing balance breakup {closing_balance_breakup}."
            )
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
                int_deposited_not_credited=deposited_not_credited,
                int_excess_credited=excess_credited,
                int_short_credited=short_credited,
                int_balance_as_per_bank=bank_balance,
                remarks=brs_remarks,
                timestamp=datetime.now(),
                prepared_by=prepared_by,
                prepared_by_employee_number=prepared_by_employee_number,
            )

            if closing_balance != 0:
                (
                    status_validate_excess_credited,
                    status_validate_short_credited,
                    status_validate_os_entries,
                ) = (10, 10, 10)

                # if closing balance is not zero

                # if not credited entries are there, tally with csv file
                if deposited_not_credited > 0:
                    if not form.data["file_outstanding_entries"]:
                        flash(
                            "Please upload details of entries which are deposited but not credited."
                        )
                    else:
                        # (
                        #     status_validate_os_entries,
                        #     df_outstanding_entries,
                        #     sum_os_entries,
                        # ) = validate_outstanding_entries(
                        #     form.data["file_outstanding_entries"],
                        #     requirement,
                        #     deposited_not_credited,
                        #     brs_id,
                        # )
                        status_validate_os_entries, df_outstanding_entries = (
                            render_error_message(
                                # status_validate_os_entries,
                                deposited_not_credited,
                                # sum_os_entries,
                                "Deposited but not credited entries",
                                form.data["file_outstanding_entries"],
                                requirement,
                                brs_id,
                            )
                        )
                        # if status_validate_os_entries == 1:
                        #     flash(
                        #         "Date of instrument must be entered in dd/mm/yyyy format."
                        #     )
                        # elif status_validate_os_entries == 2:
                        #     flash("Instrument number must be entered.")
                        # elif status_validate_os_entries == 3:
                        #     flash("Please do not enter negative amounts.")
                        # elif status_validate_os_entries == 4:
                        #     flash(
                        #         "Date of collection must be entered in dd/mm/yyyy format"
                        #     )
                        # elif status_validate_os_entries == 5:
                        #     flash(
                        #         f"Deposited but not credited entries {deposited_not_credited} is not matching with sum of the uploaded entries {sum_os_entries}."
                        #     )

                        # elif status_validate_os_entries == 6:
                        #     flash(
                        #         "Please upload in prescribed format: Dates in dd/mm/yyyy format and instrument_amount in integer format."
                        #     )
                        # elif status_validate_os_entries == 7:
                        #     flash("Date of collection cannot be after BRS period.")
                        # elif status_validate_os_entries == 8:
                        #     flash("Date of instrument cannot be after BRS period.")
                        # elif status_validate_os_entries == 9:
                        #     flash("instrument_amount is not entered in uploaded file.")
                        # elif status_validate_os_entries == 11:
                        #     flash("Date of collection must be in dd/mm/yyyy format.")
                        # elif status_validate_os_entries == 12:
                        #     flash(
                        #         "Date of instrument/collection must be in dd/mm/yyyy format."
                        #     )
                if short_credited > 0:
                    if not form.data["file_short_credit_entries"]:
                        flash("Please upload details of short credited entries.")
                    else:
                        # (
                        #     status_validate_short_credited,
                        #     df_short_credit_entries,
                        #     sum_short_credits,
                        # ) = validate_outstanding_entries(
                        #     form.data["file_short_credit_entries"],
                        #     requirement,
                        #     short_credited,
                        #     brs_id,
                        # )
                        # render_error_message(
                        #     status_validate_short_credited,
                        #     short_credited,
                        #     sum_short_credits,
                        #     "Short credit amount",
                        # )
                        status_validate_short_credited, df_short_credit_entries = (
                            render_error_message(
                                short_credited,
                                "Short credit amount",
                                form.data["file_short_credit_entries"],
                                requirement,
                                brs_id,
                            )
                        )
                        # if status_validate_short_credited == 1:
                        #     flash(
                        #         "Date of instrument must be entered in dd/mm/yyyy format."
                        #     )
                        # elif status_validate_short_credited == 2:
                        #     flash("Instrument number must be entered.")
                        # elif status_validate_short_credited == 3:
                        #     flash("Please do not enter negative amounts.")
                        # elif status_validate_short_credited == 4:
                        #     flash(
                        #         "Date of collection must be entered in dd/mm/yyyy format"
                        #     )
                        # elif status_validate_short_credited == 5:
                        #     flash(
                        #         f"Short credit amount {short_credited} is not matching with sum of short credited entries {sum_short_credits}."
                        #     )

                        # elif status_validate_short_credited == 6:
                        #     flash(
                        #         "Please upload in prescribed format: Dates in dd/mm/yyyy format and instrument_amount in integer format."
                        #     )
                        # elif status_validate_short_credited == 7:
                        #     flash("Date of collection cannot be after BRS period.")
                        # elif status_validate_short_credited == 8:
                        #     flash("Date of instrument cannot be after BRS period.")
                        # elif status_validate_short_credited == 9:
                        #     flash("instrument_amount is not entered in uploaded file.")
                        # elif status_validate_short_credited == 11:
                        #     flash("Date of collection must be in dd/mm/yyyy format.")
                        # elif status_validate_short_credited == 12:
                        #     flash(
                        #         "Date of instrument/collection must be in dd/mm/yyyy format."
                        #     )
                if excess_credited > 0:
                    if not form.data["file_excess_credit_entries"]:
                        flash("Please upload details of excess credited entries.")
                    else:
                        # (
                        #     status_validate_excess_credited,
                        #     df_excess_credit_entries,
                        #     sum_excess_credits,
                        # ) = validate_outstanding_entries(
                        #     form.data["file_excess_credit_entries"],
                        #     requirement,
                        #     excess_credited,
                        #     brs_id,
                        # )
                        # render_error_message(
                        #     status_validate_excess_credited,
                        #     excess_credited,
                        #     sum_excess_credits,
                        #     "Excess credit amount",
                        # )
                        (
                            status_validate_excess_credited,
                            df_excess_credit_entries,
                        ) = render_error_message(
                            excess_credited,
                            "Excess credit amount",
                            form.data["file_excess_credit_entries"],
                            requirement,
                            brs_id,
                        )
                        # if status_validate_excess_credited == 1:
                        #     flash(
                        #         "Date of instrument must be entered in dd/mm/yyyy format."
                        #     )
                        # elif status_validate_excess_credited == 2:
                        #     flash("Instrument number must be entered.")
                        # elif status_validate_excess_credited == 3:
                        #     flash("Please do not enter negative amounts.")
                        # elif status_validate_excess_credited == 4:
                        #     flash(
                        #         "Date of collection must be entered in dd/mm/yyyy format"
                        #     )
                        # elif status_validate_excess_credited == 5:
                        #     flash(
                        #         f"Excess credit amount {excess_credited} is not matching with sum of excess credited entries {sum_excess_credits}."
                        #     )

                        # elif status_validate_excess_credited == 6:
                        #     flash(
                        #         "Please upload in prescribed format: Dates in dd/mm/yyyy format and instrument_amount in integer format."
                        #     )
                        # elif status_validate_excess_credited == 7:
                        #     flash("Date of collection cannot be after BRS period.")
                        # elif status_validate_excess_credited == 8:
                        #     flash("Date of instrument cannot be after BRS period.")
                        # elif status_validate_excess_credited == 9:
                        #     flash("instrument_amount is not entered in uploaded file.")
                        # elif status_validate_excess_credited == 11:
                        #     flash("Date of collection must be in dd/mm/yyyy format.")
                        # elif status_validate_excess_credited == 12:
                        #     flash(
                        #         "Date of instrument/collection must be in dd/mm/yyyy format."
                        #     )
                if (
                    status_validate_os_entries
                    == status_validate_short_credited
                    == status_validate_excess_credited
                    == 10
                ):

                    db.session.add(brs)
                    db.session.commit()
                    update_brs_id(requirement, brs_entry, brs.id)
                    engine = create_engine(
                        current_app.config.get("SQLALCHEMY_DATABASE_URI")
                    )
                    # if (
                    #     deposited_not_credited > 0
                    #     and form.data["file_outstanding_entries"]
                    # ):
                    #     df_outstanding_entries["brs_month_id"] = brs.id
                    # if excess_credited > 0 and form.data["file_excess_credit_entries"]:
                    #     df_excess_credit_entries["brs_month_id"] = brs.id
                    # if short_credited > 0 and form.data["file_short_credit_entries"]:
                    #     df_short_credit_entries["brs_month_id"] = brs.id
                    try:
                        # deposited not but credited entries
                        if (
                            deposited_not_credited > 0
                            and form.data["file_outstanding_entries"]
                        ):
                            upload_df_entries_to_database(
                                df_outstanding_entries, engine, "outstanding", brs.id
                            )
                            # df_outstanding_entries = df_outstanding_entries.loc[
                            #     :, ~df_outstanding_entries.columns.str.match("Unnamed")
                            # ]
                            # df_outstanding_entries.dropna(
                            #     subset=["instrument_amount"]
                            # ).to_sql(
                            #     "outstanding", engine, if_exists="append", index=False
                            # )
                        # short credit entries
                        if (
                            short_credited > 0
                            and form.data["file_short_credit_entries"]
                        ):
                            upload_df_entries_to_database(
                                df_short_credit_entries,
                                engine,
                                "bank_recon_short_credit",
                                brs.id,
                            )
                            # df_short_credit_entries = df_short_credit_entries.loc[
                            #     :, ~df_short_credit_entries.columns.str.match("Unnamed")
                            # ]
                            # df_short_credit_entries.dropna(
                            #     subset=["instrument_amount"]
                            # ).to_sql(
                            #     "bank_recon_short_credit",
                            #     engine,
                            #     if_exists="append",
                            #     index=False,
                            # )
                        # excess credit entries
                        if (
                            excess_credited > 0
                            and form.data["file_excess_credit_entries"]
                        ):
                            upload_df_entries_to_database(
                                df_excess_credit_entries,
                                engine,
                                "bank_recon_excess_credit",
                                brs.id,
                            )
                            # df_excess_credit_entries = df_excess_credit_entries.loc[
                            #     :,
                            #     ~df_excess_credit_entries.columns.str.match("Unnamed"),
                            # ]
                            # df_excess_credit_entries.dropna(
                            #     subset=["instrument_amount"]
                            # ).to_sql(
                            #     "bank_recon_excess_credit",
                            #     engine,
                            #     if_exists="append",
                            #     index=False,
                            # )
                        db.session.commit()
                        return redirect(url_for("brs.upload_brs", brs_key=brs_id))
                    except sqlalchemy.exc.DataError as e:
                        db.session.delete(brs)
                        update_brs_id(requirement, brs_entry, None)
                        db.session.commit()
                        flash(
                            "Please ensure dates are entered in dd/mm/yyyy format and amount in integer format."
                        )

            else:
                db.session.add(brs)
                db.session.commit()
                update_brs_id(requirement, brs_entry, brs.id)

                db.session.commit()

                return redirect(url_for("brs.upload_brs", brs_key=brs_id))

    prev_month_opening_balance, prev_month_opening_on_hand = get_prev_month_amount(
        requirement, brs_id
    )
    form.opening_balance.data = prev_month_opening_balance
    form.opening_on_hand.data = prev_month_opening_on_hand

    return render_template(
        "add_brs_entry.html",
        form=form,
        brs_entry=brs_entry,
        requirement=requirement,
        get_brs_bank=get_brs_bank,
        prevent_duplicate_brs=prevent_duplicate_brs,
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

        list_all_brs_entries = BRS_month.query.join(
            BRS, BRS.id == BRS_month.brs_id
        ).filter(
            (BRS_month.status.is_(None))
            & (BRS.month == month)
            # & (BRS_month.brs_type == brs_type)
        )

        if brs_type != "View all":
            list_all_brs_entries = list_all_brs_entries.filter(
                BRS_month.brs_type == brs_type
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
            # humanize_datetime=humanize_datetime,
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

    # subquery = (
    #     Outstanding.query.with_entities(Outstanding.brs_month_id).distinct().subquery()
    # )

    list_all_brs_entries = BRS_month.query.filter(
        #   (BRS_month.status == "Deleted")
        ~BRS_month.status.is_(None)
        # | (
        #     BRS_month.status.is_(None)
        #     & (
        #         (BRS_month.int_closing_balance > 0)
        #         & (~BRS_month.id.in_(select(subquery)))
        #     )
        # )
    )

    return render_template(
        "view_brs_raw_data.html",
        brs_entries=list_all_brs_entries,
        get_brs_bank=get_brs_bank,
        # humanize_datetime=humanize_datetime,
    )


@brs_bp.route("/dashboard/view_raw_data/exceptions2")
@login_required
def list_brs_entries_exceptions2():
    """Function to return exceptions - BRS monthly records for the following conditions
    1. The BRS monthly record is deleted OR
    2.
        a. The BRS monthly record is not deleted AND
        b. Closing balance is greater than zero AND
        c. Outstanding entries are not present for the BRS monthly record."""

    subquery = (
        Outstanding.query.with_entities(Outstanding.brs_month_id).distinct().subquery()
    )

    list_all_brs_entries = BRS_month.query.filter(
        # (BRS_month.status == "Deletedbyquery")
        # | (
        #  BRS_month.status.is_(None)
        # &
        (BRS_month.int_closing_balance > 0)
        & (~BRS_month.id.in_(select(subquery)))
    )
    # )
    # brs_id = list_all_brs_entries.with_entities(BRS_month.id)
    # for id in brs_id:
    #    brs_entry = BRS_month.query.get(id)
    #    brs_entry.status = "Deleted"

    # from extensions import db
    # db.session.commit()

    return render_template(
        "view_brs_raw_data.html",
        brs_entries=list_all_brs_entries,
        get_brs_bank=get_brs_bank,
        # humanize_datetime=humanize_datetime,
    )


@brs_bp.route("/dashboard/outstanding", methods=["POST", "GET"])
@login_required
def list_outstanding_entries():
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

        outstanding_entries = (
            Outstanding.query.join(BRS_month, BRS_month.id == Outstanding.brs_month_id)
            .join(BRS, BRS_month.brs_id == BRS.id)
            .filter(
                BRS_month.status.is_(None)
                & (BRS.month == month)
                # & (BRS_month.brs_type == brs_type)
            )
        )
        if brs_type != "View all":
            outstanding_entries = outstanding_entries.filter(
                BRS_month.brs_type == brs_type
            )
        if current_user.user_type == "ro_user":
            outstanding_entries = outstanding_entries.filter(
                BRS.uiic_regional_code == current_user.ro_code
            )

        return render_template(
            "view_outstanding_entries.html",
            outstanding=outstanding_entries,
            get_brs_bank=get_brs_bank,
            title="outstanding",
        )
    return render_template("brs_raw_data_form.html", form=form)


@brs_bp.route("/dashboard/short_credit", methods=["POST", "GET"])
@login_required
def list_short_credit_entries():
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

        short_credit_entries = (
            BankReconShortCredit.query.join(
                BRS_month, BRS_month.id == BankReconShortCredit.brs_month_id
            )
            .join(BRS, BRS_month.brs_id == BRS.id)
            .filter(
                BRS_month.status.is_(None)
                & (BRS.month == month)
                #   & (BRS_month.brs_type == brs_type)
            )
        )
        if brs_type != "View all":
            short_credit_entries = short_credit_entries.filter(
                BRS_month.brs_type == brs_type
            )
        if current_user.user_type == "ro_user":
            short_credit_entries = short_credit_entries.filter(
                BRS.uiic_regional_code == current_user.ro_code
            )

        return render_template(
            "view_outstanding_entries.html",
            outstanding=short_credit_entries,
            get_brs_bank=get_brs_bank,
            title="short credit",
        )
    return render_template("brs_raw_data_form.html", form=form)


@brs_bp.route("/dashboard/excess_credit", methods=["POST", "GET"])
@login_required
def list_excess_credit_entries():
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

        excess_credit_entries = (
            BankReconExcessCredit.query.join(
                BRS_month, BRS_month.id == BankReconExcessCredit.brs_month_id
            )
            .join(BRS, BRS_month.brs_id == BRS.id)
            .filter(
                BRS_month.status.is_(None)
                & (BRS.month == month)
                # & (BRS_month.brs_type == brs_type)
            )
        )
        if brs_type != "View all":
            excess_credit_entries = excess_credit_entries.filter(
                BRS_month.brs_type == brs_type
            )
        if current_user.user_type == "ro_user":
            excess_credit_entries = excess_credit_entries.filter(
                BRS.uiic_regional_code == current_user.ro_code
            )

        return render_template(
            "view_outstanding_entries.html",
            outstanding=excess_credit_entries,
            get_brs_bank=get_brs_bank,
            title="excess credit",
        )
    return render_template("brs_raw_data_form.html", form=form)


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


@brs_bp.route(
    "/api/v1/brs/get_closing_balance/<string:office_code>/<string:month>/<string:brs_type>"
)
def get_brs_closing_balance(office_code, month, brs_type):
    """for feeding into E-Formats
    returns closing balance if office code, month and type of BRS is provided
    Sample URL: http://0.0.0.0:8080/brs/api/v1/brs/get_closing_balance/500200/January-2024/local_collection
    """

    filtered_brs = BRS.query.filter(
        (BRS.uiic_office_code == office_code) & (BRS.month == month)
    ).first()
    if brs_type == "cash":
        brs_entry_id = filtered_brs.cash_brs_id
    elif brs_type == "cheque":
        brs_entry_id = filtered_brs.cheque_brs_id
    elif brs_type == "pos":
        brs_entry_id = filtered_brs.pos_brs_id
    elif brs_type == "pg":
        brs_entry_id = filtered_brs.pg_brs_id
    elif brs_type == "bbps":
        brs_entry_id = filtered_brs.bbps_brs_id
    elif brs_type == "local_collection":
        brs_entry_id = filtered_brs.local_collection_brs_id

    brs_entry = BRS_month.query.get(brs_entry_id)

    closing_balance = brs_entry.int_closing_balance if brs_entry else 0
    return f"{closing_balance}"


def get_bank_account_detail(requirement: str, bank_name: str) -> str:

    bank = (
        BankReconAccountDetails.query.with_entities(
            BankReconAccountDetails.str_bank_account_number,
            BankReconAccountDetails.str_ifsc_code,
        )
        .filter(
            (BankReconAccountDetails.str_brs_type == requirement)
            & (BankReconAccountDetails.str_name_of_bank == bank_name)
        )
        .first()
    )

    return bank


@brs_bp.route("/api/v1/brs/<string:office_code>/<string:month>/")
def get_schedule_bbc(office_code: str, month: str) -> dict:
    """Sample URL: http://0.0.0.0:8080/brs/api/v1/brs/500200/January-2024/
    Function for entering BBC schedule in E formats
    Input: Office code and month
    Output: dictionary containing office code, month, each BRS type,
    name of bank, ifsc code, account number, closing balance and bank balance
    """
    filtered_brs = BRS.query.filter(
        (BRS.uiic_office_code == office_code) & (BRS.month == month)
    ).first()

    # return all existing brs types for the office code
    # if brs type exists, return bank name
    # and closing balance
    json_dict = {f"{office_code}": {"month": month}}
    if not filtered_brs:
        return json_dict
    if filtered_brs.cash_bank:
        account_number, ifsc_code = get_bank_account_detail(
            "cash", filtered_brs.cash_bank
        )
        json_dict[f"{office_code}"].update(
            {
                "cash": {
                    "bank": filtered_brs.cash_bank.upper(),
                    "account_number": account_number,
                    "ifsc_code": ifsc_code,
                }
            }
        )

        if filtered_brs.cash_brs_id:
            brs_entry = BRS_month.query.get(filtered_brs.cash_brs_id)
            closing_balance = brs_entry.int_closing_balance if brs_entry else 0
            bank_balance = brs_entry.int_balance_as_per_bank if brs_entry else 0
            json_dict[f"{office_code}"]["cash"].update(
                {"closing_balance": closing_balance, "bank_balance": bank_balance}
            )
    if filtered_brs.cheque_bank:
        account_number, ifsc_code = get_bank_account_detail(
            "cheque", filtered_brs.cheque_bank
        )
        json_dict[f"{office_code}"].update(
            {
                "cheque": {
                    "bank": filtered_brs.cheque_bank.upper(),
                    "account_number": account_number,
                    "ifsc_code": ifsc_code,
                }
            }
        )
        if filtered_brs.cheque_brs_id:
            brs_entry = BRS_month.query.get(filtered_brs.cheque_brs_id)
            closing_balance = brs_entry.int_closing_balance if brs_entry else 0
            bank_balance = brs_entry.int_balance_as_per_bank if brs_entry else 0
            json_dict[f"{office_code}"]["cheque"].update(
                {"closing_balance": closing_balance, "bank_balance": bank_balance}
            )
    if filtered_brs.pg_bank:
        account_number, ifsc_code = get_bank_account_detail("pg", filtered_brs.pg_bank)
        json_dict[f"{office_code}"].update(
            {
                "pg": {
                    "bank": filtered_brs.pg_bank.upper(),
                    "account_number": account_number,
                    "ifsc_code": ifsc_code,
                }
            }
        )
        if filtered_brs.pg_brs_id:
            brs_entry = BRS_month.query.get(filtered_brs.pg_brs_id)
            closing_balance = brs_entry.int_closing_balance if brs_entry else 0
            bank_balance = brs_entry.int_balance_as_per_bank if brs_entry else 0
            json_dict[f"{office_code}"]["pg"].update(
                {"closing_balance": closing_balance, "bank_balance": bank_balance}
            )
    if filtered_brs.bbps_bank:
        account_number, ifsc_code = get_bank_account_detail(
            "bbps", filtered_brs.bbps_bank
        )
        json_dict[f"{office_code}"].update(
            {
                "bbps": {
                    "bank": filtered_brs.bbps_bank.upper(),
                    "account_number": account_number,
                    "ifsc_code": ifsc_code,
                }
            }
        )
        if filtered_brs.bbps_brs_id:
            brs_entry = BRS_month.query.get(filtered_brs.bbps_brs_id)
            closing_balance = brs_entry.int_closing_balance if brs_entry else 0
            bank_balance = brs_entry.int_balance_as_per_bank if brs_entry else 0
            json_dict[f"{office_code}"]["bbps"].update(
                {"closing_balance": closing_balance, "bank_balance": bank_balance}
            )
    if filtered_brs.pos_bank:
        account_number, ifsc_code = get_bank_account_detail(
            "pos", filtered_brs.pos_bank
        )
        json_dict[f"{office_code}"].update(
            {
                "pos": {
                    "bank": filtered_brs.pos_bank.upper(),
                    "account_number": account_number,
                    "ifsc_code": ifsc_code,
                }
            }
        )
        if filtered_brs.pos_brs_id:
            brs_entry = BRS_month.query.get(filtered_brs.pos_brs_id)
            closing_balance = brs_entry.int_closing_balance if brs_entry else 0
            bank_balance = brs_entry.int_balance_as_per_bank if brs_entry else 0
            json_dict[f"{office_code}"]["pos"].update(
                {"closing_balance": closing_balance, "bank_balance": bank_balance}
            )

    return json_dict


@brs_bp.route("/api/v1/brs/get_percent_complete/<string:regional_office_code>/")
def get_percent_completion(regional_office_code):
    """for e-formats checklist of BRS completion
    returns percentage completion if regional office code is entered"""
    query = (
        BRS.query.with_entities(
            func.count(BRS.cash_bank)
            + func.count(BRS.cheque_bank)
            + func.count(BRS.pg_bank)
            + func.count(BRS.pos_bank)
            + func.count(BRS.bbps_bank)
            + func.count(BRS.local_collection_bank),
            func.count(BRS.cash_brs_id)
            + func.count(BRS.cheque_brs_id)
            + func.count(BRS.pg_brs_id)
            + func.count(BRS.pos_brs_id)
            + func.count(BRS.bbps_brs_id)
            + func.count(BRS.local_collection_brs_id),
        )
        .filter(BRS.uiic_regional_code == regional_office_code)
        .group_by(BRS.uiic_regional_code)
    )

    # add filter to remove FY23-24 out of BRS percentage calculations
    query = query.filter(BRS.financial_year != "23-24")

    percent_complete = (query[0][1] / query[0][0]) * 100 if query else 0
    return f"{percent_complete}"


@brs_bp.route("/percent_list/")
@login_required
@admin_required
def get_percent_completion_list():

    ro_list = [
        "010000",
        "020000",
        "030000",
        "040000",
        "050000",
        "060000",
        "070000",
        "080000",
        "090000",
        "100000",
        "110000",
        "120000",
        "130000",
        "140000",
        "150000",
        "160000",
        "170000",
        "180000",
        "190000",
        "200000",
        "210000",
        "220000",
        "230000",
        "240000",
        "250000",
        "260000",
        "270000",
        "280000",
        "290000",
        "300000",
        "500100",
        "500200",
        "500300",
        "500400",
        "500500",
        "500700",
    ]
    return render_template(
        "brs_dashboard_percentage_list.html",
        get_percentage_completion=get_percent_completion,
        ro_list=ro_list,
    )
