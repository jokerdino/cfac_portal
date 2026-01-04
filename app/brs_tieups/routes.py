from datetime import date, datetime
from pathlib import Path

from dateutil.relativedelta import relativedelta

import pandas as pd
from flask import (
    abort,
    flash,
    redirect,
    render_template,
    url_for,
    send_file,
    send_from_directory,
    current_app,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload, aliased

from set_view_permissions import admin_required, ro_user_only
from extensions import db
from utils import datetime_format

from . import brs_tieups_bp
from .forms import (
    BankReconEntryForm,
    BankReconDeleteForm,
    AddBankReconTieupSummaryForm,
    MonthFilterForm,
    FileUploadForm,
)
from .models import (
    BankReconTieupSummary,
    BankReconTieupDetails,
    BankReconTieupOutstanding,
    BankReconTieupShortCredit,
    BankReconTieupExcessCredit,
)

from app.brs.models import DeleteEntries

VIEW_ALL = "View all"


@brs_tieups_bp.route("/add", methods=["POST", "GET"])
@login_required
@admin_required
def add_brs_details_item():
    form = AddBankReconTieupSummaryForm()
    if form.validate_on_submit():
        brs = BankReconTieupSummary()
        form.populate_obj(brs)
        db.session.add(brs)
        db.session.commit()
        flash("BRS details for tieup successfully added.")

    return render_template(
        "brs_tieup_form.html", form=form, title="Add BRS details item"
    )


def populate_month_choices(form):
    subq = (
        db.select(
            BankReconTieupSummary.month,
            db.func.to_date(BankReconTieupSummary.month, "Month-YYYY").label(
                "month_date"
            ),
        )
        .distinct(BankReconTieupSummary.month)
        .subquery()
    )

    month_choices = db.session.scalars(
        db.select(subq.c.month).order_by(subq.c.month_date.desc())
    ).all()

    form.month.choices = [VIEW_ALL] + month_choices


def get_admin_ro_query(form):
    query = db.select(
        BankReconTieupSummary.regional_office,
        BankReconTieupSummary.month,
        db.func.count(BankReconTieupSummary.tieup_partner_name),
        db.func.count(BankReconTieupSummary.tieup_brs_month_id),
    ).group_by(
        BankReconTieupSummary.regional_office,
        BankReconTieupSummary.month,
    )

    if current_user.user_type == "ro_user":
        query = query.where(
            BankReconTieupSummary.regional_office == current_user.ro_code
        )
    if form.validate_on_submit():
        month = form.month.data
        if month != VIEW_ALL:
            query = query.where(BankReconTieupSummary.month == month)
    return query


@brs_tieups_bp.route("/", methods=["POST", "GET"])
@login_required
def brs_tieup_dashboard():
    user_type = current_user.user_type

    if user_type not in {"admin", "ro_user", "oo_user"}:
        abort(403)
    if user_type in {"admin", "ro_user"}:
        form = MonthFilterForm()
        populate_month_choices(form)
        query = get_admin_ro_query(form)

        results = db.session.execute(query)
        return render_template("brs_tieup_dashboard.html", query=results, form=form)

    oo_code = current_user.oo_code
    results = db.session.scalars(
        db.select(BankReconTieupSummary)
        .where(
            BankReconTieupSummary.operating_office == oo_code,
        )
        .order_by(BankReconTieupSummary.operating_office)
    )
    return render_template("brs_tieup_homepage.html", query=results)


@brs_tieups_bp.route("/<string:month>/<string:ro_code>/")
@login_required
def brs_tieup_homepage(month, ro_code):
    if current_user.user_type == "ro_user":
        ro_code = current_user.ro_code
    results = db.session.scalars(
        db.select(BankReconTieupSummary)
        .where(
            BankReconTieupSummary.regional_office == ro_code,
            BankReconTieupSummary.month == month,
        )
        .order_by(BankReconTieupSummary.operating_office)
    )
    return render_template("brs_tieup_homepage.html", query=results)


@brs_tieups_bp.route("/view/<int:key>/", methods=["GET", "POST"])
@login_required
def brs_tieup_view_status(key):
    brs = db.get_or_404(BankReconTieupSummary, key)
    brs.require_access(current_user)

    check_user_role = current_user.user_type in ["admin", "ro_user"]
    delete_button: bool = db.session.scalar(
        db.select(DeleteEntries.bool_enable_delete).where(
            DeleteEntries.txt_month == brs.month
        )
    )

    enable_delete = all([check_user_role, delete_button])

    form = BankReconDeleteForm()
    if form.validate_on_submit():
        brs.mark_deleted()
        db.session.commit()
        flash("BRS entry has been deleted.")
        return redirect(url_for(".brs_tieup_view_status", key=key))

    return render_template(
        "brs_tieup_view_status.html",
        brs=brs,
        form=form,
        delete_button=enable_delete,
    )


@brs_tieups_bp.route("/view/brs/<int:brs_key>/")
@login_required
def view_brs(brs_key):
    brs_entry = db.get_or_404(BankReconTieupDetails, brs_key)
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
        "brs_tieup_view_brs_entry.html",
        brs_entry=brs_entry,
        gl_column_labels=gl_column_labels,
        bank_recon_column_labels=bank_recon_column_labels,
    )


