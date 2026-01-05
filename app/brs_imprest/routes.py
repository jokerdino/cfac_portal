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

from . import brs_imprest_bp
from .forms import (
    BankReconEntryForm,
    BankReconDeleteForm,
    AddBankReconImprestSummaryForm,
    MonthFilterForm,
    FileUploadForm,
)
from .models import (
    BankReconImprestSummary,
    BankReconImprestDetails,
    BankReconImprestUnencashedDetails,
)

from app.brs.models import DeleteEntries

VIEW_ALL = "View all"


@brs_imprest_bp.route("/add", methods=["POST", "GET"])
@login_required
@admin_required
def add_brs_details_item():
    form = AddBankReconImprestSummaryForm()
    if form.validate_on_submit():
        brs = BankReconImprestSummary()
        form.populate_obj(brs)
        db.session.add(brs)
        db.session.commit()
        flash("BRS details for imprest successfully added.")

    return render_template(
        "brs_imprest_form.html", form=form, title="Add BRS imprest details item"
    )


def populate_month_choices(form, Summary, view_all=True):
    subq = (
        db.select(
            Summary.month,
            db.func.to_date(Summary.month, "Month-YYYY").label("month_date"),
        )
        .distinct(Summary.month)
        .subquery()
    )

    month_choices = db.session.scalars(
        db.select(subq.c.month).order_by(subq.c.month_date.desc())
    ).all()

    if view_all:
        form.month.choices = [VIEW_ALL] + month_choices
    else:
        form.month.choices = month_choices


def get_admin_ro_query(form, Summary):
    query = db.select(
        Summary.regional_office,
        Summary.month,
        db.func.count(Summary.imprest_bank_name),
        db.func.count(Summary.imprest_brs_month_id),
    ).group_by(
        Summary.regional_office,
        Summary.month,
    )

    if current_user.user_type == "ro_user":
        query = query.where(Summary.regional_office == current_user.ro_code)
    if form.validate_on_submit():
        month = form.month.data
        if month != VIEW_ALL:
            query = query.where(Summary.month == month)
    return query


@brs_imprest_bp.route("/", methods=["POST", "GET"])
@login_required
def brs_imprest_dashboard():
    user_type = current_user.user_type
    Summary = aliased(BankReconImprestSummary)

    if user_type not in {"admin", "ro_user", "oo_user"}:
        abort(403)
    if user_type in {"admin", "ro_user"}:
        form = MonthFilterForm()
        populate_month_choices(form, Summary)
        query = get_admin_ro_query(form, Summary)

        result = db.session.execute(query)
        return render_template("brs_imprest_dashboard.html", query=result, form=form)

    oo_code = current_user.oo_code
    query = db.session.scalars(
        db.select(Summary)
        .where(
            Summary.operating_office == oo_code,
        )
        .order_by(Summary.operating_office)
    )
    return render_template("brs_imprest_homepage.html", query=query)


@brs_imprest_bp.route("/<string:month>/<string:ro_code>/")
@login_required
def brs_imprest_homepage(month, ro_code):
    if current_user.user_type == "ro_user":
        ro_code = current_user.ro_code
    query = db.session.scalars(
        db.select(BankReconImprestSummary)
        .where(
            BankReconImprestSummary.regional_office == ro_code,
            BankReconImprestSummary.month == month,
        )
        .order_by(BankReconImprestSummary.operating_office)
    )
    return render_template("brs_imprest_homepage.html", query=query)


@brs_imprest_bp.route("/view/<int:key>/", methods=["GET", "POST"])
@login_required
def brs_imprest_view_status(key):
    brs = db.get_or_404(BankReconImprestSummary, key)
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
        return redirect(url_for(".brs_imprest_view_status", key=key))

    return render_template(
        "brs_imprest_view_status.html",
        brs=brs,
        form=form,
        delete_button=enable_delete,
    )


@brs_imprest_bp.route("/view/brs/<int:brs_key>/")
@login_required
def view_brs(brs_key):
    brs_entry = db.get_or_404(BankReconImprestDetails, brs_key)
    brs_entry.summary.require_access(current_user)

    gl_column_labels = {
        "opening_balance": (
            "Opening balance as per GL",
            datetime_format(brs_entry.summary.month, "%B-%Y", "previous"),
            True,
        ),
        "fund_transfer": (
            "Add: Fund transfer",
            datetime_format(brs_entry.summary.month, "%B-%Y", "previous"),
            False,
        ),
        "cheques_issued": (
            "Less: Cheques issued during the month",
            brs_entry.summary.month,
            False,
        ),
        "cheques_cancelled": (
            "Add: Cancellations during the month",
            brs_entry.summary.month,
            False,
        ),
        "bank_charges": ("Less: Bank charges", brs_entry.summary.month, False),
        "closing_balance_gl": (
            "Closing balance as per GL",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            True,
        ),
    }
    bank_recon_column_labels = {
        "closing_balance_gl": (
            "Closing balance as per GL",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            True,
        ),
        "cheques_unencashed": (
            "Add: Unencashed cheques",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            False,
        ),
        "closing_balance_bank": (
            "Closing balance as per bank statement",
            datetime_format(brs_entry.summary.month, "%B-%Y", "current"),
            True,
        ),
    }

    return render_template(
        "brs_imprest_view_brs_entry.html",
        brs_entry=brs_entry,
        gl_column_labels=gl_column_labels,
        bank_recon_column_labels=bank_recon_column_labels,
    )


