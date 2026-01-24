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

from . import brs_local_collection
from .forms import (
    BankReconEntryForm,
    BankReconDeleteForm,
    AddBankReconLocalCollectionSummaryForm,
    MonthFilterForm,
    FileUploadForm,
)
from .models import (
    BankReconLocalCollectionSummary,
    BankReconLocalCollectionDetails,
    BankReconLocalCollectionOutstanding,
    BankReconLocalCollectionShortCredit,
    BankReconLocalCollectionExcessCredit,
)

from app.brs.models import DeleteEntries

VIEW_ALL = "View all"


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
        "brs_lc_form.html", form=form, title="Add BRS local collection details item"
    )


def populate_month_choices(form, Summary):
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

    form.month.choices = [VIEW_ALL] + month_choices


def get_admin_ro_query(form, Summary):
    query = db.select(
        Summary.regional_office,
        Summary.month,
        db.func.count(Summary.local_collection_bank_name),
        db.func.count(Summary.local_collection_brs_month_id),
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


@brs_local_collection.route("/", methods=["POST", "GET"])
@login_required
def brs_local_collection_dashboard():
    user_type = current_user.user_type
    Summary = aliased(BankReconLocalCollectionSummary)

    if user_type not in {"admin", "ro_user", "oo_user"}:
        abort(403)
    if user_type in {"admin", "ro_user"}:
        form = MonthFilterForm()
        populate_month_choices(form, Summary)
        query = get_admin_ro_query(form, Summary)

        result = db.session.execute(query)
        return render_template("brs_lc_dashboard.html", query=result, form=form)

    oo_code = current_user.oo_code
    query = db.session.scalars(
        db.select(Summary)
        .where(
            Summary.operating_office == oo_code,
        )
        .order_by(Summary.operating_office)
    )
    return render_template("brs_lc_homepage.html", query=query)


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
        return redirect(url_for(".brs_lc_view_status", key=key))

    return render_template(
        "brs_lc_view_status.html",
        brs=brs,
        form=form,
        delete_button=enable_delete,
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
    )


def upload_document_to_folder(brs_lc_obj, model_attribute, form, field, folder_name):
    base_path = current_app.config.get("UPLOAD_FOLDER_PATH")
    folder_path = base_path / "brs_lc" / folder_name

    # Create folders if missing
    folder_path.mkdir(parents=True, exist_ok=True)

    # Check if file exists in the form
    file = form.data.get(field)
    if file:
        filename = secure_filename(file.filename)

        file_extension = Path(filename).suffix
        document_filename = (
            f"{folder_name}_{datetime.now().strftime('%d%m%Y %H%M%S')}{file_extension}"
        )

        # Save file
        file.save(folder_path / document_filename)

        # Assign filename to model attribute
        setattr(brs_lc_obj, model_attribute, document_filename)


@brs_local_collection.route("/download/<int:id>/")
@login_required
def download_bank_statement(id):
    brs_lc = db.get_or_404(BankReconLocalCollectionDetails, id)
    base_path = current_app.config.get("UPLOAD_FOLDER_PATH")
    folder_path = base_path / "brs_lc" / "brs_local_collection_bank_statement"

    filename = brs_lc.bank_statement

    file_path = folder_path / filename
    if not file_path.exists():
        abort(404)

    stored_path = Path(filename)
    file_extension = stored_path.suffix
    download_name = f"bank_statement_{brs_lc.summary.operating_office}_{brs_lc.summary.local_collection_bank_name}_{brs_lc.summary.local_collection_bank_account_number}_{brs_lc.summary.month}{file_extension}"
    return send_from_directory(
        directory=folder_path,
        path=stored_path.name,
        as_attachment=True,
        download_name=download_name,
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
        upload_document_to_folder(
            brs_entry,
            "bank_statement",
            form,
            "file_bank_statement",
            "brs_local_collection_bank_statement",
        )
        db.session.commit()

        # Upload outstanding cheques
        process_cheque_file(
            form.data.get("file_outstanding_entries"),
            BankReconLocalCollectionOutstanding,
            brs_entry.id,
        )

        # Upload short_credit cheques
        process_cheque_file(
            form.data.get("file_short_credit_entries"),
            BankReconLocalCollectionShortCredit,
            brs_entry.id,
        )

        # Upload excess_credit cheques
        process_cheque_file(
            form.data.get("file_excess_credit_entries"),
            BankReconLocalCollectionExcessCredit,
            brs_entry.id,
        )

        return redirect(url_for(".view_brs", brs_key=brs_entry.id))

    opening_balance, opening_on_hand = get_prev_month_closing_balance(brs.id)
    form.opening_balance.data = opening_balance
    form.opening_on_hand.data = opening_on_hand
    return render_template("brs_lc_data_entry.html", brs_entry=brs, form=form)


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
    db.session.execute(db.insert(table_name), df.to_dict(orient="records"))
    db.session.commit()

    # df.to_sql(table_name, db.engine, if_exists="append", index=False)


def get_prev_month_closing_balance(brs_id):
    Details = aliased(BankReconLocalCollectionDetails)
    Summary = aliased(BankReconLocalCollectionSummary)
    brs_summary = db.get_or_404(BankReconLocalCollectionSummary, brs_id)

    # need to be rectified
    # previous_month = brs_summary.month.replace(day=1) - timedelta(days=1)

    prev_month = datetime.strptime(brs_summary.month, "%B-%Y") - relativedelta(months=1)
    prev_month_str = prev_month.strftime("%B-%Y")

    previous_month_brs = db.session.scalar(
        db.select(Details).where(
            Details.brs_id == Summary.id,
            Summary.operating_office == brs_summary.operating_office,
            Summary.month == prev_month_str,
            Summary.local_collection_bank_account_number
            == brs_summary.local_collection_bank_account_number,
        )
    )
    if previous_month_brs:
        return (
            previous_month_brs.closing_balance,
            previous_month_brs.closing_on_hand,
        )
    else:
        return 0, 0


@brs_local_collection.route("/upload_previous_month/")
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
        BankReconLocalCollectionSummary.regional_office,
        BankReconLocalCollectionSummary.operating_office,
        db.literal(current_month_string),
        BankReconLocalCollectionSummary.purpose_of_bank_account,
        BankReconLocalCollectionSummary.local_collection_bank_name,
        BankReconLocalCollectionSummary.local_collection_bank_branch_name,
        BankReconLocalCollectionSummary.local_collection_bank_branch_location,
        BankReconLocalCollectionSummary.local_collection_bank_account_type,
        BankReconLocalCollectionSummary.local_collection_bank_account_number,
        BankReconLocalCollectionSummary.local_collection_bank_ifsc_code,
    ).where(BankReconLocalCollectionSummary.month == prev_month.strftime("%B-%Y"))

    insert_stmt = db.insert(BankReconLocalCollectionSummary).from_select(
        [
            BankReconLocalCollectionSummary.regional_office,
            BankReconLocalCollectionSummary.operating_office,
            BankReconLocalCollectionSummary.month,
            BankReconLocalCollectionSummary.purpose_of_bank_account,
            BankReconLocalCollectionSummary.local_collection_bank_name,
            BankReconLocalCollectionSummary.local_collection_bank_branch_name,
            BankReconLocalCollectionSummary.local_collection_bank_branch_location,
            BankReconLocalCollectionSummary.local_collection_bank_account_type,
            BankReconLocalCollectionSummary.local_collection_bank_account_number,
            BankReconLocalCollectionSummary.local_collection_bank_ifsc_code,
        ],
        stmt,
    )
    db.session.execute(insert_stmt)

    db.session.commit()

    return "Success"


@brs_local_collection.route("/bulk_upload", methods=["POST", "GET"])
@login_required
@admin_required
def bulk_upload_brs():
    form = FileUploadForm()
    if form.validate_on_submit():
        file = form.upload_file.data
        df = pd.read_excel(
            file, dtype={"regional_office": str, "operating_office": str}
        )
        db.session.execute(
            db.insert(BankReconLocalCollectionSummary), df.to_dict(orient="records")
        )
        db.session.commit()
        # df.to_sql(
        #     "bank_recon_local_collection_summary",
        #     db.engine,
        #     if_exists="append",
        #     index=False,
        # )
        flash("BRS local collection records have been uploaded to database")

    return render_template(
        "brs_lc_form.html", form=form, title="Bulk upload local collection items"
    )


@brs_local_collection.route("/download_format/")
@login_required
def download_format():
    return send_file("download_formats/brs_local_collection_upload_format.xlsx")


@brs_local_collection.route("/data/<string:entry_type>/", methods=["GET", "POST"])
@login_required
@ro_user_only
def list_brs_items(entry_type):
    form = MonthFilterForm()

    # Dynamic month dropdown
    month_choices = db.session.scalars(
        db.select(BankReconLocalCollectionSummary.month.distinct())
    )
    list_period = [datetime.strptime(item, "%B-%Y") for item in month_choices]
    list_period.sort(reverse=True)
    form.month.choices = [item.strftime("%B-%Y") for item in list_period]

    # Select which model we are querying
    MODEL_MAP = {
        "outstanding": BankReconLocalCollectionOutstanding,
        "short_credit": BankReconLocalCollectionShortCredit,
        "excess_credit": BankReconLocalCollectionExcessCredit,
    }

    if entry_type not in MODEL_MAP:
        abort(404)

    Model = MODEL_MAP.get(entry_type)

    if form.validate_on_submit():
        month = form.month.data

        stmt = (
            db.select(Model)
            .options(
                joinedload(Model.details).joinedload(
                    BankReconLocalCollectionDetails.summary
                )
            )
            .join(
                BankReconLocalCollectionDetails,
                BankReconLocalCollectionDetails.id == Model.brs_details_id,
            )
            .join(
                BankReconLocalCollectionSummary,
                BankReconLocalCollectionDetails.brs_id
                == BankReconLocalCollectionSummary.id,
            )
            .where(
                BankReconLocalCollectionDetails.status == "Active",
                BankReconLocalCollectionSummary.month == month,
            )
        )

        if current_user.user_type == "ro_user":
            stmt = stmt.where(
                BankReconLocalCollectionSummary.regional_office == current_user.ro_code
            )

        entries = db.session.scalars(stmt)

        return render_template(
            "brs_lc_entries.html",
            result=entries,
            title=entry_type.replace("_", " "),
        )

    title = f"Fetch {entry_type.replace('_', ' ')} entries"
    return render_template("brs_lc_form.html", form=form, title=title)


@brs_local_collection.route("/data/view_raw_data", methods=["GET", "POST"])
@login_required
@ro_user_only
def list_brs_entries():
    form = MonthFilterForm()

    month_choices = db.session.scalars(
        db.select(BankReconLocalCollectionSummary.month).distinct()
    )

    list_period = [datetime.strptime(item, "%B-%Y") for item in month_choices]

    # sorting the items of list_period in reverse order
    # newer months will be above
    list_period.sort(reverse=True)
    # list_period is now dynamically added as dropdown choice list to the SelectField
    form.month.choices = [item.strftime("%B-%Y") for item in list_period]

    if form.validate_on_submit():
        month = form.data["month"]

        stmt = (
            db.select(BankReconLocalCollectionDetails)
            .options(joinedload(BankReconLocalCollectionDetails.summary))
            .join(
                BankReconLocalCollectionSummary,
                BankReconLocalCollectionSummary.id
                == BankReconLocalCollectionDetails.brs_id,
            )
            .where(
                (BankReconLocalCollectionDetails.status == "Active"),
                (BankReconLocalCollectionSummary.month == month),
            )
        )

        if current_user.user_type == "ro_user":
            stmt = stmt.where(
                BankReconLocalCollectionSummary.regional_office == current_user.ro_code
            )
        results = db.session.scalars(stmt)
        return render_template(
            "brs_lc_data.html",
            brs_entries=results,
        )
    return render_template(
        "brs_lc_form.html", form=form, title="Fetch BRS - local collection data"
    )


@brs_local_collection.route("/api/v1/<string:office_code>/<string:month>/")
def get_schedule_bbc_ii(office_code: str, month: str) -> dict:
    Details = aliased(BankReconLocalCollectionDetails)
    Summary = aliased(BankReconLocalCollectionSummary)
    filtered_brs = (
        db.select(
            Summary.operating_office.label("office_code"),
            Summary.local_collection_bank_name.label("bank_name"),
            Summary.local_collection_bank_branch_location.label("bank_branch_location"),
            Summary.local_collection_bank_account_number.label("account_number"),
            Summary.local_collection_bank_ifsc_code.label("ifsc_code"),
            Summary.purpose_of_bank_account.label("nature_of_account"),
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
