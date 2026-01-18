from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from pathlib import Path

import pandas as pd

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename


from . import ho_accounts_bp
from .ho_accounts_form import (
    BRSTrackerForm,
    AccountsTrackerForm,
    BulkUploadFileForm,
    FilterPeriodForm,
    BRSAddForm,
    WorkAddForm,
)
from .ho_accounts_model import (
    HeadOfficeBankReconTracker,
    HeadOfficeAccountsTracker,
)

from app.users.user_model import User
from extensions import db
from set_view_permissions import admin_required


@ho_accounts_bp.route("/upload_previous_month/")
def upload_previous_month():
    """View function to upload previous quarter HO checklist items after scheduled quarterly cron job"""

    # current_month refers to month that just ended
    current_month = date.today() - relativedelta(months=1)

    # prev_month is the 3 months before current_month
    prev_month = current_month - relativedelta(months=3)

    current_month_string = current_month.strftime("%b-%y")
    prev_month_string = prev_month.strftime("%b-%y")

    brs_stmt = db.select(
        db.literal("AUTOUPLOAD").label("created_by"),
        db.literal(current_month_string).label("str_period"),
        HeadOfficeBankReconTracker.str_name_of_bank,
        HeadOfficeBankReconTracker.str_bank_address,
        HeadOfficeBankReconTracker.str_purpose,
        HeadOfficeBankReconTracker.str_person,
        HeadOfficeBankReconTracker.str_gl_code,
        HeadOfficeBankReconTracker.str_sl_code,
        HeadOfficeBankReconTracker.str_bank_account_number,
        HeadOfficeBankReconTracker.str_customer_id,
    ).where(HeadOfficeBankReconTracker.str_period == prev_month_string)

    insert_brs_stmt = db.insert(HeadOfficeBankReconTracker).from_select(
        [
            HeadOfficeBankReconTracker.created_by,
            HeadOfficeBankReconTracker.str_period,
            HeadOfficeBankReconTracker.str_name_of_bank,
            HeadOfficeBankReconTracker.str_bank_address,
            HeadOfficeBankReconTracker.str_purpose,
            HeadOfficeBankReconTracker.str_person,
            HeadOfficeBankReconTracker.str_gl_code,
            HeadOfficeBankReconTracker.str_sl_code,
            HeadOfficeBankReconTracker.str_bank_account_number,
            HeadOfficeBankReconTracker.str_customer_id,
        ],
        brs_stmt,
    )
    db.session.execute(insert_brs_stmt)

    checklist_stmt = db.select(
        db.literal("AUTOUPLOAD").label("created_by"),
        db.literal(current_month_string).label("str_period"),
        HeadOfficeAccountsTracker.str_work,
        HeadOfficeAccountsTracker.str_person,
    ).where(HeadOfficeAccountsTracker.str_period == prev_month_string)

    insert_checklist_stmt = db.insert(HeadOfficeAccountsTracker).from_select(
        [
            HeadOfficeAccountsTracker.created_by,
            HeadOfficeAccountsTracker.str_period,
            HeadOfficeAccountsTracker.str_work,
            HeadOfficeAccountsTracker.str_person,
        ],
        checklist_stmt,
    )
    db.session.execute(insert_checklist_stmt)

    db.session.commit()
    return "Success"


