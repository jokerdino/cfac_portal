from dataclasses import asdict
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

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

from sqlalchemy import create_engine, func, distinct, text, case, union, cast, String


from app.ho_accounts import ho_accounts_bp
from app.ho_accounts.ho_accounts_form import (
    BRSTrackerForm,
    AccountsTrackerForm,
    BulkUploadFileForm,
    FilterPeriodForm,
    BRSAddForm,
    WorkAddForm,
)
from app.ho_accounts.ho_accounts_model import (
    HeadOfficeBankReconTracker,
    HeadOfficeAccountsTracker,
)

from app.users.user_model import User


@ho_accounts_bp.route("/upload_previous_month/")
def upload_previous_month():
    """View function to upload previous quarter HO checklist itemes after scheduled quarterly cron job"""
    from extensions import db

    # current_month refers to month that just ended
    current_month = date.today() - relativedelta(months=1)

    # prev_month is the 3 months before current_month
    prev_month = current_month - relativedelta(months=3)

    fresh_entries = []
    recon_entries = db.session.scalars(
        db.select(HeadOfficeBankReconTracker).where(
            HeadOfficeBankReconTracker.str_period == prev_month.strftime("%b-%y")
        )
    )
    for entry in recon_entries:

        new_entry = HeadOfficeBankReconTracker(
            **asdict(entry),
            str_period=current_month.strftime("%b-%y"),
            created_by="AUTOUPLOAD",
        )

        fresh_entries.append(new_entry)

    accounts_entries = db.session.scalars(
        db.select(HeadOfficeAccountsTracker).where(
            HeadOfficeAccountsTracker.str_period == prev_month.strftime("%b-%y")
        )
    )
    for entry in accounts_entries:

        new_entry = HeadOfficeAccountsTracker(
            **asdict(entry),
            str_period=current_month.strftime("%b-%y"),
            created_by="AUTOUPLOAD",
        )

        fresh_entries.append(new_entry)

    db.session.add_all(fresh_entries)
    db.session.commit()
    return "Success"


@ho_accounts_bp.route("/bulk_upload_trackers", methods=["POST", "GET"])
@login_required
def bulk_upload_trackers():
    form = BulkUploadFileForm()
    from extensions import db

    if form.validate_on_submit():
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))
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
                engine,
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
                engine,
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
def ho_accounts_tracker_home():
    from extensions import db

    form = FilterPeriodForm()

    period_list_query_brs = HeadOfficeBankReconTracker.query.with_entities(
        HeadOfficeBankReconTracker.str_period
    ).distinct()
    period_list_query_work = HeadOfficeAccountsTracker.query.with_entities(
        HeadOfficeAccountsTracker.str_period
    ).distinct()
    period_list_query = period_list_query_work.union(period_list_query_brs)
    # converting the period from string to datetime object
    list_period = [datetime.strptime(item[0], "%b-%y") for item in period_list_query]

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
    mis_tracker = HeadOfficeBankReconTracker.query.filter(
        HeadOfficeBankReconTracker.str_period == period
    ).order_by(HeadOfficeBankReconTracker.id.asc())
    accounts_work_tracker = HeadOfficeAccountsTracker.query.filter(
        HeadOfficeAccountsTracker.str_period == period
    ).order_by(HeadOfficeAccountsTracker.id.asc())

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
def view_accounts_work(id):
    work = HeadOfficeAccountsTracker.query.get_or_404(id)
    return render_template("accounts_work_view.html", work=work)


@ho_accounts_bp.route("/view_mis/<int:id>/")
@login_required
def view_mis(id):
    mis = HeadOfficeBankReconTracker.query.get_or_404(id)
    return render_template("mis_status_view.html", mis=mis)


@ho_accounts_bp.route("/edit_work/<int:id>/", methods=["POST", "GET"])
@login_required
def edit_accounts_work(id):
    from extensions import db

    work = HeadOfficeAccountsTracker.query.get_or_404(id)
    form = AccountsTrackerForm()
    ho_staff = User.query.filter(User.user_type == "admin").order_by(User.username)
    form.str_assigned_to.choices = [
        person.username.upper() for person in ho_staff if "admin" not in person.username
    ]
    if form.validate_on_submit():
        work.str_work = form.str_work.data if form.str_work.data else work.str_work
        work.str_person = (
            form.str_assigned_to.data if form.str_assigned_to.data else work.str_person
        )
        work.bool_current_status = form.bool_current_status.data
        work.text_remarks = form.text_remarks.data
        work.updated_by = current_user.username
        work.date_updated_date = datetime.now()
        db.session.commit()
        return redirect(url_for("ho_accounts.ho_accounts_tracker_home"))
    form.bool_current_status.data = work.bool_current_status
    form.text_remarks.data = work.text_remarks
    form.str_assigned_to.data = work.str_person
    form.str_work.data = work.str_work
    return render_template("accounts_work_edit.html", form=form, work=work)


@ho_accounts_bp.route("/add_work", methods=["POST", "GET"])
@login_required
def add_work():
    form = WorkAddForm()
    from extensions import db

    ho_staff = User.query.filter(User.user_type == "admin").order_by(User.username)
    form.str_assigned_to.choices = [
        person.username.upper() for person in ho_staff if "admin" not in person.username
    ]
    if form.validate_on_submit():
        str_period = f"{form.str_month.data}-{form.str_year.data}"
        str_work = form.str_work.data
        str_person = form.str_assigned_to.data
        work = HeadOfficeAccountsTracker(
            str_period=str_period,
            str_work=str_work,
            str_person=str_person,
            created_by=current_user.username,
            date_created_date=datetime.now(),
        )
        db.session.add(work)
        db.session.commit()

        return redirect(url_for("ho_accounts.ho_accounts_tracker_home"))
    return render_template("accounts_work_add.html", form=form)