def upload_document_to_folder(
    brs_imprest_obj, model_attribute, form, field, folder_name
):
    base_path = Path(current_app.config.get("UPLOAD_FOLDER"))
    folder_path = base_path / "brs_imprest" / folder_name

    # Create folders if missing
    folder_path.mkdir(parents=True, exist_ok=True)

    # Check if file exists in the form
    if form.data[field]:
        filename = secure_filename(form.data[field].filename)

        file_extension = filename.rsplit(".", 1)[1]
        document_filename = (
            f"{folder_name}_{datetime.now().strftime('%d%m%Y %H%M%S')}.{file_extension}"
        )

        # Path to final file
        file_path = folder_path / document_filename

        # Save file
        form.data[field].save(file_path)

        # Assign filename to model attribute
        setattr(brs_imprest_obj, model_attribute, document_filename)


@brs_imprest_bp.route("/download/<int:id>/")
@login_required
def download_bank_statement(id):
    brs_imprest = db.get_or_404(BankReconImprestDetails, id)
    base_path = Path(current_app.config.get("UPLOAD_FOLDER"))
    folder_path = base_path / "brs_imprest" / "brs_imprest_bank_statement"

    filename = brs_imprest.bank_statement

    file_path = folder_path / filename
    if not file_path.exists():
        abort(404)

    file_extension = filename.rsplit(".", 1)[-1]
    download_name = f"bank_statement_{brs_imprest.summary.operating_office}_{brs_imprest.summary.imprest_bank_name}_{brs_imprest.summary.imprest_bank_account_number}_{brs_imprest.summary.month}.{file_extension}"
    return send_from_directory(
        directory=str(folder_path),
        path=filename,
        as_attachment=True,
        download_name=download_name,
    )


@brs_imprest_bp.route("/<int:key>/add/", methods=["POST", "GET"])
@login_required
def brs_imprest_data_entry(key):
    brs = db.get_or_404(BankReconImprestSummary, key)
    brs.require_access(current_user)
    last_date_of_month = datetime.strptime(brs.month, "%B-%Y") + relativedelta(
        months=1, day=1
    )

    form = BankReconEntryForm(obj=brs)
    form.last_date_of_month.data = last_date_of_month

    if form.validate_on_submit():
        brs_entry = BankReconImprestDetails()
        form.populate_obj(brs_entry)
        brs_entry.summary_id = brs.id
        db.session.add(brs_entry)
        db.session.commit()
        brs.imprest_brs_month_id = brs_entry.id
        upload_document_to_folder(
            brs_entry,
            "bank_statement",
            form,
            "file_bank_statement",
            "brs_imprest_bank_statement",
        )
        db.session.commit()

        # Upload unencashed cheques
        process_cheque_file(
            form.data.get("file_unencashed_entries"),
            "bank_recon_imprest_unencashed_details",
            brs_entry.id,
        )

        return redirect(url_for(".view_brs", brs_key=brs_entry.id))

    opening_balance = get_prev_month_closing_balance(brs.id)
    form.opening_balance.data = opening_balance

    return render_template("brs_imprest_data_entry.html", brs_entry=brs, form=form)


def process_cheque_file(file, table_name, brs_entry_id):
    if not file:
        return

    required_columns = [
        "voucher_number",
        "voucher_date",
        "payee_name",
        "instrument_date",
        "instrument_amount",
        "instrument_number",
        "remarks",
    ]
    str_columns = ["instrument_number", "remarks", "voucher_number", "payee_name"]
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
    df["brs_details_id"] = brs_entry_id

    # Save to database
    df.to_sql(table_name, db.engine, if_exists="append", index=False)


def get_prev_month_closing_balance(brs_id):
    Details = aliased(BankReconImprestDetails)
    Summary = aliased(BankReconImprestSummary)
    brs_summary = db.get_or_404(BankReconImprestSummary, brs_id)

    # need to be rectified
    # previous_month = brs_summary.month.replace(day=1) - timedelta(days=1)

    prev_month = datetime.strptime(brs_summary.month, "%B-%Y") - relativedelta(months=1)
    prev_month_str = prev_month.strftime("%B-%Y")

    previous_month_brs = db.session.scalar(
        db.select(Details).where(
            Details.summary_id == Summary.id,
            Summary.operating_office == brs_summary.operating_office,
            Summary.month == prev_month_str,
            Summary.imprest_bank_account_number
            == brs_summary.imprest_bank_account_number,
        )
    )
    if previous_month_brs:
        return previous_month_brs.closing_balance_gl
    else:
        return 0