@ho_accounts_bp.route("/bulk_upload_trackers", methods=["POST", "GET"])
@login_required
@admin_required
def bulk_upload_trackers():
    form = BulkUploadFileForm()

    if form.validate_on_submit():
        # engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
        if form.data["mis_tracker_file_upload"]:
            mis_tracker = form.data["mis_tracker_file_upload"]

            # TODO: define python data types at the time of reading
            df_mis_tracker = pd.read_excel(
                mis_tracker,
                dtype={"str_gl_code": str, "str_sl_code": str, "str_customer_id": str},
            )

            df_mis_tracker["date_created_date"] = datetime.now()
            df_mis_tracker["created_by"] = current_user.username
            # try:
            df_mis_tracker.to_sql(
                "head_office_bank_recon_tracker",  # "head_office_accounts_tracker",
                db.engine,
                if_exists="append",
                index=False,
            )

        if form.data["accounts_tracker_file_upload"]:
            accounts_tracker = form.data["accounts_tracker_file_upload"]
            # TODO: define python data types at the time of reading
            df_accounts_tracker = pd.read_excel(accounts_tracker)
            # engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

            df_accounts_tracker["date_created_date"] = datetime.now()
            df_accounts_tracker["created_by"] = current_user.username
            # try:
            df_accounts_tracker.to_sql(
                "head_office_accounts_tracker",
                db.engine,
                if_exists="append",
                index=False,
            )

        flash("Accounts Tracker and MIS tracker have been uploaded successfully.")

    return render_template("ho_accounts_bulk_upload.html", form=form)


def mask_account_number(account_number: str) -> str:
    if not account_number:
        return None
    return account_number[:2] + ((len(account_number) - 6) * "*") + account_number[-4:]


@ho_accounts_bp.route("/", methods=["POST", "GET"])
@login_required
@admin_required
def ho_accounts_tracker_home():
    form = FilterPeriodForm()

    period_list_query_brs = db.select(HeadOfficeBankReconTracker.str_period).distinct()
    period_list_query_work = db.select(HeadOfficeAccountsTracker.str_period).distinct()
    period_list_query = period_list_query_work.union(period_list_query_brs)
    period_list_items = db.session.scalars(period_list_query)
    # converting the period from string to datetime object
    list_period = [datetime.strptime(item, "%b-%y") for item in period_list_items]

    # sorting the items of list_period in reverse order
    # newer months will be above
    list_period.sort(reverse=True)
    # list_period is now dynamically added as dropdown choice list to the SelectField
    form.period.choices = [
        (item.strftime("%b-%y"), item.strftime("%B-%Y")) for item in list_period
    ]
    period = list_period[0].strftime("%b-%y")

    if form.validate_on_submit():
        period = form.data["period"]

    mis_stmt = (
        db.select(HeadOfficeBankReconTracker)
        .where(HeadOfficeBankReconTracker.str_period == period)
        .order_by(HeadOfficeBankReconTracker.id.asc())
    )
    accounts_stmt = (
        db.select(HeadOfficeAccountsTracker)
        .where(HeadOfficeAccountsTracker.str_period == period)
        .order_by(HeadOfficeAccountsTracker.id.asc())
    )

    mis_tracker = db.session.scalars(mis_stmt)
    accounts_work_tracker = db.session.scalars(accounts_stmt)

    return render_template(
        "ho_accounts_home.html",
        mis_tracker=mis_tracker,
        accounts_work_tracker=accounts_work_tracker,
        form=form,
        period=period,
        mask_account_number=mask_account_number,
    )


@ho_accounts_bp.route("/view_work/<int:id>/")
@login_required
@admin_required
def view_accounts_work(id):
    work = db.get_or_404(HeadOfficeAccountsTracker, id)
    return render_template("accounts_work_view.html", work=work)


@ho_accounts_bp.route("/view_mis/<int:id>/")
@login_required
@admin_required
def view_mis(id):
    mis = db.get_or_404(HeadOfficeBankReconTracker, id)
    return render_template("mis_status_view.html", mis=mis)