# def upload_document_to_folder(brs_tieup_obj, model_attribute, form, field, folder_name):
#     base_path = Path(current_app.config.get("UPLOAD_FOLDER"))
#     folder_path = base_path / "brs_tieup" / folder_name

#     # Create folders if missing
#     folder_path.mkdir(parents=True, exist_ok=True)

#     # Check if file exists in the form
#     if form.data[field]:
#         filename = secure_filename(form.data[field].filename)

#         file_extension = filename.rsplit(".", 1)[1]
#         document_filename = (
#             f"{folder_name}_{datetime.now().strftime('%d%m%Y %H%M%S')}.{file_extension}"
#         )

#         # Path to final file
#         file_path = folder_path / document_filename

#         # Save file
#         form.data[field].save(file_path)

#         # Assign filename to model attribute
#         setattr(brs_tieup_obj, model_attribute, document_filename)


# @brs_tieups_bp.route("/download/<int:id>/")
# @login_required
# def download_bank_statement(id):
#     brs_tieup = db.get_or_404(BankReconTieupDetails, id)
#     base_path = Path(current_app.config.get("UPLOAD_FOLDER"))
#     folder_path = base_path / "brs_tieup" / "brs_tieup_bank_statement"

#     filename = brs_tieup.bank_statement

#     file_path = folder_path / filename
#     if not file_path.exists():
#         abort(404)

#     file_extension = filename.rsplit(".", 1)[-1]
#     download_name = f"bank_statement_{brs_tieup.summary.operating_office}_{brs_tieup.summary.tieup_bank_name}_{brs_tieup.summary.tieup_bank_account_number}_{brs_tieup.summary.month}.{file_extension}"
#     return send_from_directory(
#         directory=str(folder_path),
#         path=filename,
#         as_attachment=True,
#         download_name=download_name,
#     )


@brs_tieups_bp.route("/<int:key>/add/", methods=["POST", "GET"])
@login_required
def brs_tieup_data_entry(key):
    brs = db.get_or_404(BankReconTieupSummary, key)

    last_date_of_month = datetime.strptime(brs.month, "%B-%Y") + relativedelta(
        months=1, day=1
    )
    brs.require_access(current_user)
    form = BankReconEntryForm(obj=brs)
    form.last_date_of_month.data = last_date_of_month

    if form.validate_on_submit():
        brs_entry = BankReconTieupDetails()
        form.populate_obj(brs_entry)
        brs_entry.brs_id = brs.id
        db.session.add(brs_entry)
        db.session.commit()
        brs.tieup_brs_month_id = brs_entry.id
        # upload_document_to_folder(
        #     brs_entry,
        #     "bank_statement",
        #     form,
        #     "file_bank_statement",
        #     "brs_tieup_bank_statement",
        # )
        db.session.commit()

        # Upload outstanding cheques
        process_cheque_file(
            form.data.get("file_outstanding_entries"),
            "bank_recon_tieup_outstanding",
            brs_entry.id,
        )

        # Upload short_credit cheques
        process_cheque_file(
            form.data.get("file_short_credit_entries"),
            "bank_recon_tieup_short_credit",
            brs_entry.id,
        )

        # Upload excess_credit cheques
        process_cheque_file(
            form.data.get("file_excess_credit_entries"),
            "bank_recon_tieup_excess_credit",
            brs_entry.id,
        )

        return redirect(url_for(".view_brs", brs_key=brs_entry.id))

    opening_balance, opening_on_hand = get_prev_month_closing_balance(brs.id)
    form.opening_balance.data = opening_balance
    form.opening_on_hand.data = opening_on_hand
    return render_template("brs_tieup_data_entry.html", brs_entry=brs, form=form)


def process_cheque_file(file, table_name, brs_entry_id):
    if not file:
        return

    required_columns = [
        "instrument_number",
        "instrument_amount",
        "date_of_instrument",
        "date_of_collection",
        "remarks",
    ]
    str_columns = ["instrument_number", "remarks"]
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
    Details = aliased(BankReconTieupDetails)
    Summary = aliased(BankReconTieupSummary)
    brs_summary = db.get_or_404(BankReconTieupSummary, brs_id)

    # need to be rectified
    # previous_month = brs_summary.month.replace(day=1) - timedelta(days=1)

    prev_month = datetime.strptime(brs_summary.month, "%B-%Y") - relativedelta(months=1)
    prev_month_str = prev_month.strftime("%B-%Y")

    previous_month_brs = db.session.scalar(
        db.select(Details).where(
            Details.brs_id == Summary.id,
            Summary.operating_office == brs_summary.operating_office,
            Summary.month == prev_month_str,
            Summary.tieup_partner_name == brs_summary.tieup_partner_name,
        )
    )
    if previous_month_brs:
        return (
            previous_month_brs.closing_balance,
            previous_month_brs.closing_on_hand,
        )
    else:
        return 0, 0