@brs_imprest_bp.route("/upload_previous_month/")
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

    Summary = aliased(BankReconImprestSummary)
    stmt = db.select(
        Summary.regional_office,
        Summary.operating_office,
        db.literal(current_month_string),
        Summary.purpose_of_bank_account,
        Summary.imprest_bank_name,
        Summary.imprest_bank_branch_name,
        Summary.imprest_bank_branch_location,
        Summary.imprest_bank_account_type,
        Summary.imprest_bank_account_number,
        Summary.imprest_bank_ifsc_code,
    ).where(Summary.month == prev_month.strftime("%B-%Y"))

    insert_stmt = db.insert(Summary).from_select(
        [
            Summary.regional_office,
            Summary.operating_office,
            Summary.month,
            Summary.purpose_of_bank_account,
            Summary.imprest_bank_name,
            Summary.imprest_bank_branch_name,
            Summary.imprest_bank_branch_location,
            Summary.imprest_bank_account_type,
            Summary.imprest_bank_account_number,
            Summary.imprest_bank_ifsc_code,
        ],
        stmt,
    )
    db.session.execute(insert_stmt)

    db.session.commit()

    return "Success"


@brs_imprest_bp.route("/bulk_upload", methods=["POST", "GET"])
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
            "bank_recon_imprest_summary",
            db.engine,
            if_exists="append",
            index=False,
        )
        flash("BRS imprest records have been uploaded to database")

    return render_template(
        "brs_imprest_form.html", form=form, title="Bulk upload imprest accounts"
    )


@brs_imprest_bp.route("/download_format/")
@login_required
def download_format():
    return send_file("download_formats/brs_imprest_upload_format.xlsx")


@brs_imprest_bp.route("/data/<string:entry_type>/", methods=["GET", "POST"])
@login_required
@ro_user_only
def list_brs_items(entry_type):
    form = MonthFilterForm()

    populate_month_choices(form, BankReconImprestSummary, view_all=False)

    # Select which model we are querying
    MODEL_MAP = {
        "unencashed": BankReconImprestUnencashedDetails,
    }

    if entry_type not in MODEL_MAP:
        abort(404)

    Model = MODEL_MAP.get(entry_type)

    if form.validate_on_submit():
        month = form.month.data

        stmt = (
            db.select(Model)
            .options(
                joinedload(Model.details).joinedload(BankReconImprestDetails.summary)
            )
            .join(
                BankReconImprestDetails,
                BankReconImprestDetails.id == Model.brs_details_id,
            )
            .join(
                BankReconImprestSummary,
                BankReconImprestDetails.summary_id == BankReconImprestSummary.id,
            )
            .where(
                BankReconImprestDetails.status == "Active",
                BankReconImprestSummary.month == month,
            )
        )

        if current_user.user_type == "ro_user":
            stmt = stmt.where(
                BankReconImprestSummary.regional_office == current_user.ro_code
            )

        entries = db.session.scalars(stmt)

        return render_template(
            "brs_imprest_entries.html",
            result=entries,
            title=entry_type.replace("_", " "),
        )

    title = f"Fetch {entry_type.replace('_', ' ')} entries"
    return render_template("brs_imprest_form.html", form=form, title=title)


@brs_imprest_bp.route("/data/view_raw_data", methods=["GET", "POST"])
@login_required
@ro_user_only
def list_brs_entries():
    form = MonthFilterForm()

    populate_month_choices(form, BankReconImprestSummary, view_all=False)

    if form.validate_on_submit():
        month = form.data["month"]

        stmt = (
            db.select(BankReconImprestDetails)
            .options(joinedload(BankReconImprestDetails.summary))
            .join(
                BankReconImprestSummary,
                BankReconImprestSummary.id == BankReconImprestDetails.summary_id,
            )
            .where(
                (BankReconImprestDetails.status == "Active"),
                (BankReconImprestSummary.month == month),
            )
        )

        if current_user.user_type == "ro_user":
            stmt = stmt.where(
                BankReconImprestSummary.regional_office == current_user.ro_code
            )
        results = db.session.scalars(stmt)
        return render_template(
            "brs_imprest_data.html",
            brs_entries=results,
        )
    return render_template(
        "brs_imprest_form.html", form=form, title="Fetch BRS - imprest data"
    )


@brs_imprest_bp.route("/api/v1/<string:office_code>/<string:month>/")
def get_schedule_bbi(office_code: str, month: str) -> dict:
    Details = aliased(BankReconImprestDetails)
    Summary = aliased(BankReconImprestSummary)
    filtered_brs = (
        db.select(
            Summary.operating_office.label("office_code"),
            Summary.imprest_bank_name.label("bank_name"),
            Summary.imprest_bank_branch_location.label("bank_branch_location"),
            Summary.imprest_bank_account_number.label("account_number"),
            Summary.imprest_bank_ifsc_code.label("ifsc_code"),
            Summary.purpose_of_bank_account.label("nature_of_account"),
            Details.closing_balance_bank.label("balance_as_per_bank"),
            Details.closing_balance_gl.label("balance_as_per_book"),
            Details.remarks,
        )
        .join(Details, Details.summary_id == Summary.id)
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
