from datetime import date, datetime

from dateutil.relativedelta import relativedelta

import pandas as pd
import sqlalchemy

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from flask_weasyprint import HTML, render_pdf
from sqlalchemy.orm import joinedload

from app.brs import brs_bp
from app.brs.forms import (
    BankReconAccountDetailsAddForm,
    BRSEntryForm,
    BRSForm,
    DashboardForm,
    EnableDeleteMonthForm,
    RawDataForm,
)
from app.brs.models import (
    BRS,
    BankReconAccountDetails,
    BankReconExcessCredit,
    BankReconShortCredit,
    BRSMonth,
    DeleteEntries,
    Outstanding,
)
from set_view_permissions import admin_required, ro_user_only

# from .brs_helper_functions import get_financial_year, upload_brs_file

from extensions import db


def get_financial_year(input_date):
    if input_date.strftime("%m") in ["01", "02", "03"]:
        prev_year = input_date - relativedelta(years=1)
        return f"{prev_year.strftime('%y')}-{input_date.strftime('%y')}"
    else:
        next_year = input_date - relativedelta(years=-1)
        return f"{input_date.strftime('%y')}-{next_year.strftime('%y')}"


@brs_bp.route("/upload_previous_month/")
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
    current_month = date.today() - relativedelta(months=1)

    # prev_month is the month before current_month
    prev_month = current_month - relativedelta(months=1)
    # FY will be fetched based on current_month value
    financial_year = get_financial_year(current_month)

    current_month_string = current_month.strftime("%B-%Y")

    stmt = db.select(
        BRS.uiic_regional_code,
        BRS.uiic_office_code,
        db.literal(financial_year),
        db.literal(current_month_string),
        BRS.cash_bank,
        BRS.cheque_bank,
        BRS.pos_bank,
        BRS.pg_bank,
        BRS.bbps_bank,
        BRS.dqr_bank,
    ).where(BRS.month == prev_month.strftime("%B-%Y"))

    insert_stmt = db.insert(BRS).from_select(
        [
            BRS.uiic_regional_code,
            BRS.uiic_office_code,
            BRS.financial_year,
            BRS.month,
            BRS.cash_bank,
            BRS.cheque_bank,
            BRS.pos_bank,
            BRS.pg_bank,
            BRS.bbps_bank,
            BRS.dqr_bank,
        ],
        stmt,
    )
    db.session.execute(insert_stmt)

    delete_month_entry = DeleteEntries(
        txt_month=current_month.strftime("%B-%Y"), created_by="AUTOUPLOAD"
    )
    db.session.add(delete_month_entry)
    db.session.commit()

    return "Success"


@brs_bp.route("/home", methods=["POST", "GET"])
@login_required
def brs_home_page():
    if current_user.user_type == "oo_user":
        brs_entries = db.session.scalars(
            db.select(BRS).where(BRS.uiic_office_code == current_user.oo_code)
        )
    elif current_user.user_type in ["admin", "ro_user"]:
        return redirect(url_for("brs.brs_dashboard"))
    else:
        abort(404)
    return render_template(
        "brs_home.html",
        brs_entries=brs_entries,
        # colour_check=colour_check,
        # percent_completed=percent_completed,
    )


@brs_bp.route("/<string:ro_code>/<string:month>/", methods=["POST", "GET"])
@login_required
@ro_user_only
def brs_ro_wise(ro_code, month):
    if current_user.user_type == "admin" or (
        current_user.user_type == "ro_user" and current_user.ro_code == ro_code
    ):
        brs_entries = db.session.scalars(
            db.select(BRS).where(BRS.uiic_regional_code == ro_code, BRS.month == month)
        )
    else:
        abort(404)
    return render_template(
        "brs_home.html",
        brs_entries=brs_entries,
        #  colour_check=colour_check,
        # percent_completed=percent_completed,
    )