@ho_accounts_bp.route("/add_mis", methods=["POST", "GET"])
@login_required
def add_mis():
    from extensions import db

    form = BRSAddForm()
    ho_staff = User.query.filter(User.user_type == "admin").order_by(User.username)
    form.str_assigned_to.choices = [
        person.username.upper() for person in ho_staff if "admin" not in person.username
    ]
    if form.validate_on_submit():
        str_period = f"{form.str_month.data}-{form.str_year.data}"
        str_name_of_bank = form.str_name_of_bank.data
        str_purpose = form.str_purpose.data
        str_person = form.str_assigned_to.data
        str_bank_address = form.str_bank_address.data
        str_gl_code = form.str_gl_code.data
        str_sl_code = form.str_sl_code.data

        str_bank_account_number = form.str_bank_account_number.data
        str_customer_id = form.str_customer_id.data

        mis = HeadOfficeBankReconTracker(
            str_period=str_period,
            str_name_of_bank=str_name_of_bank,
            str_purpose=str_purpose,
            str_person=str_person,
            str_bank_address=str_bank_address,
            str_gl_code=str_gl_code,
            str_sl_code=str_sl_code,
            str_bank_account_number=str_bank_account_number,
            str_customer_id=str_customer_id,
            date_created_date=datetime.now(),
            created_by=current_user.username,
        )
        db.session.add(mis)
        db.session.commit()
        return redirect(url_for("ho_accounts.ho_accounts_tracker_home"))
    return render_template("mis_status_add.html", form=form)


@ho_accounts_bp.route("/edit_mis/<int:id>/", methods=["POST", "GET"])
@login_required
def edit_mis(id):
    from extensions import db

    mis = HeadOfficeBankReconTracker.query.get_or_404(id)
    form = BRSTrackerForm()
    ho_staff = User.query.filter(User.user_type == "admin").order_by(User.username)
    form.str_assigned_to.choices = [
        person.username.upper() for person in ho_staff if "admin" not in person.username
    ]
    if form.validate_on_submit():
        mis.str_purpose = (
            form.str_purpose.data if form.str_purpose.data else mis.str_purpose
        )
        mis.str_name_of_bank = (
            form.str_name_of_bank.data
            if form.str_name_of_bank.data
            else mis.str_name_of_bank
        )
        mis.boolean_mis_shared = form.boolean_mis_shared.data
        mis.boolean_jv_passed = form.boolean_jv_passed.data
        mis.text_remarks = form.text_remarks.data
        mis.str_person = (
            form.str_assigned_to.data if form.str_assigned_to.data else mis.str_person
        )

        if form.data["str_brs_file_upload"]:

            brs_filename_data = secure_filename(
                form.data["str_brs_file_upload"].filename
            )
            brs_file_extension = brs_filename_data.rsplit(".", 1)[1]
            brs_filename = (
                "brs"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + brs_file_extension
            )
            form.str_brs_file_upload.data.save(
                f"{current_app.config.get('UPLOAD_FOLDER')}ho_accounts/brs/"
                + brs_filename
            )
            mis.str_brs_file_upload = brs_filename

        if form.data["str_bank_confirmation_file_upload"]:
            bank_confirmation_filename_data = secure_filename(
                form.data["str_bank_confirmation_file_upload"].filename
            )
            bank_confirmation_file_extension = bank_confirmation_filename_data.rsplit(
                ".", 1
            )[1]
            bank_confirmation_filename = (
                "bank_confirmation"
                + datetime.now().strftime("%d%m%Y %H%M%S")
                + "."
                + bank_confirmation_file_extension
            )
            form.str_bank_confirmation_file_upload.data.save(
                f"{current_app.config.get('UPLOAD_FOLDER')}ho_accounts/bank_confirmation/"
                + bank_confirmation_filename
            )
            mis.str_bank_confirmation_file_upload = bank_confirmation_filename

        mis.updated_by = current_user.username
        mis.date_updated_date = datetime.now()
        db.session.commit()
        return redirect(url_for("ho_accounts.ho_accounts_tracker_home"))
    form.boolean_mis_shared.data = mis.boolean_mis_shared
    form.boolean_jv_passed.data = mis.boolean_jv_passed
    form.text_remarks.data = mis.text_remarks
    form.str_assigned_to.data = mis.str_person
    form.str_purpose.data = mis.str_purpose
    form.str_name_of_bank.data = mis.str_name_of_bank

    return render_template("mis_status_edit.html", form=form, mis=mis)


@ho_accounts_bp.route("/download_mis_document/<string:requirement>/<int:id>")
@login_required
def download_mis_documents(requirement, id):
    mis = HeadOfficeBankReconTracker.query.get_or_404(id)
    if requirement == "bank_confirmation":

        file_extension = mis.str_bank_confirmation_file_upload.rsplit(".", 1)[1]
        path = mis.str_bank_confirmation_file_upload
    elif requirement == "brs":
        file_extension = mis.str_brs_file_upload.rsplit(".", 1)[1]
        path = mis.str_brs_file_upload
    else:
        abort(404)
    filename = f"{mis.str_period}-{requirement}_{mis.str_name_of_bank}_{mis.str_gl_code}_{mis.str_sl_code}.{file_extension}"

    return send_from_directory(
        directory=f"{current_app.config.get('UPLOAD_FOLDER')}ho_accounts/{requirement}/",
        path=path,
        as_attachment=True,
        download_name=filename,
    )