@ho_accounts_bp.route("/edit_work/<int:id>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_accounts_work(id):
    work = db.get_or_404(HeadOfficeAccountsTracker, id)
    form = AccountsTrackerForm(obj=work)
    stmt = (
        db.select(User.username)
        .where(User.user_type == "admin")
        .order_by(User.username)
    )
    ho_staff = db.session.scalars(stmt)
    form.str_person.choices = [
        username.upper() for username in ho_staff if "admin" not in username
    ]
    if form.validate_on_submit():
        form.populate_obj(work)
        db.session.commit()
        return redirect(url_for("ho_accounts.ho_accounts_tracker_home"))

    return render_template("accounts_work_edit.html", form=form, work=work)


@ho_accounts_bp.route("/add_work", methods=["POST", "GET"])
@login_required
@admin_required
def add_work():
    form = WorkAddForm()

    stmt = (
        db.select(User.username)
        .where(User.user_type == "admin")
        .order_by(User.username)
    )
    ho_staff = db.session.scalars(stmt)
    form.str_person.choices = [
        username.upper() for username in ho_staff if "admin" not in username
    ]
    if form.validate_on_submit():
        work = HeadOfficeAccountsTracker()
        form.populate_obj(work)

        db.session.add(work)
        db.session.commit()

        return redirect(url_for("ho_accounts.ho_accounts_tracker_home"))
    return render_template("accounts_work_add.html", form=form)


@ho_accounts_bp.route("/add_bank_account", methods=["POST", "GET"])
@login_required
@admin_required
def add_bank_account():
    form = BRSAddForm()
    stmt = (
        db.select(User.username)
        .where(User.user_type == "admin")
        .order_by(User.username)
    )
    ho_staff = db.session.scalars(stmt)
    form.str_person.choices = [
        username.upper() for username in ho_staff if "admin" not in username
    ]
    if form.validate_on_submit():
        mis = HeadOfficeBankReconTracker()
        form.populate_obj(mis)
        db.session.add(mis)
        db.session.commit()
        return redirect(url_for("ho_accounts.ho_accounts_tracker_home"))
    return render_template("mis_status_add.html", form=form)


@ho_accounts_bp.route("/edit_mis/<int:id>/", methods=["POST", "GET"])
@login_required
@admin_required
def edit_mis(id):
    mis = db.get_or_404(HeadOfficeBankReconTracker, id)
    form = BRSTrackerForm(obj=mis)
    stmt = (
        db.select(User.username)
        .where(User.user_type == "admin")
        .order_by(User.username)
    )
    ho_staff = db.session.scalars(stmt)
    form.str_person.choices = [
        username.upper() for username in ho_staff if "admin" not in username
    ]
    if form.validate_on_submit():
        form.populate_obj(mis)
        upload_mis_documents(form, "str_brs_file", mis, "str_brs_file_upload", "brs")
        upload_mis_documents(
            form,
            "str_bank_confirmation_file",
            mis,
            "str_bank_confirmation_file_upload",
            "bank_confirmation",
        )

        db.session.commit()
        return redirect(url_for("ho_accounts.ho_accounts_tracker_home"))

    return render_template("mis_status_edit.html", form=form, mis=mis)


def upload_mis_documents(form, field_name, model_obj, model_field, folder_name):
    upload_root = current_app.config.get("UPLOAD_FOLDER_PATH")
    folder_path = upload_root / "ho_accounts" / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    file = form.data.get(field_name)

    if file:
        brs_filename_data = secure_filename(file.filename)
        brs_file_extension = Path(brs_filename_data).suffix
        brs_filename = (
            folder_name + datetime.now().strftime("%d%m%Y %H%M%S") + brs_file_extension
        )
        file.save(folder_path / brs_filename)
        setattr(model_obj, model_field, brs_filename)


@ho_accounts_bp.route("/download_mis_document/<string:requirement>/<int:id>")
@login_required
@admin_required
def download_mis_documents(requirement, id):
    mis = db.get_or_404(HeadOfficeBankReconTracker, id)
    if requirement == "bank_confirmation":
        stored_filename = mis.str_bank_confirmation_file_upload
    elif requirement == "brs":
        stored_filename = mis.str_brs_file_upload
    else:
        abort(404)
    stored_path = Path(stored_filename)
    file_extension = stored_path.suffix
    download_name = f"{mis.str_period}-{requirement}_{mis.str_name_of_bank}_{mis.str_gl_code}_{mis.str_sl_code}{file_extension}"

    base_directory = (
        current_app.config.get("UPLOAD_FOLDER_PATH") / "ho_accounts" / requirement
    )
    return send_from_directory(
        directory=base_directory,
        path=stored_path.name,
        as_attachment=True,
        download_name=download_name,
    )