@brs_bp.route("/percentage", methods=["POST", "GET"])
@login_required
@admin_required
def brs_percentage():
    form = DashboardForm()

    # Dynamic month dropdown
    month_choices = db.session.scalars(db.select(BRS.month.distinct()))
    list_period = [datetime.strptime(item, "%B-%Y") for item in month_choices]
    list_period.sort(reverse=True)
    form.month.choices = ["View all"] + [item.strftime("%B-%Y") for item in list_period]

    stmt = db.select(
        BRS.uiic_regional_code,
        BRS.month,
        db.func.count(BRS.cash_bank),
        db.func.count(BRS.cash_brs_id),
        db.func.count(BRS.cheque_bank),
        db.func.count(BRS.cheque_brs_id),
        db.func.count(BRS.pg_bank),
        db.func.count(BRS.pg_brs_id),
        db.func.count(BRS.pos_bank),
        db.func.count(BRS.pos_brs_id),
        db.func.count(BRS.bbps_bank),
        db.func.count(BRS.bbps_brs_id),
        db.func.count(BRS.dqr_bank),
        db.func.count(BRS.dqr_brs_id),
        db.func.count(BRS.local_collection_bank),
        db.func.count(BRS.local_collection_brs_id),
    ).group_by(BRS.uiic_regional_code, BRS.month)

    if form.validate_on_submit():
        month = form.data["month"]
        if month != "View all":
            stmt = stmt.where(BRS.month == month)
    query = db.session.execute(stmt)
    return render_template("brs_dashboard_percentage.html", query=query, form=form)


@brs_bp.route("/dashboard", methods=["POST", "GET"])
@login_required
@ro_user_only
def brs_dashboard():
    form = DashboardForm()

    # Dynamic month dropdown
    month_choices = db.session.scalars(db.select(BRS.month.distinct()))
    list_period = [datetime.strptime(item, "%B-%Y") for item in month_choices]
    list_period.sort(reverse=True)
    form.month.choices = ["View all"] + [item.strftime("%B-%Y") for item in list_period]

    stmt = db.select(
        BRS.uiic_regional_code,
        BRS.month,
        db.func.count(BRS.cash_bank),
        db.func.count(BRS.cash_brs_id),
        db.func.count(BRS.cheque_bank),
        db.func.count(BRS.cheque_brs_id),
        db.func.count(BRS.pg_bank),
        db.func.count(BRS.pg_brs_id),
        db.func.count(BRS.pos_bank),
        db.func.count(BRS.pos_brs_id),
        db.func.count(BRS.bbps_bank),
        db.func.count(BRS.bbps_brs_id),
        db.func.count(BRS.dqr_bank),
        db.func.count(BRS.dqr_brs_id),
        db.func.count(BRS.local_collection_bank),
        db.func.count(BRS.local_collection_brs_id),
    ).group_by(BRS.uiic_regional_code, BRS.month)

    if current_user.user_type == "ro_user":
        stmt = stmt.where(BRS.uiic_regional_code == current_user.ro_code)

    if form.validate_on_submit():
        month = form.data["month"]
        if month != "View all":
            stmt = stmt.where(BRS.month == month)
    query = db.session.execute(stmt)
    return render_template("brs_dashboard.html", query=query, form=form)


# @brs_bp.route("/bulk_upload", methods=["POST", "GET"])
# @login_required
# @admin_required
# def bulk_upload_brs():
#     if request.method == "POST":
#         upload_file = request.files.get("file")
#         df_brs_upload = pd.read_csv(
#             upload_file, dtype={"uiic_regional_code": str, "uiic_office_code": str}
#         )
#         upload_brs_file(df_brs_upload, db.engine, current_user.username)
#         flash("BRS records have been uploaded to database.")

#     return render_template("bulk_brs_upload.html")


# add month
@brs_bp.route("/enable_delete/add", methods=["POST", "GET"])
@login_required
@admin_required
def enable_month_deletion():
    form = EnableDeleteMonthForm()

    if form.validate_on_submit():
        delete_entries = DeleteEntries(
            txt_month=form.data["txt_month"],
            bool_enable_delete=form.data["bool_enable_delete"],
        )
        db.session.add(delete_entries)
        db.session.commit()
    return render_template("enable_month_delete.html", form=form)


