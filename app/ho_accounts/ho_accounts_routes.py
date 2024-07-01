from datetime import datetime
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
)
from app.ho_accounts.ho_accounts_model import (
    HeadOfficeBankReconTracker,
    HeadOfficeAccountsTracker,
)

from app.users.user_model import User


@ho_accounts_bp.route("/bulk_upload_trackers", methods=["POST", "GET"])
@login_required
def bulk_upload_trackers():
    form = BulkUploadFileForm()
    from extensions import db

    if form.validate_on_submit():

        mis_tracker = form.data["mis_tracker_file_upload"]

        # TODO: define python data types at the time of reading
        df_mis_tracker = pd.read_excel(
            mis_tracker,
            dtype={"str_gl_code": str, "str_sl_code": str, "str_customer_id": str},
        )
        engine = create_engine(current_app.config.get("SQLALCHEMY_DATABASE_URI"))

        df_mis_tracker["date_created_date"] = datetime.now()
        df_mis_tracker["created_by"] = current_user.username
        # try:
        df_mis_tracker.to_sql(
            "head_office_bank_recon_tracker",  # "head_office_accounts_tracker",
            engine,
            if_exists="append",
            index=False,
        )

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
    #        return redirect(url_for("ho_accounts.home"))

    return render_template("ho_accounts_bulk_upload.html", form=form)


@ho_accounts_bp.route("/", methods=["POST", "GET"])
@login_required
def ho_accounts_tracker_home():
    form = FilterPeriodForm()

    period_list_query = HeadOfficeBankReconTracker.query.with_entities(
        HeadOfficeBankReconTracker.str_period
    ).distinct()

    # converting the period from string to datetime object
    list_period = [datetime.strptime(item[0], "%b-%y") for item in period_list_query]

    # sorting the items of list_period in reverse order
    # newer months will be above
    list_period.sort(reverse=True)
    # list_period is now dynamically added as dropdown choice list to the SelectField
    form.period.choices = [
        (item.strftime("%b-%y"), item.strftime("%B-%Y")) for item in list_period
    ]

    period = (
        HeadOfficeAccountsTracker.query.with_entities(
            HeadOfficeAccountsTracker.str_period
        )
        .distinct()
        .first()[0]
    )
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
        work.str_person = (
            form.str_assigned_to.data if form.str_assigned_to.data else None
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
    return render_template("accounts_work_edit.html", form=form, work=work)


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
        mis.boolean_mis_shared = form.boolean_mis_shared.data
        mis.boolean_jv_passed = form.boolean_jv_passed.data
        mis.text_remarks = form.text_remarks.data
        mis.str_person = (
            form.str_assigned_to.data if form.str_assigned_to.data else None
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
            form.str_brs_file_upload.data.save("data/ho_accounts/brs/" + brs_filename)
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
                "data/ho_accounts/bank_confirmation/" + bank_confirmation_filename
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
        directory=f"data/ho_accounts/{requirement}/",
        path=path,
        as_attachment=True,
        download_name=filename,
    )