@brs_tieups_bp.route("/upload_previous_month/")
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

    current_month_string = current_month.strftime("%B-%Y")

    stmt = db.select(
        BankReconTieupSummary.regional_office,
        BankReconTieupSummary.operating_office,
        db.literal(current_month_string),
        BankReconTieupSummary.tieup_partner_name,
    ).where(BankReconTieupSummary.month == prev_month.strftime("%B-%Y"))

    insert_stmt = db.insert(BankReconTieupSummary).from_select(
        [
            BankReconTieupSummary.regional_office,
            BankReconTieupSummary.operating_office,
            BankReconTieupSummary.month,
            BankReconTieupSummary.tieup_partner_name,
        ],
        stmt,
    )
    db.session.execute(insert_stmt)

    db.session.commit()

    return "Success"


@brs_tieups_bp.route("/bulk_upload", methods=["POST", "GET"])
@login_required
@admin_required
def bulk_upload_brs():
    form = FileUploadForm()
    if form.validate_on_submit():
        file = form.upload_file.data
        df = pd.read_excel(
            file, dtype={"regional_office": str, "operating_office": str}
        )
        df.to_sql(
            "bank_recon_tieup_summary",
            db.engine,
            if_exists="append",
            index=False,
        )
        flash("BRS local collection records have been uploaded to database")

    return render_template("brs_tieup_form.html", form=form)


@brs_tieups_bp.route("/download_format/")
@login_required
def download_format():
    return send_file("download_formats/brs_tieup_upload_format.xlsx")


@brs_tieups_bp.route("/data/<string:entry_type>/", methods=["GET", "POST"])
@login_required
@ro_user_only
def list_brs_items(entry_type):
    form = MonthFilterForm()

    populate_month_choices(form)
    # Select which model we are querying
    MODEL_MAP = {
        "outstanding": BankReconTieupOutstanding,
        "short_credit": BankReconTieupShortCredit,
        "excess_credit": BankReconTieupExcessCredit,
    }

    if entry_type not in MODEL_MAP:
        abort(404)

    Model = MODEL_MAP.get(entry_type)

    if form.validate_on_submit():
        month = form.month.data

        stmt = (
            db.select(Model)
            .options(
                joinedload(Model.details).joinedload(BankReconTieupDetails.summary)
            )
            .join(
                BankReconTieupDetails,
                BankReconTieupDetails.id == Model.brs_details_id,
            )
            .join(
                BankReconTieupSummary,
                BankReconTieupDetails.brs_id == BankReconTieupSummary.id,
            )
            .where(
                BankReconTieupDetails.status == "Active",
                BankReconTieupSummary.month == month,
            )
        )

        if current_user.user_type == "ro_user":
            stmt = stmt.where(
                BankReconTieupSummary.regional_office == current_user.ro_code
            )

        entries = db.session.scalars(stmt)

        return render_template(
            "brs_tieup_entries.html",
            result=entries,
            title=entry_type.replace("_", " "),
        )

    title = f"Fetch {entry_type.replace('_', ' ')} entries"
    return render_template("brs_tieup_form.html", form=form, title=title)


@brs_tieups_bp.route("/data/view_raw_data", methods=["GET", "POST"])
@login_required
@ro_user_only
def list_brs_entries():
    form = MonthFilterForm()

    populate_month_choices(form)

    if form.validate_on_submit():
        month = form.data["month"]

        stmt = (
            db.select(BankReconTieupDetails)
            .options(joinedload(BankReconTieupDetails.summary))
            .join(
                BankReconTieupSummary,
                BankReconTieupSummary.id == BankReconTieupDetails.brs_id,
            )
            .where(
                (BankReconTieupDetails.status == "Active"),
                (BankReconTieupSummary.month == month),
            )
        )

        if current_user.user_type == "ro_user":
            stmt = stmt.where(
                BankReconTieupSummary.regional_office == current_user.ro_code
            )
        results = db.session.scalars(stmt)
        return render_template(
            "brs_tieup_data.html",
            brs_entries=results,
        )
    return render_template(
        "brs_tieup_form.html", form=form, title="Fetch BRS - local collection data"
    )


@brs_tieups_bp.route("/api/v1/<string:office_code>/<string:month>/")
def get_schedule_bbc_ii(office_code: str, month: str) -> dict:
    Details = aliased(BankReconTieupDetails)
    Summary = aliased(BankReconTieupSummary)
    filtered_brs = (
        db.select(
            Summary.operating_office.label("office_code"),
            Summary.tieup_partner_name.label("tieup_name"),
            Details.balance_as_per_bank.label("balance_as_per_bank"),
            Details.closing_balance.label("balance_as_per_book"),
            Details.remarks,
        )
        .join(Details, Details.brs_id == Summary.id)
        .where(
            Summary.operating_office == office_code,
            Summary.month == month,
            Details.status == "Active",
        )
    )
    result = db.session.execute(filtered_brs).mappings()

    data = [dict(item) for item in result]

    return {
        office_code: {
            "month": month,
            "records": data,
        }
    }