# edit month
@brs_bp.route("/enable_delete/edit/<int:month_id>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_month_deletion(month_id):
    delete_entries = db.get_or_404(DeleteEntries, month_id)
    form = EnableDeleteMonthForm(obj=delete_entries)

    if form.validate_on_submit():
        delete_entries.bool_enable_delete = form.data["bool_enable_delete"]
        db.session.commit()
    return render_template("enable_month_delete.html", form=form)


# list months
@brs_bp.route("/enable_delete/list")
@login_required
@admin_required
def list_month_deletions():
    list = db.session.scalars(db.select(DeleteEntries).order_by(DeleteEntries.id))
    column_names = [col.name for col in DeleteEntries.__table__.columns]

    return render_template(
        "list_months_delete.html", list=list, column_names=column_names
    )


@brs_bp.route("/upload_brs/<int:brs_key>/", methods=["POST", "GET"])
@login_required
def upload_brs(brs_key):
    # Fetch the BRS entry and list of months where deletion is enabled
    brs_entry = db.get_or_404(BRS, brs_key)
    brs_entry.require_access(current_user)

    month_string = brs_entry.month

    enable_delete = db.session.scalar(
        db.select(DeleteEntries.bool_enable_delete).where(
            DeleteEntries.txt_month == month_string
        )
    )

    roles_allowed_to_delete = ["admin", "ro_user"] if enable_delete else []

    # Initialize form and handle submission
    form = BRSForm()
    if form.validate_on_submit():
        delete_fields = [f for f in form.data if f not in ("csrf_token", "submit")]
        for brs_type in delete_fields:
            if form.data[brs_type]:
                month_id = brs_entry.get_brs_id(brs_type)
                if month_id:
                    brs_month = db.get_or_404(BRSMonth, month_id)
                    brs_month.status = "Deleted"
                    brs_entry.set_brs_id(brs_type, None)

        db.session.commit()
        flash("BRS entry has been deleted.")
        return redirect(url_for("brs.upload_brs", brs_key=brs_key))

    return render_template(
        "open_brs.html",
        brs_entry=brs_entry,
        form=form,
        list_delete_brs=roles_allowed_to_delete,
    )


@brs_bp.route("/view_consolidated/<int:brs_key>/<string:display>/")
@login_required
def view_consolidated_brs(brs_key, display):
    brs_entry = db.get_or_404(BRS, brs_key)
    brs_entry.require_access(current_user)

    # Collect brs_type → brs_id using model method
    brs_ids = {
        brs_type: brs_entry.get_brs_id(brs_type)
        for brs_type in brs_entry.brs_field_list()
    }

    # Filter out None values
    valid_ids = [i for i in brs_ids.values() if i]

    # Bulk load all BRSMonth rows into a dict
    query = db.session.scalars(
        db.select(BRSMonth).where(BRSMonth.id.in_(valid_ids))
    ).all()
    brs_data = {brs_month.brs_type: brs_month for brs_month in query}

    html = render_template(
        "view_consolidated_brs.html",
        **brs_data,
        brs_month=brs_entry,
        display=display,
    )
    if display == "html":
        return html
    elif display == "pdf":
        return render_pdf(HTML(string=html))


@brs_bp.route("/download_format/<string:requirement>/")
@login_required
def download_format(requirement):
    if requirement == "cash":
        return send_file("download_formats/outstanding_cash_upload_format.csv")
    else:
        return send_file("download_formats/outstanding_cheques_upload_format.csv")


@brs_bp.route("/view/<int:brs_key>/", defaults={"display": "html"})
@brs_bp.route("/view/<int:brs_key>/<string:display>/")
@login_required
def view_brs(brs_key, display):
    brs_entry = db.get_or_404(BRSMonth, brs_key)
    brs_entry.brs.require_access(current_user)

    html = render_template(
        "view_brs_entry.html",
        brs_entry=brs_entry,
        # get_brs_bank=get_brs_bank,
        display=display,
    )
    if display == "html":
        return html
    elif display == "pdf":
        return render_pdf(HTML(string=html))


def get_prev_month_amount(requirement: str, brs_id: int):
    brs_entry = db.get_or_404(BRS, brs_id)

    prev_month = datetime.strptime(brs_entry.month, "%B-%Y") - relativedelta(months=1)
    prev_month_str = prev_month.strftime("%B-%Y")

    prev_brs_entry = db.session.scalar(
        db.select(BRS).where(
            BRS.uiic_office_code == brs_entry.uiic_office_code,
            BRS.month == prev_month_str,
        )
    )
    if not prev_brs_entry:
        return 0, 0

    # attr_map = {
    #     "cash": "cash_brs_id",
    #     "cheque": "cheque_brs_id",
    #     "pg": "pg_brs_id",
    #     "pos": "pos_brs_id",
    #     "bbps": "bbps_brs_id",
    #     "dqr": "dqr_brs_id",
    #     "local_collection": "local_collection_brs_id",
    # }
    # field_name = attr_map.get(requirement)

    #    brs_entry_id = getattr(prev_brs_entry, field_name, None)
    brs_entry_id = prev_brs_entry.get_brs_id(requirement)

    if not brs_entry_id:
        return 0, 0

    prev_brs = db.get_or_404(BRSMonth, brs_entry_id)
    return prev_brs.int_closing_balance, prev_brs.int_closing_on_hand


def prevent_duplicate_brs(brs_type: str, brs_id: int) -> bool:
    """Check if BRS already exists for given BRS type and BRS ID."""
    brs_entry = db.get_or_404(BRS, brs_id)

    return bool(brs_entry.get_brs_id(brs_type))

    # mapping = {
    #     "cash": brs_entry.cash_brs_id,
    #     "cheque": brs_entry.cheque_brs_id,
    #     "pg": brs_entry.pg_brs_id,
    #     "pos": brs_entry.pos_brs_id,
    #     "bbps": brs_entry.bbps_brs_id,
    #     "dqr": brs_entry.dqr_brs_id,
    #     "local_collection": brs_entry.local_collection_brs_id,
    # }

    # return bool(mapping.get(brs_type))


# def update_brs_id(brs_type: str, brs_entry: BRS, brs_id: int) -> None:
#     """Update the BRS ID on brs_entry based on requirement."""
#     field_map = {
#         "cash": "cash_brs_id",
#         "cheque": "cheque_brs_id",
#         "pg": "pg_brs_id",
#         "pos": "pos_brs_id",
#         "bbps": "bbps_brs_id",
#         "dqr": "dqr_brs_id",
#         "local_collection": "local_collection_brs_id",
#     }
#     field_name = field_map.get(brs_type)
#     if field_name:
#         setattr(brs_entry, field_name, brs_id)


def upload_df_entries(file, brs_type, table_name, brs_id):
    # Reset file pointer
    file.stream.seek(0)

    if brs_type == "cash":
        required_columns = ["instrument_amount", "date_of_collection"]
    else:
        required_columns = [
            "instrument_number",
            "instrument_amount",
            "date_of_instrument",
            "date_of_collection",
        ]

    optional_columns = ["remarks"]

    df = pd.read_csv(file, dtype={"instrument_number": str})
    # Add missing optional columns as empty
    for col in optional_columns:
        if col not in df.columns:
            df[col] = ""

    # Keep only required + optional columns in desired order
    df = df[required_columns + optional_columns]

    # Convert date columns
    date_columns = ["date_of_instrument", "date_of_collection"]
    for date_col in date_columns:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(
                df[date_col], errors="coerce", format="%d/%m/%Y"
            )

    # Convert string columns
    str_columns = ["instrument_number", "remarks"]
    for str_col in str_columns:
        if str_col in df.columns:
            df[str_col] = df[str_col].astype(str)

    # Drop invalid rows
    df = df.dropna(subset=["instrument_amount"])

    # Map table_name → ORM class
    model_map = {
        "outstanding": Outstanding,
        "bank_recon_short_credit": BankReconShortCredit,
        "bank_recon_excess_credit": BankReconExcessCredit,
    }

    ModelClass = model_map.get(table_name)
    if not ModelClass:
        raise ValueError(f"Unknown table name: {table_name}")

    # Convert DataFrame to list of dicts
    rows = df.to_dict(orient="records")

    # Create ORM objects
    objects = [
        ModelClass(
            instrument_number=row.get("instrument_number"),
            instrument_amount=row.get("instrument_amount"),
            date_of_instrument=row.get("date_of_instrument"),
            date_of_collection=row.get("date_of_collection"),
            remarks=row.get("remarks"),
            brs_month_id=brs_id,
        )
        for row in rows
    ]

    # Bulk insert
    db.session.add_all(objects)


@brs_bp.route("/<int:brs_id>/<string:requirement>/add_brs", methods=["POST", "GET"])
@login_required
def enter_brs(requirement, brs_id):
    brs_entry = db.get_or_404(BRS, brs_id)
    brs_entry.require_access(current_user)

    brs_month = datetime.strptime(brs_entry.month, "%B-%Y") + relativedelta(
        months=1, day=1
    )

    form = BRSEntryForm()
    form.date_of_month.data = brs_month
    form.brs_type.data = requirement

    if prevent_duplicate_brs(requirement, brs_id):
        flash("BRS has already been submitted.")
    elif form.validate_on_submit():
        brs = BRSMonth(brs_id=brs_id)
        form.populate_obj(brs)

        db.session.add(brs)
        db.session.flush()

        try:
            # Upload related entries only if closing balance is non-zero
            if brs.int_closing_balance != 0:
                upload_map = [
                    (
                        "int_deposited_not_credited",
                        "file_outstanding_entries",
                        "outstanding",
                    ),
                    (
                        "int_short_credited",
                        "file_short_credit_entries",
                        "bank_recon_short_credit",
                    ),
                    (
                        "int_excess_credited",
                        "file_excess_credit_entries",
                        "bank_recon_excess_credit",
                    ),
                ]
                for amount_field, file_field, table_name in upload_map:
                    if getattr(brs, amount_field, 0) > 0:
                        upload_df_entries(
                            form.data.get(file_field), requirement, table_name, brs.id
                        )

            # update_brs_id(requirement, brs_entry, brs.id)
            brs_entry.set_brs_id(requirement, brs.id)
            db.session.commit()

            return redirect(url_for("brs.upload_brs", brs_key=brs_id))

        except sqlalchemy.exc.DataError:
            db.session.rollback()
            flash(
                "Please ensure dates are entered in dd/mm/yyyy format and amount in integer format."
            )

    prev_month_opening_balance, prev_month_opening_on_hand = get_prev_month_amount(
        requirement, brs_id
    )
    form.int_opening_balance.data = prev_month_opening_balance
    form.int_opening_on_hand.data = prev_month_opening_on_hand

    return render_template(
        "add_brs_entry.html",
        form=form,
        brs_entry=brs_entry,
        requirement=requirement,
        # get_brs_bank=get_brs_bank,
        prevent_duplicate_brs=prevent_duplicate_brs,
    )


@brs_bp.route("/dashboard/view_raw_data", methods=["GET", "POST"])
@login_required
@ro_user_only
def list_brs_entries():
    """Function to return genuine BRS entries to be considered for passing JV
    a. Entries which are not deleted AND
    b. Entries which have no closing balance AND
    c. Entries which have closing balance and corresponding outstanding/short_credit/excess_credit entries.
    """
    form = RawDataForm()

    month_choices = db.session.scalars(db.select(BRS.month).distinct())

    list_period = [datetime.strptime(item, "%B-%Y") for item in month_choices]

    # sorting the items of list_period in reverse order
    # newer months will be above
    list_period.sort(reverse=True)
    # list_period is now dynamically added as dropdown choice list to the SelectField
    form.month.choices = [item.strftime("%B-%Y") for item in list_period]

    if form.validate_on_submit():
        month = form.data["month"]
        brs_type = form.data["brs_type"]

        stmt = (
            db.select(BRSMonth)
            .options(joinedload(BRSMonth.brs))
            .join(BRS, BRS.id == BRSMonth.brs_id)
            .where((BRSMonth.status.is_(None)), (BRS.month == month))
        )

        if brs_type != "View all":
            stmt = stmt.where(BRSMonth.brs_type == brs_type)

        subquery_os = db.select(Outstanding.brs_month_id).distinct()
        subquery_excess = db.select(BankReconExcessCredit.brs_month_id).distinct()
        subquery_short = db.select(BankReconShortCredit.brs_month_id).distinct()

        unioned_ids = db.union_all(
            subquery_os, subquery_excess, subquery_short
        ).subquery()

        stmt = stmt.where(
            (BRSMonth.int_closing_balance == 0)
            | (
                (BRSMonth.int_closing_balance != 0)
                & BRSMonth.id.in_(db.select(unioned_ids.c.brs_month_id))
            )
        )

        if current_user.user_type == "ro_user":
            stmt = stmt.where(BRS.uiic_regional_code == current_user.ro_code)
        results = db.session.scalars(stmt)
        return render_template(
            "view_brs_raw_data.html",
            brs_entries=results,
        )
    return render_template("brs_raw_data_form.html", form=form)


@brs_bp.route("/dashboard/view_raw_data/exceptions")
@login_required
def list_brs_entries_exceptions():
    """Function to return exceptions - BRS monthly records for the following conditions
    1. The BRS monthly record is deleted OR
    2.
        a. The BRS monthly record is not deleted AND
        b. Closing balance is not zero AND
        c. Outstanding entries are not present for the BRS monthly record."""

    subquery_os = db.select(Outstanding.brs_month_id).distinct()
    subquery_excess = db.select(BankReconExcessCredit.brs_month_id).distinct()
    subquery_short = db.select(BankReconShortCredit.brs_month_id).distinct()

    unioned_ids = db.union_all(subquery_os, subquery_excess, subquery_short).subquery()

    stmt = (
        db.select(BRSMonth)
        .options(joinedload(BRSMonth.brs))
        .join(BRS, BRS.id == BRSMonth.brs_id)
        .where(
            db.or_(
                BRSMonth.status == "Deleted",
                db.and_(
                    (BRSMonth.int_closing_balance - BRSMonth.int_balance_as_per_bank)
                    != 0,
                    BRSMonth.id.not_in(db.select(unioned_ids.c.brs_month_id)),
                ),
            )
        )
    )
    query = db.session.scalars(stmt)

    return render_template(
        "view_brs_raw_data.html",
        brs_entries=query,
    )


@brs_bp.route("/dashboard/<string:entry_type>/", methods=["GET", "POST"])
@login_required
@ro_user_only
def list_brs_items(entry_type):
    form = RawDataForm()

    # Dynamic month dropdown
    month_choices = db.session.scalars(db.select(BRS.month.distinct()))
    list_period = [datetime.strptime(item, "%B-%Y") for item in month_choices]
    list_period.sort(reverse=True)
    form.month.choices = [item.strftime("%B-%Y") for item in list_period]

    # Select which model we are querying
    MODEL_MAP = {
        "outstanding": Outstanding,
        "short_credit": BankReconShortCredit,
        "excess_credit": BankReconExcessCredit,
    }

    if entry_type not in MODEL_MAP:
        abort(404)

    Model = MODEL_MAP.get(entry_type)

    if form.validate_on_submit():
        month = form.month.data
        brs_type = form.brs_type.data

        stmt = (
            db.select(Model)
            .options(joinedload(Model.brs_month).joinedload(BRSMonth.brs))
            .join(BRSMonth, BRSMonth.id == Model.brs_month_id)
            .join(BRS, BRSMonth.brs_id == BRS.id)
            .where(
                BRSMonth.status.is_(None),
                BRS.month == month,
            )
        )

        if brs_type != "View all":
            stmt = stmt.where(BRSMonth.brs_type == brs_type)

        if current_user.user_type == "ro_user":
            stmt = stmt.where(BRS.uiic_regional_code == current_user.ro_code)

        entries = db.session.scalars(stmt)

        return render_template(
            "view_outstanding_entries.html",
            outstanding=entries,
            title=entry_type.replace("_", " "),
        )

    return render_template("brs_raw_data_form.html", form=form)


# def get_brs_bank(brs_id, brs_type):
#     brs_entry = db.get_or_404(BRS, brs_id)

#     return brs_entry.get_bank_for_type(brs_type)
#     # bank_mapping = {
#     #     "cash": brs_entry.cash_bank,
#     #     "cheque": brs_entry.cheque_bank,
#     #     "pos": brs_entry.pos_bank,
#     #     "pg": brs_entry.pg_bank,
#     #     "bbps": brs_entry.bbps_bank,
#     #     "dqr": brs_entry.dqr_bank,
#     #     "local_collection": brs_entry.local_collection_bank,
#     # }
#     # return bank_mapping.get(brs_type)


def get_bank_account_detail(requirement: str, bank_name: str) -> str:
    bank = db.session.scalar(
        db.select(BankReconAccountDetails).where(
            BankReconAccountDetails.str_brs_type == requirement,
            BankReconAccountDetails.str_name_of_bank == bank_name,
        )
    )

    return bank.str_bank_account_number, bank.str_ifsc_code


@brs_bp.route("/api/v1/brs/<string:office_code>/<string:month>/")
def get_schedule_bbc_updated(office_code: str, month: str) -> dict:
    """Sample URL: http://0.0.0.0:8080/brs/api/v1/brs/500200/January-2024/
    Function for entering BBC schedule in E formats
    Input: Office code and month
    Output: dictionary containing office code, month, each BRS type,
    name of bank, ifsc code, account number, closing balance and bank balance
    """
    # TODO: Candidate for refactoring

    filtered_brs = BRS.query.filter(
        (BRS.uiic_office_code == office_code) & (BRS.month == month)
    ).first()

    # return all existing brs types for the office code
    # if brs type exists, return bank name
    # and closing balance
    json_dict = {f"{office_code}": {"month": month}}
    if not filtered_brs:
        return json_dict
    brs_types = {
        "cash": (filtered_brs.cash_bank, filtered_brs.cash_brs_id),
        "cheque": (filtered_brs.cheque_bank, filtered_brs.cheque_brs_id),
        "pg": (filtered_brs.pg_bank, filtered_brs.pg_brs_id),
        "bbps": (filtered_brs.bbps_bank, filtered_brs.bbps_brs_id),
        "dqr": (filtered_brs.dqr_bank, filtered_brs.dqr_brs_id),
        "pos": (filtered_brs.pos_bank, filtered_brs.pos_brs_id),
    }

    # Helper function to fetch details and update the JSON
    def add_brs_details(brs_type, bank_name, brs_id):
        if not bank_name:
            return
        account_number, ifsc_code = get_bank_account_detail(brs_type, bank_name)
        details = {
            "bank": bank_name.upper(),
            "account_number": account_number,
            "ifsc_code": ifsc_code,
        }
        if brs_id:
            brs_entry = BRSMonth.query.get(brs_id)
            details.update(
                {
                    "closing_balance": (
                        brs_entry.int_closing_balance if brs_entry else 0
                    ),
                    "bank_balance": (
                        brs_entry.int_balance_as_per_bank if brs_entry else 0
                    ),
                }
            )
        json_dict[office_code][brs_type] = details

    # Process each BRS type
    for brs_type, (bank_name, brs_id) in brs_types.items():
        add_brs_details(brs_type, bank_name, brs_id)

    return json_dict


@brs_bp.route("/api/v2/brs/<string:office_code>/<string:month>/")
def get_schedule_bbc_updated_v2(office_code: str, month: str) -> dict:
    """Sample URL: http://0.0.0.0:8080/brs/api/v2/brs/500200/January-2024/
    Function for entering BBC schedule in E formats
    Input: Office code and month
    Output: dictionary containing office code, month, each BRS type,
    name of bank, ifsc code, account number, closing balance and bank balance
    """

    filtered_brs = db.session.scalar(
        db.select(BRS).where(BRS.uiic_office_code == office_code, BRS.month == month)
    )
    if not filtered_brs:
        return {office_code: {"month": month}}

    bank_name_case = db.case(
        (BRSMonth.brs_type == "cash", BRS.cash_bank),
        (BRSMonth.brs_type == "cheque", BRS.cheque_bank),
        (BRSMonth.brs_type == "pos", BRS.pos_bank),
        (BRSMonth.brs_type == "pg", BRS.pg_bank),
        (BRSMonth.brs_type == "bbps", BRS.bbps_bank),
        (BRSMonth.brs_type == "dqr", BRS.dqr_bank),
        else_="",
    ).label("bank_name")

    brs_amount = (
        db.select(
            BRSMonth.brs_type,
            BRSMonth.int_closing_balance.label("closing_balance"),
            BRSMonth.int_balance_as_per_bank.label("bank_balance"),
            db.func.upper(bank_name_case).label("bank"),
            BankReconAccountDetails.str_bank_account_number.label("account_number"),
            BankReconAccountDetails.str_ifsc_code.label("ifsc_code"),
        )
        .join(BRS, BRS.id == BRSMonth.brs_id)
        .join(
            BankReconAccountDetails,
            db.and_(
                BankReconAccountDetails.str_brs_type == BRSMonth.brs_type,
                BankReconAccountDetails.str_name_of_bank == bank_name_case,
            ),
            isouter=True,
        )
        .where(
            BRSMonth.brs_id == filtered_brs.id, BRSMonth.brs_type != "local_collection"
        )
    )

    result = db.session.execute(brs_amount).mappings()

    data = {
        entry.brs_type: {k: v for k, v in dict(entry).items() if k != "brs_type"}
        for entry in result
    }
    response = {office_code: {"month": month, **data}}

    return response


@brs_bp.route("/api/v1/brs/get_percent_complete/<string:regional_office_code>/")
def get_percent_completion(regional_office_code):
    """for e-formats checklist of BRS completion
    returns percentage completion if regional office code is entered"""

    stmt = get_percentages(regional_office_code)
    subq = stmt.subquery()
    percentage = db.session.scalar(db.select(subq.c.percent_complete))
    return str(percentage)


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
    stmt = get_percentages(ro_list)
    query = db.session.execute(stmt)
    return render_template(
        "brs_dashboard_percentage_list.html",
        percentages=query,
    )


def get_percentages(ro_codes):
    """Return {regional_code: percent_complete} for one or many RO codes."""
    if isinstance(ro_codes, str):
        ro_codes = [ro_codes]  # normalize to list

    stmt = (
        db.select(
            BRS.uiic_regional_code,
            db.func.coalesce(
                db.func.round(
                    (
                        (
                            db.func.count(BRS.cash_brs_id)
                            + db.func.count(BRS.cheque_brs_id)
                            + db.func.count(BRS.pg_brs_id)
                            + db.func.count(BRS.pos_brs_id)
                            + db.func.count(BRS.bbps_brs_id)
                            + db.func.count(BRS.dqr_brs_id)
                            + db.func.count(BRS.local_collection_brs_id)
                        )
                        / (
                            db.func.count(BRS.cash_bank)
                            + db.func.count(BRS.cheque_bank)
                            + db.func.count(BRS.pg_bank)
                            + db.func.count(BRS.pos_bank)
                            + db.func.count(BRS.bbps_bank)
                            + db.func.count(BRS.dqr_bank)
                            + db.func.count(BRS.local_collection_bank)
                        )
                    )
                    * 100,
                    2,
                ),
                0,
            ).label("percent_complete"),
        )
        .where(BRS.financial_year != "23-24")
        .where(BRS.uiic_regional_code.in_(ro_codes))
        .group_by(BRS.uiic_regional_code)
        .order_by(BRS.uiic_regional_code)
    )

    return stmt


@brs_bp.route("/bank_accounts/add", methods=["POST", "GET"])
@login_required
@admin_required
def add_bank_account():
    """Add new bank account through model form"""
    bank_account = BankReconAccountDetails()

    if request.method == "POST":
        form = BankReconAccountDetailsAddForm(request.form, obj=bank_account)
        if form.validate():
            form.populate_obj(bank_account)
            db.session.add(bank_account)
            db.session.commit()

            flash("Bank account details have been successfully added.")
    else:
        form = BankReconAccountDetailsAddForm()

    return render_template(
        "brs_bank_account_add.html",
        form=form,
    )
